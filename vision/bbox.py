import sys
from os import listdir, system, execl
import os.path
import copy
import PySide2
from PySide2.QtWidgets import QGraphicsScene
from PySide2.QtGui import QBrush, QPen, QFont, QCursor
from PySide2.QtCore import QLineF, QPointF
from Ancker import Ancker
from ADS_config import (label_table, modification_list, 
                    IMG_FOLDER, IMG_EXT, LEBEL_FOLDER)


class BBox(object):
    def __init__(self, xywh, imgSizeWH, class_num):
        self.parent = None
        self.currentScene = None
        # make sure xywh = [centerX, centerY, width, height]
        self.xywh = xywh
        self.imgSizeWH = imgSizeWH

        self.top = int(xywh[1] - xywh[3]/2)
        self.bottom = int(xywh[1] + xywh[3]/2) 
        self.left = int(xywh[0] - xywh[2]/2)
        self.right = int(xywh[0] + xywh[2]/2)

        self.cls = class_num


    def drew_in_scene(self, scene_ref, dScene_ref, target_idx, highlight=False):
        # pass in a reference to the sence
        # then this function will drew on the scene
        self.currentScene = scene_ref
        self.dScene = dScene_ref
        self.target_idx = target_idx
        blueBrush = QBrush(PySide2.QtCore.Qt.blue)
        bluePen = QPen(PySide2.QtCore.Qt.blue)
        highlightPen = QPen(PySide2.QtCore.Qt.red)
        highlightPen.setWidth(3)

        # 4 ancker points at 4 corners
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


    def update(self):
        # update bbox to anckers (after moving)

        self.restore_pt = \
            BBox(self.xywh, self.imgSizeWH, self.cls)

        self.xywh[0] = \
            (self.tl.centerX() + self.tr.centerX()) / 2
        self.xywh[1] = \
            (self.tl.centerY() + self.bl.centerY()) / 2
        self.xywh[2] = \
            abs(self.tr.centerX() - self.tl.centerX())
        self.xywh[3] = \
            abs(self.bl.centerY() - self.tl.centerY())

        self.top = int(self.xywh[1] - self.xywh[3]/2)
        self.bottom = int(self.xywh[1] + self.xywh[3]/2) 
        self.left = int(self.xywh[0] - self.xywh[2]/2)
        self.right = int(self.xywh[0] + self.xywh[2]/2)


    def reorder(self):
        # after moving anckers, its positional order might
        # be wrong (ex: self.tl is moved to bottom right 
        # relitive to other anckers, and w, h will turn negitive)
        temp_tl = self.tl
        temp_tr = self.tr
        temp_bl = self.bl
        temp_br = self.br

        if self.xywh[2] < 0:
            # if width is negitive, swap left and right
            self.tl = temp_tr
            self.tr = temp_tl
            self.bl = temp_br 
            self.br = temp_bl

        temp_tl = self.tl
        temp_tr = self.tr
        temp_bl = self.bl
        temp_br = self.br

        if self.xywh[3] < 0:
            # if height is negitive, swap top and bottom
            self.tl = temp_bl
            self.bl = temp_tl
            self.tr = temp_br
            self.br = temp_tr
        
        self.update()


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


    def __str__(self):
        str_out = "BBox: "
        str_out += "cls=" + str(self.cls)
        str_out += " At:" + str(self.xywh)
        return str_out


    def __repr__(self):
        return self.__str__()


