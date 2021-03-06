import argparse
import queue
import copy
import threading

import torch.backends.cudnn as cudnn
import datetime

from models.experimental import *
from utils.datasets import *
from utils.utils import *
from sort import *

active_output_dir = "active/images/"
active_label_dir = "active/labels/"

global tracking_list
tracking_list = {}
global tracking_list_cv
tracking_list_cv = threading.Condition()


class Player(object):
    class_num = 0

    def __init__(self, tracking_id=-1):
        self.tracking_id = tracking_id
        self.conf = -1.0

        self.x = -1
        self.y = -1
        self.w = -1
        self.h = -1
        self.r = -1
        
        self.time = time.time()
        self.speed = 0
        # x, y components of velocity
        # Note the positive direction is down and right
        self.velocity_vec_x = 0
        self.velocity_vec_y = 0

        self.x_prev = -1
        self.y_prev = -1
        self.w_prev = -1
        self.h_prev = -1

        self.time_prev = time.time()

        self.interval = 0
        self.interval_prev = 0

        # tracking how long have the Player being inactivate
        self.obsolete = 0


    def update(self, left, top, right, bottom, conf, time_stemp=0):
        self.x_prev = self.x
        self.y_prev = self.y
        self.w_prev = self.w
        self.h_prev = self.h
        self.time_prev = self.time

        self.x = int((left + right)/2)
        self.y = int((top + bottom)/2)
        self.w = int(abs(right - left))
        self.h = int(abs(bottom - top))
        self.conf = conf
        if not time_stemp:
            self.time = time.time()
        else:
            self.time = time_stemp

        # filtering time inerval
        self.interval_prev = self.interval
        self.interval = float(self.time - self.time_prev)
        # if (abs(self.interval - self.interval_prev) / self.interval_prev) > 1.5:
        #     self.interval = self.interval_prev

        displacement = math.sqrt((self.x - self.x_prev) ** 2 + (self.y - self.y_prev) ** 2)
        if (float(self.time - self.time_prev) > 0) and \
            self.x_prev != -1 and self.y_prev != -1:
            # only if when a reasonable speed can be calculated, calculats it
            self.speed = displacement / self.interval
            self.velocity_vec_x = (self.x - self.x_prev) / self.interval
            self.velocity_vec_y = (self.y - self.y_prev) / self.interval
        else:
            self.speed = 0
            self.velocity_vec_x = 0
            self.velocity_vec_y = 0

        self.obsolete = 0

        # print(self.interval)

        # self.velocity_vec_x = (self.x - self.x_prev) / float(self.time - self.time_prev)
        # self.velocity_vec_y = (self.y - self.y_prev) / float(self.time - self.time_prev)
 

    # This return a projected position in the future of leading time
    # it is simpelly current (position + velocity * leading time)
    def position_projection(self, leading_time=0):
        proj_x = self.x + self.velocity_vec_x * leading_time
        proj_y = self.y + self.velocity_vec_y * leading_time
        return proj_x, proj_y

    
    def __str__(self):
        position_str = '(' + str(self.x) + ', ' + str(self.y) + ')'
        size_str = '(' + str(self.w) + 'x' + str(self.h) + ')'
        speed_str = str(self.speed) + 'pix/s'
        return position_str + ' : ' + size_str + ' @' + speed_str \
            + ' conf:' + str(int(float(self.conf)*100)) + '\n'
    

    def __repr__(self):
        return self.__str__()


def age_traking_list():
    # age all players by 1
    for target in tracking_list.values():
        target.obsolete += 1


def clean_traking_list():
    # remove players that is inactive
    obsoletes = []
    for track_id, target in tracking_list.items():
        if target.obsolete or target.tracking_id == -1:
            obsoletes.append(track_id)
    for tid in obsoletes:
        del tracking_list[tid]
    


