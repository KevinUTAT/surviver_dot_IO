import argparse
import queue
import copy
import threading

import torch.backends.cudnn as cudnn

from models.experimental import *
from utils.datasets import *
from utils.utils import *
from sort import *

global tracking_list
tracking_list = {}
global tracking_list_cv
tracking_list_cv = threading.Condition()


class Player(object):
    def __init__(self, tracking_id=-1):
        self.tracking_id = tracking_id
        self.conf = -1

        self.x = -1
        self.y = -1
        self.w = -1
        self.h = -1
        self.r = -1
        
        self.time = time.time()
        self.speed = 0

        self.x_prev = -1
        self.y_prev = -1
        self.w_prev = -1
        self.h_prev = -1

        self.time_prev = time.time() - 1


    def update(self, left, top, right, bottom):
        self.x_prev = self.x
        self.y_prev = self.y
        self.w_prev = self.w
        self.h_prev = self.h
        self.time_prev = self.time

        self.x = int((left + right)/2)
        self.y = int((top + bottom)/2)
        self.w = int(abs(right - left))
        self.h = int(abs(bottom - top))
        self.time = time.time()



    
    def __str__(self):
        position_str = '(' + str(self.x) + ', ' + str(self.y) + ')'
        size_str = '(' + str(self.w) + 'x' + str(self.h) + ')'
        speed_str = str(self.speed) + 'pix/s'
        return position_str + ' : ' + size_str + ' @' + speed_str
    

    def __repr__(self):
        return self.__str__()
    


def detect(opt, prediction, save_img=False):
    out, source, weights, view_img, save_txt, imgsz = \
        opt.output, opt.source, opt.weights, opt.view_img, opt.save_txt, opt.img_size
    webcam = source == '0' or source.startswith('rtsp') or source.startswith('http') or source.endswith('.txt')
    screen_cap = source == 'screen' or source == 'Screen'

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

        # Inference
        t1 = torch_utils.time_synchronized()
        pred = model(img, augment=opt.augment)[0]

        # Apply NMS
        pred = non_max_suppression(pred, opt.conf_thres, opt.iou_thres, classes=opt.classes, agnostic=opt.agnostic_nms)
        t2 = torch_utils.time_synchronized()

        # Apply Classifier
        if classify:
            pred = apply_classifier(pred, modelc, img, im0s)

        # Apply motion tracker
        if pred is not None:
            tracked_objs = moTrack.update(pred)
            # Note that tracked_objs here is in the reversed order of pred
            # so we reverse it:
            tracked_objs = tracked_objs[::-1] 
            # if len(tracked_objs) >= 2:
            #     print(pred)
            #     print(tracked_objs)

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
                # Rescale boxes from img_size to im0 size
                det[:, :4] = scale_coords(img.shape[2:], det[:, :4], im0.shape).round()

                # Print results
                for c in det[:, -1].unique():
                    n = (det[:, -1] == c).sum()  # detections per class
                    s += '%g %ss, ' % (n, names[int(c)])  # add to string

                # output results
                targets_out = []
                global tracking_list
                global tracking_list_cv
                tracking_list_cv.acquire()
                # tracking_list.clear()
                # populate the tracking list
                det_idx = 0
                for *xyxy, conf, cls in det:
                    if len(tracked_objs) > det_idx:
                        current_track_id = tracked_objs[det_idx][4]
                        # create a new player object if its tracking id is new
                        if (current_track_id not in tracking_list):
                            new_player = Player(current_track_id)
                            new_player.update(xyxy[0], xyxy[1], xyxy[2], xyxy[3])
                            tracking_list[current_track_id] = new_player
                        # if its a existing id, update current object
                        else:
                            tracking_list[current_track_id].update(xyxy[0], xyxy[1], xyxy[2], xyxy[3])
                    det_idx += 1

                # Write results
                det_idx = 0
                for *xyxy, conf, cls in det:
                    c1, c2 = (int(xyxy[0]), int(xyxy[1])), (int(xyxy[2]), int(xyxy[3]))
                    # target = [int(cls), c1, c2, float(conf)]    # a single target predection
                    # print(target)
                    # tracking_list.append(target)      # add to the list
                    if save_txt:  # Write to file
                        xywh = (xyxy2xywh(torch.tensor(xyxy).view(1, 4)) / gn).view(-1).tolist()  # normalized xywh
                        with open(txt_path + '.txt', 'a') as f:
                            f.write(('%g ' * 5 + '\n') % (cls, *xywh))  # label format

                    if save_img or view_img:  # Add bbox to image
                        label = '%s %.2f' % (names[int(cls)], conf)
                        if len(tracked_objs) > det_idx:
                            if opt.debug:
                                plot_one_box(xyxy, im0, label=label, track_id=tracked_objs[det_idx][4], \
                                    color=colors[int(cls)], line_thickness=1)
                            plot_one_box(xyxy, im0, label=label, track_id=tracked_objs[det_idx][4], color=colors[int(cls)], line_thickness=1)
                        else:
                            plot_one_box(xyxy, im0, label=label, color=colors[int(cls)], line_thickness=1)
                    det_idx += 1
                # prediction.put(targets_out)
                
                # tracking_list = copy.deepcopy(targets_out)
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--weights', nargs='+', type=str, default='weights/best.pt', help='model.pt path(s)')
    parser.add_argument('--source', type=str, default='videos/surviv.io - 2d battle royale game - Google Chrome 2020-07-14 21-27-29.mp4', help='source')  # file/folder, 0 for webcam ../Drone-Yolo/video/cuttingdata3.mp4
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
