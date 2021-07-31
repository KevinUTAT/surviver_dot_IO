import time
import math


# for all objects that are detected through YOLO ============================
class Element(object):

    def __init__(self):
        self.conf = -1.0

        # center x, y, w, h
        self.x = -1
        self.y = -1
        self.w = -1
        self.h = -1

        self.r = -1


    def __str__(self):
        position_str = '(' + str(self.x) + ', ' + str(self.y) + ')'
        size_str = '(' + str(self.w) + 'x' + str(self.h) + ')'
        size_str = f"({self.w}x{self.h}, r={self.r})"
        return position_str + ' : ' + size_str \
            + ' conf:' + str(int(float(self.conf)*100)) + '\n'
    

    def __repr__(self):
        return self.__str__()


    def update(self, left, top, right, bottom, conf):
        self.x = int((left + right)/2)
        self.y = int((top + bottom)/2)
        self.w = int(abs(right - left))
        self.h = int(abs(bottom - top))

        self.conf = conf


    def update_xywh(self, xywh, conf):
        self.x = xywh[0]
        self.y = xywh[1]
        self.w = xywh[2]
        self.h = xywh[3]

        self.conf = conf


    def update_r(self):
        self.r = (self.w + self.h) / 4


# for players that can be tracked using SORT =================================
class Player(Element):
    class_num = 0

    def __init__(self, tracking_id=-1):
        super().__init__()
        self.tracking_id = tracking_id
        
        # timestemp of last update
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


    # overloaded to calculate velocity as well
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

    # over write to add speed
    def __str__(self):
        position_str = '(' + str(self.x) + ', ' + str(self.y) + ')'
        size_str = '(' + str(self.w) + 'x' + str(self.h) + ')'
        speed_str = "{:.2f}".format(self.speed) + 'pix/s'
        return position_str + ' : ' + size_str + ' @' + speed_str \
            + ' conf:' + str(int(float(self.conf)*100)) + '\n'
    

# trees as a stationary object =================================================
class Tree(Element):

    def __init__(self):
        super().__init__()

