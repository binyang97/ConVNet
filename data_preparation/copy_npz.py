import numpy as np
import shutil
import glob
import os

path = "../../SHARP_data_coinvonet/track1/train_partial"

for data in glob.glob(path + "/*"):
    shutil.copy(os.path.join(data, "points/points_00.npz"), os.path.join(data, "points.npz"))