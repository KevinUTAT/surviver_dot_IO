''' This script is used to perform pre process to images 
that is going to be used as training data:
- rename the image to prevent name colition
'''

import os
import datetime
import re
from numpy import random

img_dir = "raw/"
target_dir = "forboxing/0/"
label_dir = "newlabels/0/"
data_label_dir = "data/sparrow_nsparrow/labels/correct/"


def rename(filename, work_dir):
    extenstion = filename.split('.')[-1]
    timestemp = datetime.datetime.now()
    new_name = timestemp.strftime('%y') + timestemp.strftime('%j') \
        + timestemp.strftime('%H') + timestemp.strftime('%M') \
            + timestemp.strftime('%S') + timestemp.strftime('%f') \
                + str(random.randint(999)) + '.' + extenstion
    src = work_dir + filename
    target = work_dir + new_name
    os.rename(src, target)
    return new_name


def rename_all():
    for count, filename in enumerate(os.listdir(img_dir)):
        rename(filename, img_dir)


# used for renaming image-label pairs
def back_ward_rename():
    for count, filename in enumerate(os.listdir(target_dir)):
        newname = rename(filename, target_dir)
        
        new_name = newname.split('.')[0] + '.' + "txt"
        src = label_dir + filename.split('.')[0] + '.' + "txt"
        target = label_dir + new_name
        os.rename(src, target)


# correcting labels with class non - 0
def label_correction():
    for count, label_name in enumerate(os.listdir(data_label_dir)):
        with open(data_label_dir + label_name, 'r+') as label_txt:
            # for line in label_txt:
            #     line_arr = line.split()
            #     if line_arr[0] != '0':
            #         line_arr[0] = '0'
            #         for element in line_arr:
            #             label_txt.write(element)
            data = label_txt.read()
            label_txt.seek(0)
            label_txt.write(re.sub(r"-1", r"0", data))
            label_txt.truncate()
    




if __name__ == '__main__': 
    rename_all() 
    # back_ward_rename()
    # label_correction()