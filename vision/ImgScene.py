import sys
from os import listdir, system, execl
import os.path
import PySide2
import copy
from PySide2.QtWidgets import (QGraphicsScene)
from PySide2.QtGui import (QBrush, QPen, QFont)
from PySide2.QtCore import QLineF, QPointF
from bbox import BBox


class ImgScene(QGraphicsScene):

    def __init__(self, parent):
        super().__init__(parent)
        
        self.mouseDown = False
        self.targetCreated = False
        self.newBboxes = []


    def set_dataScene(self, dscene_ref):
        self.dscene = dscene_ref


    # To correctly capture a click and drag event
    # we need to intercept the floowing three events

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.mouseDown = True


    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        if self.mouseDown and (not self.targetCreated):
            x = event.scenePos().x()
            y = event.scenePos().y()
            newBbox = BBox([x, y, 0, 0],
                        self.dscene.backgroundSize,
                        self.dscene.last_cls)
            newBbox.drew_in_scene(self, self.dscene, -1)
            newBbox.br.mouseMoveEvent(event, \
                passed_by_scene=True)
            self.newBboxes.append(newBbox)
            self.targetCreated = True
        elif self.mouseDown:
            self.newBboxes[-1].br.mouseMoveEvent(event, \
                passed_by_scene=True)


    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if self.mouseDown:
            self.mouseDown = False
            self.targetCreated = False
            self.newBboxes[-1].update()
            self.dscene.record_new_target(self.newBboxes[-1])
