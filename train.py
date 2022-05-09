import torch
import torch.optim as optim
from tensorboardX import SummaryWriter
import numpy as np
import os
import argparse
import time, datetime
import matplotlib; matplotlib.use('Agg')
from src import config, data
from src.checkpoints import CheckpointIO
from collections import defaultdict
import shutil
import torch.distributed as dist
import torch.multiprocessing as mp
from torch.nn.parallel import DistributedDataParallel as DDP


def setup(rank, world_size):
    os.environ['MASTER_ADDR'] = 'localhost'
    os.environ['MASTER_PORT'] = '12355'

    # initialize the process group
    dist.init_process_group("gloo", rank=rank, world_size=world_size)

def cleanup():
    dist.destroy_process_group()

def train_basic(rank, cfg, args, t0, world_size, lock):
    print(f"Running basic DDP on rank {rank}.")
    setup(rank, world_size)

    # Shorthands
    out_dir = cfg['training']['out_dir']
    batch_size = cfg['training']['batch_size']
    backup_every = cfg['training']['backup_every']
    vis_n_outputs = cfg['generation']['vis_n_outputs']
    exit_after = args.exit_after

    model_selection_metric = cfg['training']['model_selection_metric']
    if cfg['training']['model_selection_mode'] == 'maximize':
        model_selection_sign = 1
    elif cfg['training']['model_selection_mode'] == 'minimize':
        model_selection_sign = -1
    else:
        raise ValueError('model_selection_mode must be '
                        'either maximize or minimize.')

    # Output directory
    if not rank and not os.path.exists(out_dir):
        os.makedirs(out_dir)

    if not rank:
        shutil.copyfile(args.config, os.path.join(out_dir, 'config.yaml'))#!!!!!!

    # Dataset
    train_dataset = config.get_dataset('train', cfg)
    val_dataset = config.get_dataset('val', cfg, return_idx=True)
    if not rank:
        #dist.send(tensor=torch.Tensor(val_loss), dst=1)
        train_length = len(train_dataset)
        train_partial_length = int(train_length/world_size)
        train_index = np.arange(0,train_length, dtype = int)
        np.random.shuffle(train_index)
        for i in range(1, world_size):
            partial_index = torch.Tensor(train_index[train_partial_length*i: train_partial_length*(i+1)])
            dist.send(tensor=partial_index, dst=i)
        train_index = train_index[: train_partial_length]
    else:
        index_torch = torch.Tensor([0])
        dist.recv(tensor=index_torch, src=0)
        train_index = index_torch.cpu().numpy()
    dist.barrier()
    if not rank:
        val_length = len(val_dataset)
        val_partial_length = int(val_length/world_size)
        val_index = np.arange(0,val_length, dtype = int)
        np.random.shuffle(val_index)
        for i in range(1, world_size):
            partial_index = torch.Tensor(val_index[val_partial_length*i: val_partial_length*(i+1)])
            dist.send(tensor=partial_index, dst=i)
        val_index = val_index[: val_partial_length]
    else:
        index_torch = torch.Tensor([0])
        dist.recv(tensor=index_torch, src=0)
        val_index = index_torch.cpu().numpy()
    dist.barrier()
    
    train_dataset.random_split(train_index)
    val_dataset.random_split(val_index)

    '''
    train_loader = torch.utils.data.DataLoader(
        #train_dataset, batch_size=batch_size, num_workers=cfg['training']['n_workers'], shuffle=True,
        train_dataset, batch_size=batch_size, num_workers=0, shuffle=True,
        collate_fn=data.collate_remove_none,
        worker_init_fn=data.worker_init_fn)

    val_loader = torch.utils.data.DataLoader(
        val_dataset, batch_size=1, num_workers=0, shuffle=False,
        #val_dataset, batch_size=1, num_workers=cfg['training']['n_workers_val'], shuffle=False,
        collate_fn=data.collate_remove_none,
        worker_init_fn=data.worker_init_fn)

    # For visualizations
    if not rank:
        vis_loader = torch.utils.data.DataLoader(
            val_dataset, batch_size=1, shuffle=False,
            collate_fn=data.collate_remove_none,
            worker_init_fn=data.worker_init_fn)
        model_counter = defaultdict(int)#!!!!!
        data_vis_list = []#!!!!!!

        # Build a data dictionary for visualization
        #!!!!
        iterator = iter(vis_loader)
        for i in range(len(vis_loader)):
            data_vis = next(iterator)
            idx = data_vis['idx'].item()
            model_dict = val_dataset.get_model_dict(idx)
            category_id = model_dict.get('category', 'n/a')
            category_name = val_dataset.metadata[category_id].get('name', 'n/a')
            category_name = category_name.split(',')[0]
            if category_name == 'n/a':
                category_name = category_id

            c_it = model_counter[category_id]
            if c_it < vis_n_outputs:
                data_vis_list.append({'category': category_name, 'it': c_it, 'data': data_vis})

            model_counter[category_id] += 1
        #!!!!!!

    # Model
    model = config.get_model(cfg, device=rank, dataset=train_dataset)
    ddp_model = DDP(model, device_ids = [rank])

    # Generator!!!!!!!!
    if not rank:
        generator = config.get_generator(ddp_model, cfg, device=ddp_model.device)

    # Intialize training
    optimizer = optim.Adam(ddp_model.parameters(), lr=1e-4)#??????
    # optimizer = optim.SGD(model.parameters(), lr=1e-4, momentum=0.9)
    trainer = config.get_trainer(ddp_model, optimizer, cfg, device=ddp_model.device)#???????

    checkpoint_io = CheckpointIO(out_dir, model=ddp_model, optimizer=optimizer)#!!!!!!

    try:
        load_dict = checkpoint_io.load('model.pt', rank = rank)
    except FileExistsError:
        load_dict = dict()
    epoch_it = load_dict.get('epoch_it', 0)
    it = load_dict.get('it', 0)
    metric_val_best = load_dict.get(
        'loss_val_best', -model_selection_sign * np.inf)

    if metric_val_best == np.inf or metric_val_best == -np.inf:
        metric_val_best = -model_selection_sign * np.inf

    if not rank:
        print('Current best validation metric (%s): %.8f'
            % (model_selection_metric, metric_val_best))
        logger = SummaryWriter(os.path.join(out_dir, 'logs'))#!!!!!!!!!!

    # Shorthands
    print_every = cfg['training']['print_every']
    checkpoint_every = cfg['training']['checkpoint_every']
    validate_every = cfg['training']['validate_every']
    visualize_every = cfg['training']['visualize_every']

    # Print model !!!!!!!
    if not rank:
        nparameters = sum(p.numel() for p in model.parameters())
        print('Total number of parameters: %d' % nparameters)

        print('output path: ', cfg['training']['out_dir'])

    dist.barrier()
 
    while True:
        epoch_it += 1
        
        for batch in train_loader:
            it += 1
            loss = trainer.train_step(batch)
            sum_loss = loss

            if not rank:
                #dist.send(tensor=torch.Tensor(val_loss), dst=1)
                for rank in range(1, world_size):
                    train_loss_from_others = torch.zeros(1)
                    dist.recv(tensor=train_loss_from_others, src=rank)
                    sum_loss += train_loss_from_others.item()
            else:
                dist.send(tensor=torch.Tensor([loss]), dst=0)
            dist.barrier()
            if not rank:
                loss = sum_loss/world_size
                logger.add_scalar('train/loss', loss, it)#synchronize

            # Print output
            if print_every > 0 and (it % print_every) == 0 and not rank:#!!!!!!!
                t = datetime.datetime.now()
                print('[Epoch %02d] it=%03d, loss=%.4f, time: %.2fs, %02d:%02d'
                        % (epoch_it, it, loss, time.time() - t0, t.hour, t.minute))

            # Visualize output
            if visualize_every > 0 and (it % visualize_every) == 0 and not rank:#!!!!!!!
                print('Visualizing')
                for data_vis in data_vis_list:
                    if cfg['generation']['sliding_window']:
                        out = generator.generate_mesh_sliding(data_vis['data'])    
                    else:
                        out = generator.generate_mesh(data_vis['data'])
                    # Get statistics
                    try:
                        mesh, stats_dict = out
                    except TypeError:
                        mesh, stats_dict = out, {}

                    mesh.export(os.path.join(out_dir, 'vis', '{}_{}_{}.off'.format(it, data_vis['category'], data_vis['it'])))


            # Save checkpoint
            if (checkpoint_every > 0 and (it % checkpoint_every) == 0) and not rank:#!!!!!!!
                print('Saving checkpoint')
                checkpoint_io.save('model.pt', epoch_it=epoch_it, it=it,
                                loss_val_best=metric_val_best)

            # Backup if necessary
            if (backup_every > 0 and (it % backup_every) == 0) and not rank:#!!!!!!
                print('Backup checkpoint')
                checkpoint_io.save('model_%d.pt' % it, epoch_it=epoch_it, it=it,
                                loss_val_best=metric_val_best)
            dist.barrier()
            # Run validation
            if validate_every > 0 and (it % validate_every) == 0:#synchronize
                eval_dict = trainer.evaluate(val_loader)
                
                temp_data = []
                for k, v in eval_dict.items():
                    temp_data.append(v)

                temp_data = torch.Tensor(temp_data)

                if not rank:
                    total_data = temp_data.detach().clone()
                    #dist.send(tensor=torch.Tensor(val_loss), dst=1)
                    for rank in range(1,world_size):
                        val_loss_from_others = torch.zeros_like(total_data)
                        dist.recv(tensor=val_loss_from_others, src=rank)
                        total_data += val_loss_from_others
                    total_data = total_data/world_size
                else:
                    dist.send(tensor=temp_data, dst=0)
                dist.barrier()

                if not rank:
                    temp_i=0
                    for k, v in eval_dict.items():
                        logger.add_scalar('val/%s' % k, total_data[i].item(), it)
                        temp_i+=1

                    metric_val = eval_dict[model_selection_metric]
                    print('Validation metric (%s): %.4f'
                        % (model_selection_metric, metric_val))

                    if model_selection_sign * (metric_val - metric_val_best) > 0:
                        metric_val_best = metric_val
                        print('New best model (loss %.4f)' % metric_val_best)
                        checkpoint_io.save('model_best.pt', epoch_it=epoch_it, it=it,
                                        loss_val_best=metric_val_best)
                dist.barrier()

            # Exit if necessary
            if exit_after > 0 and (time.time() - t0) >= exit_after:#!!!!!!!!!!
                print('Time limit reached. Exiting.')
                if not rank:
                    checkpoint_io.save('model.pt', epoch_it=epoch_it, it=it,
                                    loss_val_best=metric_val_best)
                dist.barrier()
                exit(3)
    '''
    cleanup()

if __name__ == '__main__':
    # Arguments
    parser = argparse.ArgumentParser(
        description='Train a 3D reconstruction model.'
    )
    parser.add_argument('config', type=str, help='Path to config file.')
    parser.add_argument('--no-cuda', action='store_true', help='Do not use cuda.')
    parser.add_argument('--exit-after', type=int, default=-1,
                        help='Checkpoint and exit after specified number of seconds'
                            'with exit code 2.')

    args = parser.parse_args()
    cfg = config.load_config(args.config, 'configs/default.yaml')

    n_gpus = torch.cuda.device_count()
    assert n_gpus >= 2, f"Requires at least 2 GPUs to run, but got {n_gpus}"
    world_size = n_gpus

    # Set t0
    t0 = time.time()
    lock = mp.Lock()
    mp.spawn(train_basic,
             args=(cfg, args, t0, world_size, lock),
             nprocs=world_size,
             join=True)
    print("main finished")

