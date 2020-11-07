import glob
import os
import numpy as np
import sys

current_dir = "./data/data/player/images"
img_dir = "./data/player/images"
split_pct = 10  # 10% validation set

def train_val_split():
    file_train = open("data/train.txt", "w")  
    file_val = open("data/val.txt", "w")  
    counter = 1  
    index_test = round(100 / split_pct)  
    for fullpath in glob.iglob(os.path.join(current_dir, "*.png")):  
        title, ext = os.path.splitext(os.path.basename(fullpath))
        if counter == index_test:
            counter = 1
            file_val.write(img_dir + "/" + title + '.png' + "\n")
        else:
            file_train.write(img_dir + "/" + title + '.png' + "\n")
            counter = counter + 1
    file_train.close()
    file_val.close()


if __name__ == "__main__":
    train_val_split()