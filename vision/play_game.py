import argparse
import threading
import queue
import time
import pyautogui
from detect import *


def game_ai(tracking_list):
    center_screen = (pyautogui.size()[0]/2 , pyautogui.size()[1]/2)
    pyautogui.FAILSAFE = False
    while True:
        while not tracking_list.empty():
            i = 0
            targets = tracking_list.get()
            center_x = int((targets[i][1][0] + targets[i][2][0]) / 2)
            center_y = int((targets[i][1][1] + targets[i][2][1]) / 2)
            # Check the target to be yourself, if it is, move on to the next target
            if (abs(center_screen[0] - center_x) + abs(center_screen[1] - center_y)) > 50 \
                and targets[i][3] > 0.3: 
                pyautogui.mouseDown(x=center_x, y=center_y)
                time.sleep(0.1)
                pyautogui.mouseUp()
                # pyautogui.moveTo(x=center_x, y=center_y)
                print("Firing at ", center_x, center_y)
                break
            else:
                i += 1
        time.sleep(0.01)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cfg', type=str, default='config/yolov3-spp.cfg', help='*.cfg path')
    parser.add_argument('--names', type=str, default='config/coco.names', help='*.names path')
    parser.add_argument('--weights', type=str, default='weights/best.pt', help='weights path')
    parser.add_argument('--source', type=str, default='videos/2020-07-07 21-23-58.mp4', help='source')  # input file/folder, 0 for webcam
    parser.add_argument('--output', type=str, default='output', help='output folder')  # output folder
    parser.add_argument('--img-size', type=int, default=1024, help='inference size (pixels)')
    parser.add_argument('--conf-thres', type=float, default=0.3, help='object confidence threshold')
    parser.add_argument('--iou-thres', type=float, default=0.6, help='IOU threshold for NMS')
    parser.add_argument('--fourcc', type=str, default='mp4v', help='output video codec (verify ffmpeg support)')
    parser.add_argument('--half', action='store_true', help='half precision FP16 inference')
    parser.add_argument('--device', default='', help='device id (i.e. 0 or 0,1) or cpu')
    parser.add_argument('--view-img', action='store_true', help='display results')
    parser.add_argument('--save-txt', action='store_true', help='save results to *.txt')
    parser.add_argument('--classes', nargs='+', type=int, help='filter by class')
    parser.add_argument('--agnostic-nms', action='store_true', help='class-agnostic NMS')
    opt = parser.parse_args()
    print(opt)

    trackings = queue.Queue()
    ai_thread = threading.Thread(target=game_ai, args=(trackings,))
    ai_thread.start()
    try:
        with torch.no_grad():
            detect(opt=opt, save_img=False, prediction=trackings)
        ai_thread.join()
    except:
        ai_thread.join()
