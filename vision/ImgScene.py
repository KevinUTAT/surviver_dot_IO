import sys
from os import listdir, system, execl
import os.path
import PySide2
import copy
from PySide2.QtWidgets import (QGraphicsScene)
from PySide2.QtGui import (QBrush, QPen, QFont)
from PySide2.QtCore import QLineF, QPointF


class ImgScene(QGraphicsScene):

    def __init__(self, parent):
        super().__init__(parent)
        
        self.mouseDown = False


    # To correctly capture a click and drag event
    # we need to intercept the floowing three events

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.mouseDown = True


    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        if self.mouseDown:
            print(event.scenePos())


    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.mouseDown = False
