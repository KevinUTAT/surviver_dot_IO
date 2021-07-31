import argparse
import threading
import queue
import time
import pyautogui
import torch
import numpy
import math
from detect import detect, tracking_list, tracking_list_cv



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
        global program_terminated
        shots_fired = False
        while not program_terminated:
            tracking_list_cv.acquire()
            if (len(tracking_list) > 0) and not shots_fired:       # if not empty
                # print(tracking_list)
                for target in tracking_list.values():

                    center_x = target.x
                    center_y = target.y
                    # Check the target to be yourself, if it is, move on to the next target
                    if (abs(self.center_screen[0] - center_x) + abs(self.center_screen[1] - center_y)) > 50 \
                        and target.conf > 0.3 and target.tracking_id != -1: 
                        # usin deflection
                        center_x, center_y = target.position_projection(0.2)
                        pyautogui.mouseDown(x=center_x, y=center_y)
                        time.sleep(0.005)
                        pyautogui.mouseUp()
                        pyautogui.mouseDown(x=center_x, y=center_y)
                        time.sleep(0.005)
                        pyautogui.mouseUp()
                        # pyautogui.moveTo(x=center_x, y=center_y)
                        print("Firing at ", center_x, center_y)
                        # tracking_list.clear()
                        break

                shots_fired = True
                # tracking_list.clear()
            else:
                tracking_list_cv.wait()
                shots_fired = False
                # print("wakeup")
                # print(shots_fired)
            tracking_list_cv.release()
            # else:
            #     time.sleep(0.005)


# if there is a clear shot to a target, giving a circler obstacle 
# https://stackoverflow.com/questions/1073336/circle-line-segment-collision-detection-algorithm
def circle_in_between(player_x, player_y, target_x, target_y, \
    circle_x, circle_y, circle_r):
    player = numpy.array([player_x, player_y])
    target = numpy.array([target_x, target_y])
    circle = numpy.array([circle_x, circle_y])

    d = target - player
    f = player - circle
    
    a = d.dot(d)
    b = 2 * f.dot(d)
    c = f.dot(f) - circle_r * circle_r

    discriminant = b*b - 4 * a * c
    if discriminant < 0:
        return False
    discriminant = math.sqrt(discriminant)
    t1 = (-b - discriminant) / (2 * a)
    t2 = (-b + discriminant) / (2 * a)

    if t1 >= 0 and t1 <= 1:
        return True
    if t2 >= 0 and t2 <= 1:
        return True
    return False


if __name__ == '__main__':
    # parser = argparse.ArgumentParser()
    # parser.add_argument('--weights', nargs='+', type=str, default='weights/bests.pt', help='model.pt path(s)')
    # parser.add_argument('--source', type=str, default='screen', help='source')  # file/folder, 0 for webcam ../Drone-Yolo/video/cuttingdata3.mp4
    # parser.add_argument('--output', type=str, default='inference/output', help='output folder')  # output folder
    # parser.add_argument('--img-size', type=int, default=1024, help='inference size (pixels)')
    # parser.add_argument('--conf-thres', type=float, default=0.4, help='object confidence threshold')
    # parser.add_argument('--iou-thres', type=float, default=0.3, help='IOU threshold for NMS')
    # parser.add_argument('--device', default='', help='cuda device, i.e. 0 or 0,1,2,3 or cpu')
    # parser.add_argument('--view-img', action='store_true', help='display results')
    # parser.add_argument('--save-txt', action='store_true', help='save results to *.txt')
    # parser.add_argument('--classes', nargs='+', type=int, help='filter by class: --class 0, or --class 0 2 3')
    # parser.add_argument('--agnostic-nms', action='store_true', help='class-agnostic NMS')
    # parser.add_argument('--augment', action='store_true', help='augmented inference')
    # parser.add_argument('--update', action='store_true', help='update all models')
    # parser.add_argument('--active', type=float, default=0, help='out put threshold, enable active learning ouput when set to non zero')
    # parser.add_argument('--debug', type=bool, default=False, help='add more info in image overlay')
    # opt = parser.parse_args()
    # print(opt)


    parser = argparse.ArgumentParser()
    parser.add_argument('--weights', nargs='+', type=str, default='weights/bests.pt', help='model.pt path(s)')
    parser.add_argument('--source', type=str, default='screen', help='source')  # file/folder, 0 for webcam
    parser.add_argument('--img-size', type=int, default=1024, help='inference size (pixels)')
    parser.add_argument('--conf-thres', type=float, default=0.25, help='object confidence threshold')
    parser.add_argument('--iou-thres', type=float, default=0.45, help='IOU threshold for NMS')
    parser.add_argument('--max-det', type=int, default=1000, help='maximum number of detections per image')
    parser.add_argument('--device', default='', help='cuda device, i.e. 0 or 0,1,2,3 or cpu')
    parser.add_argument('--view-img', action='store_true', help='display results')
    parser.add_argument('--save-txt', action='store_true', help='save results to *.txt')
    parser.add_argument('--save-conf', action='store_true', help='save confidences in --save-txt labels')
    parser.add_argument('--save-crop', action='store_true', help='save cropped prediction boxes')
    parser.add_argument('--nosave', action='store_true', help='do not save images/videos')
    parser.add_argument('--classes', nargs='+', type=int, help='filter by class: --class 0, or --class 0 2 3')
    parser.add_argument('--agnostic-nms', action='store_true', help='class-agnostic NMS')
    parser.add_argument('--augment', action='store_true', help='augmented inference')
    parser.add_argument('--update', action='store_true', help='update all models')
    parser.add_argument('--project', default='runs/detect', help='save results to project/name')
    parser.add_argument('--name', default='exp', help='save results to project/name')
    parser.add_argument('--exist-ok', action='store_true', help='existing project/name ok, do not increment')
    parser.add_argument('--line-thickness', default=3, type=int, help='bounding box thickness (pixels)')
    parser.add_argument('--hide-labels', default=False, action='store_true', help='hide labels')
    parser.add_argument('--hide-conf', default=False, action='store_true', help='hide confidences')
    parser.add_argument('--active', type=float, default=0, help='out put threshold, enable active learning ouput when set to non zero')
    parser.add_argument('--debug', type=bool, default=False, help='add more info in image overlay')
    opt = parser.parse_args()
    print(opt)
    # check_requirements(exclude=('tensorboard', 'pycocotools', 'thop'))


    trackings = queue.Queue()
    # ai_thread = threading.Thread(target=game_ai, args=(trackings,))
    # ai_thread.start()
    program_terminated = False
    ai_thread = Game_AI("main ai")
    ai_thread.start()
    try:
        with torch.no_grad():
            detect(opt=opt)
        program_terminated = True
        ai_thread.join()
    except:
        program_terminated = True
        ai_thread.join()