def detect(opt, prediction, save_img=False, progress=None):
    out, source, weights, view_img, save_txt, imgsz = \
        opt.output, opt.source, opt.weights, opt.view_img, opt.save_txt, opt.img_size
    webcam = source == '0' or source.startswith('rtsp') or source.startswith('http') or source.endswith('.txt')
    screen_cap = source == 'screen' or source == 'Screen'
    active_learn = opt.active > 0.05
    active_learn_thres = opt.active

    # Initialize
    device = torch_utils.select_device(opt.device)
    if os.path.exists(out):
        shutil.rmtree(out)  # delete output folder
    os.makedirs(out)  # make new output folder
    half = device.type != 'cpu'  # half precision only supported on CUDA

    # Load model
    model = attempt_load(weights, map_location=device)  # load FP32 model
    imgsz = check_img_size(imgsz, s=model.stride.max())  # check img_size
    if half:
        model.half()  # to FP16

    # Second-stage classifier
    classify = False
    if classify:
        modelc = torch_utils.load_classifier(name='resnet101', n=2)  # initialize
        modelc.load_state_dict(torch.load('weights/resnet101.pt', map_location=device)['model'])  # load weights
        modelc.to(device).eval()

    # Set Dataloader
    vid_path, vid_writer = None, None
    if webcam or screen_cap:
        # view_img = True
        # save_img = True
        cudnn.benchmark = True  # set True to speed up constant image size inference
        dataset = LoadStreams(source, img_size=imgsz)
    else:
        save_img = True
        dataset = LoadImages(source, img_size=imgsz)

    # Get names and colors
    names = model.module.names if hasattr(model, 'module') else model.names
    colors = [[random.randint(0, 255) for _ in range(3)] for _ in range(len(names))]

    frame_count = 0

    # Run inference
    moTrack = Sort()
    t0 = time.time()
    img = torch.zeros((1, 3, imgsz, imgsz), device=device)  # init img
    _ = model(img.half() if half else img) if device.type != 'cpu' else None  # run once
    for path, img, im0s, vid_cap in dataset:
        img = torch.from_numpy(img).to(device)
        img = img.half() if half else img.float()  # uint8 to fp16/32
        img /= 255.0  # 0 - 255 to 0.0 - 1.0
        if img.ndimension() == 3:
            img = img.unsqueeze(0)

        # update progress
        if not progress:
            frame_count += 1
            progress.setValue(int(frame_count / len(dataset)))
            if progress.wasCanceled():
                    return

        # Inference
        t1 = torch_utils.time_synchronized()
        pred = model(img, augment=opt.augment)[0]

        # Apply NMS
        pred = non_max_suppression(pred, opt.conf_thres, opt.iou_thres, classes=opt.classes, agnostic=opt.agnostic_nms)
        t2 = torch_utils.time_synchronized()

        # Apply Classifier
        if classify:
            pred = apply_classifier(pred, modelc, img, im0s)

        # # Apply motion tracker
        # if pred is not None:
        #     tracked_objs = moTrack.update(pred)
        #     # Note that tracked_objs here is in the reversed order of pred
        #     # so we reverse it:
        #     tracked_objs = tracked_objs[::-1] 
        #     if len(tracked_objs) >= 2:
        #         print(pred)
        #         print(tracked_objs)

        global tracking_list
        global tracking_list_cv
        # tracking_list_cv.acquire()
        # tracking_list.clear()
        clean_traking_list()
        age_traking_list()
        # tracking_list_cv.notify_all()
        # tracking_list_cv.release()

        # Process detections
        for i, det in enumerate(pred):  # detections per image
            if webcam or screen_cap:  # batch_size >= 1
                p, s, im0 = path[i], '%g: ' % i, im0s[i].copy()
            else:
                p, s, im0 = path, '', im0s

            save_path = str(Path(out) / Path(p).name)
            txt_path = str(Path(out) / Path(p).stem) + ('_%g' % dataset.frame if dataset.mode == 'video' else '')
            s += '%gx%g ' % img.shape[2:]  # print string
            gn = torch.tensor(im0.shape)[[1, 0, 1, 0]]  # normalization gain whwh
            if det is not None and len(det):
                # apply motion tracker on each class
                tracked_objs = moTrack.update(det)
                # Note that tracked_objs here is in the reversed order of det
                # so we need to reorder it to match det
                det_idex = 0
                ordered_tracked_objs = []
                for *xyxy, conf, cls in det:
                    # if the end screen is detected, end the program
                    if int(cls) == 1 and conf > 0.8 and screen_cap:
                        return
                    match_found = False
                    for tracked_obj in tracked_objs:
                        x_match = abs(tracked_obj[0] - xyxy[0]) < 3
                        y_match = abs(tracked_obj[1] - xyxy[1]) < 3
                        if x_match and y_match:
                            ordered_tracked_objs.append(tracked_obj)
                            match_found = True
                            break
                        else:
                            match_found = False
                    # if SORT cannot track the object, assign id -1
                    if not match_found:
                        ordered_tracked_objs.append([0,0,0,0,-1])

                # Rescale boxes from img_size to im0 size
                det[:, :4] = scale_coords(img.shape[2:], det[:, :4], im0.shape).round()

                # Print results
                for c in det[:, -1].unique():
                    n = (det[:, -1] == c).sum()  # detections per class
                    s += '%g %ss, ' % (n, names[int(c)])  # add to string

                # output results
                targets_out = []
                # global tracking_list
                # global tracking_list_cv
                tracking_list_cv.acquire()
                # tracking_list.clear()
                # populate the tracking list
                active_frame = False
                det_idx = 0
                for *xyxy, conf, cls in det:
                    if len(ordered_tracked_objs) > det_idx:
                        # current_track_id = tracked_objs[det_idx][4]
                        # current_track_id = -1
                        # for tracked_obj in tracked_objs:
                        #     x_match = (tracked_obj[0] - xyxy[0]) < 2
                        #     y_match = (tracked_obj[1] - xyxy[1]) < 2
                        #     if x_match and y_match:
                        #         current_track_id = tracked_obj[4]
                        current_track_id = ordered_tracked_objs[det_idx][4]
                        # create a new player object if its tracking id is new
                        if (current_track_id not in tracking_list):
                            new_player = Player(current_track_id)
                            new_player.update(xyxy[0], xyxy[1], xyxy[2], xyxy[3], conf, time_stemp=t2)
                            tracking_list[current_track_id] = new_player
                        # if its a existing id, update current object
                        else:
                            tracking_list[current_track_id].update(xyxy[0], xyxy[1], xyxy[2], xyxy[3], conf, time_stemp=t2)

                    # On completly different note, while we are going through det,
                    # we are going to out put unanotated img for training
                    if active_learn: 
                        if conf < active_learn_thres and conf >= 0.05 and not active_frame:
                            # if object is moving slow (not moving) don't output
                            # this reduce redundent frames output from stationary scene
                            # min_speed = im0.shape[0] / 10
                            # if (len(tracked_objs) > det_idx) and (current_track_id in tracking_list):
                            #     if tracking_list[current_track_id].speed < min_speed:
                            #         det_idx += 1
                            #         continue
                            
                            active_frame =True
                            timestemp = datetime.datetime.now()
                            new_name = timestemp.strftime('%y') + timestemp.strftime('%j') \
                                + timestemp.strftime('%H') + timestemp.strftime('%M') \
                                + timestemp.strftime('%S') + timestemp.strftime('%f') \
                                + '_' + str(int(float(conf)*100))
                            out_dir_name = active_output_dir + new_name + '.png'
                            cv2.imwrite(out_dir_name, im0)
                    det_idx += 1
                # print(tracking_list)

                # output ALL the targets for a active frame
                if active_frame:
                    imh = im0.shape[0]
                    imw = im0.shape[1]
                    with open(active_label_dir + new_name + '.txt', 'a+') as new_label:
                        for target in tracking_list.values():
                            new_label.write(str(target.class_num))  # write class
                            new_label.write(' ')
                            new_label.write(str(target.x/imw))   # write x
                            new_label.write(' ')
                            new_label.write(str(target.y/imh))   # write y
                            new_label.write(' ')
                            new_label.write(str(target.w/imw))   # write w
                            new_label.write(' ')
                            new_label.write(str(target.h/imh))   # write h
                            new_label.write('\n')
                    active_frame = False

                # Write results
                det_idx = 0
                for *xyxy, conf, cls in det:
                    # c1, c2 = (int(xyxy[0]), int(xyxy[1])), (int(xyxy[2]), int(xyxy[3]))
                    # target = [int(cls), c1, c2, float(conf)]    # a single target predection
                    # print(target)
                    # tracking_list.append(target)      # add to the list
                    if save_txt:  # Write to file
                        xywh = (xyxy2xywh(torch.tensor(xyxy).view(1, 4)) / gn).view(-1).tolist()  # normalized xywh
                        with open(txt_path + '.txt', 'a') as f:
                            f.write(('%g ' * 5 + '\n') % (cls, *xywh))  # label format

                    if save_img or view_img:  # Add bbox to image
                        label = '%s %.2f' % (names[int(cls)], conf)
                        if len(ordered_tracked_objs) > det_idx:
                            # current_track_id = -1
                            # for tracked_obj in tracked_objs:
                            #     x_match = abs(tracked_obj[0] - int(xyxy[0])) < 2
                            #     y_match = abs(tracked_obj[1] - int(xyxy[1])) < 2
                            #     # print(tracked_obj[0], int(xyxy[0]))
                            #     # print(tracked_obj[1], int(xyxy[1]))
                            #     # print(xyxy)
                            #     # print(tracked_obj)
                            #     print(x_match, y_match)
                            #     if x_match and y_match:
                            #         current_track_id = tracked_obj[4]
                            current_track_id = ordered_tracked_objs[det_idx][4]
                            if opt.debug:
                                plot_one_box(xyxy, im0, label=label, track_id=current_track_id, \
                                    color=colors[int(cls)], line_thickness=1, \
                                        speed=tracking_list[current_track_id].speed, \
                                        velo_x=tracking_list[current_track_id].velocity_vec_x, \
                                        velo_y=tracking_list[current_track_id].velocity_vec_y)
                            plot_one_box(xyxy, im0, label=label, track_id=current_track_id, color=colors[int(cls)], line_thickness=1)
                        else:
                            plot_one_box(xyxy, im0, label=label, color=colors[int(cls)], line_thickness=1)
                    det_idx += 1
                
                # tracking_list = copy.deepcopy(targets_out)
                # global shots_fired
                # shots_fired = False
                # print("relealock")
                # print(tracking_list)
                tracking_list_cv.notify_all()
                tracking_list_cv.release()

            # Print time (inference + NMS)
            print('%sDone. (%.3fs)' % (s, t2 - t1))

            # Stream results
            if view_img:
                cv2.imshow(p, im0)
                if cv2.waitKey(1) == ord('q'):  # q to quit
                    raise StopIteration

            # Save results (image with detections)
            if save_img:
                if dataset.mode == 'images' and not screen_cap:
                    cv2.imwrite(save_path, im0)
                else:
                    if vid_path != save_path:  # new video
                        vid_path = save_path
                        if isinstance(vid_writer, cv2.VideoWriter):
                            vid_writer.release()  # release previous video writer

                        fourcc = 'mp4v'  # output video codec
                        if screen_cap:
                            fps = 24
                            w = 1920
                            h = 1080
                        else:
                            fps = vid_cap.get(cv2.CAP_PROP_FPS)
                            w = int(vid_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                            h = int(vid_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        vid_writer = cv2.VideoWriter(save_path, cv2.VideoWriter_fourcc(*fourcc), fps, (w, h))
                    vid_writer.write(im0)

    if save_txt or save_img:
        print('Results saved to %s' % os.getcwd() + os.sep + out)
        if platform == 'darwin' and not opt.update:  # MacOS
            os.system('open ' + save_path)

    print('Done. (%.3fs)' % (time.time() - t0))


def run_detect_video(vid_source, progress, active=0.0):
    parser = argparse.ArgumentParser()
    parser.add_argument('--weights', nargs='+', type=str, default='weights/bests.pt', help='model.pt path(s)')
    parser.add_argument('--source', type=str, default=vid_source, help='source')  # file/folder, 0 for webcam ../Drone-Yolo/video/cuttingdata3.mp4
    parser.add_argument('--output', type=str, default='inference/output', help='output folder')  # output folder
    parser.add_argument('--img-size', type=int, default=1024, help='inference size (pixels)')
    parser.add_argument('--conf-thres', type=float, default=0.3, help='object confidence threshold')
    parser.add_argument('--iou-thres', type=float, default=0.3, help='IOU threshold for NMS')
    parser.add_argument('--device', default='', help='cuda device, i.e. 0 or 0,1,2,3 or cpu')
    parser.add_argument('--view-img', action='store_true', help='display results')
    parser.add_argument('--save-txt', action='store_true', help='save results to *.txt')
    parser.add_argument('--classes', nargs='+', type=int, help='filter by class: --class 0, or --class 0 2 3')
    parser.add_argument('--agnostic-nms', action='store_true', help='class-agnostic NMS')
    parser.add_argument('--augment', action='store_true', help='augmented inference')
    parser.add_argument('--update', action='store_true', help='update all models')
    parser.add_argument('--active', type=float, default=active, help='out put threshold, enable active learning ouput when set to non zero')
    parser.add_argument('--debug', type=bool, default=False, help='add more info in image overlay')
    opt = parser.parse_args()
    print(opt)

    outputs = queue.Queue()
    with torch.no_grad():
        if opt.update:  # update all models (to fix SourceChangeWarning)
            for opt.weights in ['yolov5s.pt', 'yolov5m.pt', 'yolov5l.pt', 'yolov5x.pt', 'yolov3-spp.pt']:
                detect(opt=opt, prediction=outputs, progress=progress)
                strip_optimizer(opt.weights)
        else:
            detect(opt=opt, prediction=outputs, progress=progress)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--weights', nargs='+', type=str, default='weights/bests.pt', help='model.pt path(s)')
    parser.add_argument('--source', type=str, default='videos/surviv.io2020-11-06_22-41-45.mp4', help='source')  # file/folder, 0 for webcam ../Drone-Yolo/video/cuttingdata3.mp4
    parser.add_argument('--output', type=str, default='inference/output', help='output folder')  # output folder
    parser.add_argument('--img-size', type=int, default=1024, help='inference size (pixels)')
    parser.add_argument('--conf-thres', type=float, default=0.3, help='object confidence threshold')
    parser.add_argument('--iou-thres', type=float, default=0.3, help='IOU threshold for NMS')
    parser.add_argument('--device', default='', help='cuda device, i.e. 0 or 0,1,2,3 or cpu')
    parser.add_argument('--view-img', action='store_true', help='display results')
    parser.add_argument('--save-txt', action='store_true', help='save results to *.txt')
    parser.add_argument('--classes', nargs='+', type=int, help='filter by class: --class 0, or --class 0 2 3')
    parser.add_argument('--agnostic-nms', action='store_true', help='class-agnostic NMS')
    parser.add_argument('--augment', action='store_true', help='augmented inference')
    parser.add_argument('--update', action='store_true', help='update all models')
    parser.add_argument('--active', type=float, default=0, help='out put threshold, enable active learning ouput when set to non zero')
    parser.add_argument('--debug', type=bool, default=False, help='add more info in image overlay')
    opt = parser.parse_args()
    print(opt)

    outputs = queue.Queue()
    with torch.no_grad():
        if opt.update:  # update all models (to fix SourceChangeWarning)
            for opt.weights in ['yolov5s.pt', 'yolov5m.pt', 'yolov5l.pt', 'yolov5x.pt', 'yolov3-spp.pt']:
                detect(opt=opt, prediction=outputs)
                strip_optimizer(opt.weights)
        else:
            detect(opt=opt, prediction=outputs)
