import sys
from os import listdir, system, execl
import os.path
import copy
import PySide2
from PySide2.QtWidgets import QGraphicsScene
from PySide2.QtGui import QBrush, QPen, QFont, QCursor
from PySide2.QtCore import QLineF, QPointF
from Ancker import Ancker


class BBox(object):
    def __init__(self, xywh, imgSizeWH, class_num):
        self.parent = None
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
        highlightPen = QPen(PySide2.QtCore.Qt.red)
        highlightPen.setWidth(3)

        # 4 ancker points at 4 corners
        # tl = scene_ref.addRect(self.left-5, self.top-5, 10,10, brush=blueBrush)
        # tl.setFlag(PySide2.QtWidgets.QGraphicsItem.ItemIsMovable, True)
        # tr = scene_ref.addRect(self.right-5, self.top-5, 10,10, brush=blueBrush)
        # tr.setFlag(PySide2.QtWidgets.QGraphicsItem.ItemIsMovable, True)
        # bl = scene_ref.addRect(self.left-5, self.bottom-5, 10,10, brush=blueBrush)
        # bl.setFlag(PySide2.QtWidgets.QGraphicsItem.ItemIsMovable, True)
        # br = scene_ref.addRect(self.right-5, self.bottom-5, 10,10, brush=blueBrush)
        # br.setFlag(PySide2.QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.tl = Ancker(self.left-5, self.top-5, 10,10, blueBrush, 'tl', self)
        self.tl.setFlag(PySide2.QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.tl.setCursor(QCursor(PySide2.QtCore.Qt.SizeFDiagCursor))
        scene_ref.addItem(self.tl)
        self.tr = Ancker(self.right-5, self.top-5, 10,10, blueBrush, 'tr', self)
        self.tr.setFlag(PySide2.QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.tr.setCursor(QCursor(PySide2.QtCore.Qt.SizeBDiagCursor))
        scene_ref.addItem(self.tr)
        self.bl = Ancker(self.left-5, self.bottom-5, 10,10, blueBrush, 'bl', self)
        self.bl.setFlag(PySide2.QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.bl.setCursor(QCursor(PySide2.QtCore.Qt.SizeBDiagCursor))
        scene_ref.addItem(self.bl)
        self.br = Ancker(self.right-5, self.bottom-5, 10,10, blueBrush, 'br', self)
        self.br.setFlag(PySide2.QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.br.setCursor(QCursor(PySide2.QtCore.Qt.SizeFDiagCursor))
        scene_ref.addItem(self.br)


        if highlight:
            self.top_line    = scene_ref.addLine(\
                self.left, self.top, self.right, self.top, pen=highlightPen)
            self.bottom_line = scene_ref.addLine(\
                self.left, self.bottom, self.right, self.bottom, pen=highlightPen)
            self.left_line   = scene_ref.addLine(\
                self.left, self.top, self.left, self.bottom, pen=highlightPen)
            self.right_line  = scene_ref.addLine(\
                self.right, self.top, self.right, self.bottom, pen=highlightPen)
        else:
            self.top_line    = scene_ref.addLine(\
                self.left, self.top, self.right, self.top, pen=bluePen)
            self.bottom_line = scene_ref.addLine(\
                self.left, self.bottom, self.right, self.bottom, pen=bluePen)
            self.left_line   = scene_ref.addLine(\
                self.left, self.top, self.left, self.bottom, pen=bluePen)
            self.right_line  = scene_ref.addLine(\
                self.right, self.top, self.right, self.bottom, pen=bluePen)


    def redraw_lines_by_anckers(self):
        # redraw lines by connecting anckers
        self.top_line.setLine(\
            self.tl.abs_scenePos_center().x(),\
            self.tl.abs_scenePos_center().y(),\
            self.tr.abs_scenePos_center().x(),\
            self.tr.abs_scenePos_center().y())
        self.bottom_line.setLine(\
            self.bl.abs_scenePos_center().x(),\
            self.bl.abs_scenePos_center().y(),\
            self.br.abs_scenePos_center().x(),\
            self.br.abs_scenePos_center().y())
        self.left_line.setLine(\
            self.tl.abs_scenePos_center().x(),\
            self.tl.abs_scenePos_center().y(),\
            self.bl.abs_scenePos_center().x(),\
            self.bl.abs_scenePos_center().y())
        self.right_line.setLine(\
            self.tr.abs_scenePos_center().x(),\
            self.tr.abs_scenePos_center().y(),\
            self.br.abs_scenePos_center().x(),\
            self.br.abs_scenePos_center().y())


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


