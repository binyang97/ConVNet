import numpy as np
import pickle

# file_demo = "D:\Documents/3dVision_ConVoNet/convolutional_occupancy_networks_green/data/demo/Matterport3D_processed/17DRP5sb8fy/pointcloud.npz"
# file_sharp = "D:/Documents/3dVision_ConVoNet/convolutional_occupancy_networks_green/Track1-3DBodyTex.v2/Track1-3DBodyTex.v2/train/train/180228-001-casual-scape012-etui-8b2f-low-res-result/180228-001-casual-scape012-etui-8b2f-low-res-result_normalized.npz"

# file_partial = "D:/Documents/3dVision_ConVoNet/170410-012-a-iqbj-e9b3-low-res-result/170410-012-a-iqbj-e9b3-low-res-result_normalized-partial-01..npz"
# points_file_2 = np.load(file_sharp,  allow_pickle=True)

# points_file = np.load(file_demo)

# points_partial = np.load(file_partial)


# print(points_file_2["normals"].shape)
# file_partial_obj = "D:/Documents/3dVision_ConVoNet/170410-012-a-iqbj-e9b3-low-res-result/170410-012-a-iqbj-e9b3-low-res-result_normalized-partial-01..obj"

file = "D:/Documents/3dVision_ConVoNet/convolutional_occupancy_networks_green/data/demo/Matterport3D_processed/17DRP5sb8fy/pointcloud.npz"
file2 = "D:\Documents/3dVision_ConVoNet/convolutional_occupancy_networks_green/scripts/data/synthetic_room_dataset/rooms_04/00000009/points_iou/points_iou_00.npz"

points_file = np.load(file)
points_iou_file = np.load(file2)
#print(points_file["normals"].shape)
#print(points_iou_file["points"].shape)

print(points_file.files)
print(points_iou_file.files)

path = "D:/Documents/3dVision_ConVoNet/train_partial/170410-012-a-iqbj-e9b3-low-res-result/170410-012-a-iqbj-e9b3-low-res-result_normalized-partial-01._scaled_boundary_0.1_samples.npz"

file3 = np.load(path, allow_pickle = True)

print(file3.files)
# for face in file3['faces']:
#     vertex_1 = vertices[face[0]]
#     vertex_2 = vertices[face[1]]
#     vertex_3 = vertices[face[2]]

#     vector1 = vertex_2 - vertex_1
#     vector2 = vertex_3 - vertex_1

#     normal = np.cross(vector1, vector2)
#     normals.append(normal)

# data['normals'] = normals

# np.savez(path, **data)

# file_new = np.load(path)









