import argparse
import time
from pathlib import Path
import queue
import copy
import threading
import math

import cv2
import torch
import torch.backends.cudnn as cudnn
import datetime

from models.experimental import attempt_load
from utils.datasets import LoadStreams, LoadImages
from utils.general import check_img_size, check_requirements, check_imshow, non_max_suppression, apply_classifier, \
    scale_coords, xyxy2xywh, strip_optimizer, set_logging, increment_path, save_one_box
from utils.plots import colors, plot_one_box, plot_debug_info
from utils.torch_utils import select_device, load_classifier, time_synchronized
from sort import *
from elements import Player, Tree

active_output_dir = "active/images/"
active_label_dir = "active/labels/"

# global tracking_list
tracking_list = {}
# global tracking_list_cv
tracking_list_cv = threading.Condition()

# list of trees in a frame
tree_list = []
tree_list_cv = threading.Condition()




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

def detect(opt):
    source, weights, view_img, save_txt, imgsz = opt.source, opt.weights, opt.view_img, opt.save_txt, opt.img_size
    save_img = not opt.nosave and not source.endswith('.txt')  # save inference images
    webcam = source.isnumeric() or source.endswith('.txt') or source.lower().startswith(
        ('rtsp://', 'rtmp://', 'http://', 'https://'))
    screen_cap = source == 'screen' or source == 'Screen'
    active_learn = opt.active > 0.05
    active_learn_thres = opt.active

    if screen_cap and not opt.record:
        save_img = False

    # Directories
    save_dir = increment_path(Path(opt.project) / opt.name, exist_ok=opt.exist_ok)  # increment run
    (save_dir / 'labels' if save_txt else save_dir).mkdir(parents=True, exist_ok=True)  # make dir

    # Initialize
    set_logging()
    device = select_device(opt.device)
    half = device.type != 'cpu'  # half precision only supported on CUDA

    # Load model
    model = attempt_load(weights, map_location=device)  # load FP32 model
    stride = int(model.stride.max())  # model stride
    imgsz = check_img_size(imgsz, s=stride)  # check img_size
    names = model.module.names if hasattr(model, 'module') else model.names  # get class names
    if half:
        model.half()  # to FP16

    # Second-stage classifier
    classify = False
    if classify:
        modelc = load_classifier(name='resnet101', n=2)  # initialize
        modelc.load_state_dict(torch.load('weights/resnet101.pt', map_location=device)['model']).to(device).eval()

    # Set Dataloader
    vid_path, vid_writer = None, None
    if webcam or screen_cap:
        if view_img or (not screen_cap):
            view_img = check_imshow()
        cudnn.benchmark = True  # set True to speed up constant image size inference
        dataset = LoadStreams(source, img_size=imgsz, stride=stride)
    else:
        dataset = LoadImages(source, img_size=imgsz, stride=stride)

    # Run inference
    moTrack = Sort() # the motion tracker
    if device.type != 'cpu':
        model(torch.zeros(1, 3, imgsz, imgsz).to(device).type_as(next(model.parameters())))  # run once
    t0 = time.time()
    for path, img, im0s, vid_cap in dataset:
        img = torch.from_numpy(img).to(device)
        img = img.half() if half else img.float()  # uint8 to fp16/32
        img /= 255.0  # 0 - 255 to 0.0 - 1.0
        if img.ndimension() == 3:
            img = img.unsqueeze(0)

        # Inference
        t1 = time_synchronized()
        pred = model(img, augment=opt.augment)[0]

        # Apply NMS
        pred = non_max_suppression(pred, opt.conf_thres, opt.iou_thres, opt.classes, opt.agnostic_nms,
                                   max_det=opt.max_det)
        t2 = time_synchronized()

        # Apply Classifier
        if classify:
            pred = apply_classifier(pred, modelc, img, im0s)

        # setup shared data structure with game ai
        global tracking_list
        global tracking_list_cv
        clean_traking_list()
        age_traking_list()

        global tree_list
        global tree_list_cv
        tree_list = []

        # Process detections
        for i, det in enumerate(pred):  # detections per image
            if webcam or screen_cap:  # batch_size >= 1
                p, s, im0, frame = path[i], f'{i}: ', im0s[i].copy(), dataset.count
            else:
                p, s, im0, frame = path, '', im0s.copy(), getattr(dataset, 'frame', 0)

            p = Path(p)  # to Path
            save_path = str(save_dir / p.name)  # img.jpg
            txt_path = str(save_dir / 'labels' / p.stem) + ('' if dataset.mode == 'image' else f'_{frame}')  # img.txt
            s += '%gx%g ' % img.shape[2:]  # print string
            gn = torch.tensor(im0.shape)[[1, 0, 1, 0]]  # normalization gain whwh
            imc = im0.copy() if opt.save_crop else im0  # for opt.save_crop
            if len(det):
                # apply motion tracker on each class
                tracked_objs = moTrack.update(det)
                # Note that tracked_objs here is in the reversed order of det
                # so we need to reorder it to match det
                det_idex = 0
                ordered_tracked_objs = []
                for *xyxy, conf, cls in reversed(det):
                    # if the end screen is detected, end the program
                    if int(cls) == 1 and conf > 0.8 and screen_cap:
                        return
                    match_found = False
                    for tracked_obj in tracked_objs:
                        x_match = abs(tracked_obj[0] - xyxy[0]) < 3
                        y_match = abs(tracked_obj[1] - xyxy[1]) < 3
                        if x_match and y_match and (int(cls) == 0):
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
                    s += f"{n} {names[int(c)]}{'s' * (n > 1)}, "  # add to string

                # output results
                targets_out = []

                # None blocking so detection flaw wont be effected
                # if the list are currently used, just don't up date it
                if not tracking_list_cv.acquire(blocking=False):
                    continue
                # print("Lock acquired")

                active_frame = False
                det_idx = 0
                for *xyxy, conf, cls in reversed(det):
                    if len(ordered_tracked_objs) > det_idx:
                        current_track_id = ordered_tracked_objs[det_idx][4]
                        # create a new player object if its tracking id is new
                        if (current_track_id not in tracking_list) and (int(cls) == 0):
                            new_player = Player(current_track_id)
                            new_player.update(xyxy[0], xyxy[1], xyxy[2], xyxy[3], conf, time_stemp=t2)
                            tracking_list[current_track_id] = new_player
                        # if its a existing id, update current object
                        elif int(cls) == 0:
                            tracking_list[current_track_id].update(xyxy[0], xyxy[1], xyxy[2], xyxy[3], conf, time_stemp=t2)
                        # else:
                        #     print("Unknown Class: " + str(cls))


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

                    # record all trees
                    if int(cls) == 2:
                        new_tree = Tree()
                        new_tree.update(xyxy[0], xyxy[1], xyxy[2], xyxy[3], conf)
                        new_tree.update_r()
                        tree_list.append(new_tree)

                    det_idx += 1
                # print(tracking_list)
                tracking_list_cv.notify_all()
                tracking_list_cv.release()

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
                for *xyxy, conf, cls in reversed(det):
                    if save_txt:  # Write to file
                        xywh = (xyxy2xywh(torch.tensor(xyxy).view(1, 4)) / gn).view(-1).tolist()  # normalized xywh
                        line = (cls, *xywh, conf) if opt.save_conf else (cls, *xywh)  # label format
                        with open(txt_path + '.txt', 'a') as f:
                            f.write(('%g ' * len(line)).rstrip() % line + '\n')

                    if save_img or opt.save_crop or view_img:  # Add bbox to image
                        c = int(cls)  # integer class
                        label = None if opt.hide_labels else (names[c] if opt.hide_conf else f'{names[c]} {conf:.2f}')
                        if len(ordered_tracked_objs) > det_idx:
                            current_track_id = ordered_tracked_objs[det_idx][4]
                            if opt.debug and (current_track_id != -1):
                                plot_one_box(xyxy, im0, label=label, track_id=current_track_id, \
                                    color=colors(c, True), line_thickness=1, \
                                        speed=tracking_list[current_track_id].speed, \
                                        velo_x=tracking_list[current_track_id].velocity_vec_x, \
                                        velo_y=tracking_list[current_track_id].velocity_vec_y)
                            plot_one_box(xyxy, im0, label=label, track_id=current_track_id, color=colors(c, True), line_thickness=1)
                        else:
                            plot_one_box(xyxy, im0, label=label, color=colors(c, True), line_thickness=1)
                        if opt.save_crop:
                            save_one_box(xyxy, imc, file=save_dir / 'crops' / names[c] / f'{p.stem}.jpg', BGR=True)
                    det_idx += 1
                # tracking_list_cv.notify_all()
                # tracking_list_cv.release()
                # print("Lock released")

            # print debug info to each frame
            if opt.debug:
                plot_debug_info(im0, tracking_list, tree_list)

            # Print time (inference + NMS)
            print(f'{s}Done. ({t2 - t1:.3f}s)')

            # Stream results
            if view_img:
                cv2.imshow(str(p), im0)
                cv2.waitKey(1)  # 1 millisecond

            # Save results (image with detections)
            if save_img:
                if dataset.mode == 'image' and not screen_cap:
                    cv2.imwrite(save_path, im0)
                else:  # 'video' or 'stream'
                    if vid_path != save_path:  # new video
                        vid_path = save_path
                        if isinstance(vid_writer, cv2.VideoWriter):
                            vid_writer.release()  # release previous video writer
                        if vid_cap:  # video
                            fps = vid_cap.get(cv2.CAP_PROP_FPS)
                            w = int(vid_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                            h = int(vid_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        else:  # stream
                            fps, w, h = 30, im0.shape[1], im0.shape[0]
                            save_path += '.mp4'
                        vid_writer = cv2.VideoWriter(save_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
                    vid_writer.write(im0)

    if save_txt or save_img:
        s = f"\n{len(list(save_dir.glob('labels/*.txt')))} labels saved to {save_dir / 'labels'}" if save_txt else ''
        print(f"Results saved to {save_dir}{s}")

    print(f'Done. ({time.time() - t0:.3f}s)')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--weights', nargs='+', type=str, default='weights/bestm.pt', help='model.pt path(s)')
    parser.add_argument('--source', type=str, default='videos/surviv.io2020-11-06_22-41-45.mp4', help='source')  # file/folder, 0 for webcam
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
    parser.add_argument('--record', action='store_true', help='Record screen cap')
    opt = parser.parse_args()
    print(opt)
    # check_requirements(exclude=('tensorboard', 'pycocotools', 'thop'))

    with torch.no_grad():
        if opt.update:  # update all models (to fix SourceChangeWarning)
            for opt.weights in ['yolov5s.pt', 'yolov5m.pt', 'yolov5l.pt', 'yolov5x.pt']:
                detect(opt=opt)
                strip_optimizer(opt.weights)
        else:
            detect(opt=opt)
