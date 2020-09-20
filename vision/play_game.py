import argparse
import threading
import queue
import time
import pyautogui
from detect import *



# def game_ai(tracking_list):
#     center_screen = (pyautogui.size()[0]/2 , pyautogui.size()[1]/2)
#     pyautogui.FAILSAFE = False
#     while True:
#         while not tracking_list.empty():
#             i = 0
#             targets = tracking_list.get()
#             center_x = int((targets[i][1][0] + targets[i][2][0]) / 2)
#             center_y = int((targets[i][1][1] + targets[i][2][1]) / 2)
#             # Check the target to be yourself, if it is, move on to the next target
#             if (abs(center_screen[0] - center_x) + abs(center_screen[1] - center_y)) > 50 \
#                 and targets[i][3] > 0.3: 
#                 pyautogui.mouseDown(x=center_x, y=center_y)
#                 time.sleep(0.01)
#                 pyautogui.mouseUp()
#                 # pyautogui.moveTo(x=center_x, y=center_y)
#                 print("Firing at ", center_x, center_y)
#                 break
#             else:
#                 i += 1
#         time.sleep(0.01)



class Game_AI(threading.Thread):
    def __init__(self, name):
        threading.Thread.__init__(self)
        self.name = name
        self.center_screen = (pyautogui.size()[0]/2 , pyautogui.size()[1]/2)
        pyautogui.FAILSAFE = False

    def run(self):
        global tracking_list
        global tracking_list_cv
        while True:
            tracking_list_cv.acquire()
            if tracking_list:       # if not empty
                # print(tracking_list)
                for target in tracking_list.values():
                    center_x = target.x
                    center_y = target.y
                    # Check the target to be yourself, if it is, move on to the next target
                    if (abs(self.center_screen[0] - center_x) + abs(self.center_screen[1] - center_y)) > 50 \
                        and target.conf > 0.3 and target.tracking_id != -1: 
                        pyautogui.mouseDown(x=center_x, y=center_y)
                        time.sleep(0.005)
                        pyautogui.mouseUp()
                        pyautogui.mouseDown(x=center_x, y=center_y)
                        time.sleep(0.005)
                        pyautogui.mouseUp()
                        # pyautogui.moveTo(x=center_x, y=center_y)
                        print("Firing at ", center_x, center_y)
                        break
                tracking_list.clear()
            else:
                tracking_list_cv.wait()
            tracking_list_cv.release()
            # time.sleep(0.01)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--weights', nargs='+', type=str, default='weights/bests.pt', help='model.pt path(s)')
    parser.add_argument('--source', type=str, default='screen', help='source')  # file/folder, 0 for webcam ../Drone-Yolo/video/cuttingdata3.mp4
    parser.add_argument('--output', type=str, default='inference/output', help='output folder')  # output folder
    parser.add_argument('--img-size', type=int, default=1024, help='inference size (pixels)')
    parser.add_argument('--conf-thres', type=float, default=0.4, help='object confidence threshold')
    parser.add_argument('--iou-thres', type=float, default=0.3, help='IOU threshold for NMS')
    parser.add_argument('--device', default='', help='cuda device, i.e. 0 or 0,1,2,3 or cpu')
    parser.add_argument('--view-img', action='store_true', help='display results')
    parser.add_argument('--save-txt', action='store_true', help='save results to *.txt')
    parser.add_argument('--classes', nargs='+', type=int, help='filter by class: --class 0, or --class 0 2 3')
    parser.add_argument('--agnostic-nms', action='store_true', help='class-agnostic NMS')
    parser.add_argument('--augment', action='store_true', help='augmented inference')
    parser.add_argument('--update', action='store_true', help='update all models')
    opt = parser.parse_args()
    print(opt)

    # with torch.no_grad():
    #     if opt.update:  # update all models (to fix SourceChangeWarning)
    #         for opt.weights in ['yolov5s.pt', 'yolov5m.pt', 'yolov5l.pt', 'yolov5x.pt', 'yolov3-spp.pt']:
    #             detect()
    #             strip_optimizer(opt.weights)
    #     else:
    #         detect()


    trackings = queue.Queue()
    # ai_thread = threading.Thread(target=game_ai, args=(trackings,))
    # ai_thread.start()
    ai_thread = Game_AI("main ai")
    ai_thread.start()
    try:
        with torch.no_grad():
            detect(opt=opt, save_img=False, prediction=trackings)
        ai_thread.join()
    except:
        ai_thread.join()
