import cv2

VIDEO_SRC = "videos/surviv.io2020-10-03_16-39-54.mp4"

def frames_slicer(video_dir, interval=15):
    vidcap = cv2.VideoCapture(video_dir)
    success,image = vidcap.read()
    count = 0
    while success:
        if count % interval == 0:
            skip_count = 0
            count += 1
            cv2.imwrite("raw/frame%d.png" % count, image)     # save frame as PNG file     
            print("Output frame ", count) 
        success,image = vidcap.read()
        count += 1
    print("Output total frames: ", count)






if __name__ == '__main__': 
    frames_slicer(VIDEO_SRC, 15)