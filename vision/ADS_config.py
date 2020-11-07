# this file is to store all the globlly accessed
# data structure and configuration variable

# subfolder where images can be found
IMG_FOLDER = "/images"
# extension of images
IMG_EXT = 'png'
# subfolder where labels can be found
LEBEL_FOLDER = "/labels"

label_table = {}

# A modification is a array of [data_name, target_idx, new_data, old_data]
# to delete a target, set new_data to ''
# Old data is used to undo changes
modification_list = []