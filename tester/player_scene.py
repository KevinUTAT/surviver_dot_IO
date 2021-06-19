import sys
from os import listdir, system
import os.path
import os
import PySide2
from PySide2 import QtGui
from PySide2 import QtWidgets
from PySide2 import QtXml
from PySide2.QtMultimedia import QMediaContent, QMediaPlayer
from PySide2.QtWidgets import (QGraphicsScene)
from PySide2.QtCore import QObject, QRectF, Qt, QSizeF
from PySide2.QtGui import (QIcon, QPixmap, QImage, QCursor, QPen)


class PlayerScene(QGraphicsScene):

    def __init__(self, parent):
        super().__init__(parent)
        self.max_width = 3840
        self.max_height = 2160
        self.red_pen = QPen(Qt.red)
        

    def link_view(self, view):
        self.view_ref = view


    # zoom to fit the video
    def fit_player(self, playerItem):
        playerItem.setSize(QSizeF(3840, 2160)) # hard code to 4k for now, will work for any size of 16:9
        self.view_ref.fitInView(playerItem, Qt.KeepAspectRatio)


    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        self.draw_cross(event.scenePos().x(), event.scenePos().y())


    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.draw_cross(event.scenePos().x(), event.scenePos().y(), colour="red")


    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.draw_cross(event.scenePos().x(), event.scenePos().y(), colour="black")


    def draw_cross(self, x, y, colour="black"):
        if (x > self.max_width) or (x < 0) \
            or (y > self.max_height) or (y < 0):
            return
        # draw a cross center at the cursor
        # or move the cross if it's already drawn
        if not hasattr(self, 'cross_pen'):
            self.cross_pen = QPen()
            self.cross_h = self.addLine(0, y, self.max_width, y, self.cross_pen)
            self.cross_v = self.addLine(x, 0, x, self.max_height, self.cross_pen)
        else:
            
            self.cross_h.setLine(0, y, self.max_width, y)
            self.cross_v.setLine(x, 0, x, self.max_height)

            if colour == "black": 
                self.cross_h.setPen(self.cross_pen)
                self.cross_v.setPen(self.cross_pen)
            elif colour == "red":
                self.cross_h.setPen(self.red_pen)
                self.cross_v.setPen(self.red_pen)