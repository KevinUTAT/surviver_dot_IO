import sys
from os import listdir, system, execl
import os.path
import PySide2
from PySide2.QtWidgets import QGraphicsScene
from PySide2.QtGui import QBrush, QPen, QFont



class BBox(object):
    def __init__(self, xywh, class_num):
        # make sure xywh = [centerX, centerY, width, height]

        self.top = int(xywh[1] - xywh[3]/2)
        self.bottom = int(xywh[1] + xywh[3]/2) 
        self.left = int(xywh[0] - xywh[2]/2)
        self.right = int(xywh[0] + xywh[2]/2)

        self.cls = class_num


    def drew_in_scene(self, scene_ref):
        # pass in a reference to the sence
        # then this function will drew on the scene
        blueBrush = QBrush(PySide2.QtCore.Qt.blue)
        bluePen = QPen(PySide2.QtCore.Qt.blue)

        tl = scene_ref.addRect(self.left-5, self.top-5, 10,10, brush=blueBrush)
        tr = scene_ref.addRect(self.right-5, self.top-5, 10,10, brush=blueBrush)
        bl = scene_ref.addRect(self.left-5, self.bottom-5, 10,10, brush=blueBrush)
        br = scene_ref.addRect(self.right-5, self.bottom-5, 10,10, brush=blueBrush)

        top_line    = scene_ref.addLine(self.left, self.top, self.right, self.top, pen=bluePen)
        bottom_line = scene_ref.addLine(self.left, self.bottom, self.right, self.bottom, pen=bluePen)
        left_line   = scene_ref.addLine(self.left, self.top, self.left, self.bottom, pen=bluePen)
        right_line  = scene_ref.addLine(self.right, self.top, self.right, self.bottom, pen=bluePen)


