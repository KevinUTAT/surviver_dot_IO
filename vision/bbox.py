import sys
from os import listdir, system, execl
import os.path
import PySide2
from PySide2.QtWidgets import QGraphicsScene
from PySide2.QtGui import QBrush, QPen, QFont



class BBox(object):
    def __init__(self, xywh, imgSizeWH, class_num):
        # make sure xywh = [centerX, centerY, width, height]
        self.xywh = xywh
        self.imgSizeWH = imgSizeWH

        self.top = int(xywh[1] - xywh[3]/2)
        self.bottom = int(xywh[1] + xywh[3]/2) 
        self.left = int(xywh[0] - xywh[2]/2)
        self.right = int(xywh[0] + xywh[2]/2)

        self.cls = class_num


    def drew_in_scene(self, scene_ref, highlight=False):
        # pass in a reference to the sence
        # then this function will drew on the scene
        blueBrush = QBrush(PySide2.QtCore.Qt.blue)
        bluePen = QPen(PySide2.QtCore.Qt.blue)
        highlightPen = QPen(PySide2.QtCore.Qt.blue)
        highlightPen.setWidth(5)

        tl = scene_ref.addRect(self.left-5, self.top-5, 10,10, brush=blueBrush)
        tr = scene_ref.addRect(self.right-5, self.top-5, 10,10, brush=blueBrush)
        bl = scene_ref.addRect(self.left-5, self.bottom-5, 10,10, brush=blueBrush)
        br = scene_ref.addRect(self.right-5, self.bottom-5, 10,10, brush=blueBrush)

        if highlight:
            top_line    = scene_ref.addLine(self.left, self.top, self.right, self.top, pen=highlightPen)
            bottom_line = scene_ref.addLine(self.left, self.bottom, self.right, self.bottom, pen=highlightPen)
            left_line   = scene_ref.addLine(self.left, self.top, self.left, self.bottom, pen=highlightPen)
            right_line  = scene_ref.addLine(self.right, self.top, self.right, self.bottom, pen=highlightPen)
        else:
            top_line    = scene_ref.addLine(self.left, self.top, self.right, self.top, pen=bluePen)
            bottom_line = scene_ref.addLine(self.left, self.bottom, self.right, self.bottom, pen=bluePen)
            left_line   = scene_ref.addLine(self.left, self.top, self.left, self.bottom, pen=bluePen)
            right_line  = scene_ref.addLine(self.right, self.top, self.right, self.bottom, pen=bluePen)


        # return a string representing one line of label
    def to_label_str(self):
        label_str = ""
        label_str += str(self.cls)
        label_str += " "
        label_str += str(self.xywh[0]/self.imgSizeWH[0])
        label_str += " "
        label_str += str(self.xywh[1]/self.imgSizeWH[1])
        label_str += " "
        label_str += str(self.xywh[2]/self.imgSizeWH[0])
        label_str += " "
        label_str += str(self.xywh[3]/self.imgSizeWH[1])
        return label_str


