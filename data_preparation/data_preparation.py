import glob
import numpy as np
import os
import shutil
import random


path = "../../SHARP_data_coinvonet/track1/train_partial"

files_scaled = glob.glob(path + "././*scaled_boundary_0.1_samples.npz")

for data in glob.glob(path + "./*"):
    os.makedir(os.path.join(data + "points"))
    
    for pointcloud in glob.glob(data+"./*scaled_boundary_0.1_samples.npz"):
        shutil.copy(pointcloud, os.path.join(path + "points"))

for data in glob.glob(path + "./*"):
    points = os.listdir(os.path.join(data + "points"))
    assert len(points) != 0
    points.sort()
    for count, point in enumerate(points):
        if count < 10:
            os.rename(point, "points_0" + str(count))
        else:
            os.rename(point, "points_" + str(count))

# Creat lst file

data = os.listdir(path)
data.remove("points")
random.shuffle(data)

# 8:2 = train:val
index = int(len(data)*0.8)
train = data[:index]
val = data[index:]

with open(path + "train.lst", "a") as a_file:
    a_file.write(train)
with open(path + "val.lst", "a") as a_file:
    a_file.write(val)

