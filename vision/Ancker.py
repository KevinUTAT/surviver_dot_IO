import sys
from os import listdir, system, execl
import os.path
import PySide2
import copy
from PySide2.QtWidgets import (QGraphicsScene, 
                        QGraphicsRectItem)
from PySide2.QtGui import (QBrush, QPen, QFont)
from PySide2.QtCore import QLineF, QPointF


class Ancker(QGraphicsRectItem):
# Ancker for a BBox corner
    def __init__(self, x, y, w, h, brush, atype, bbox_ref, parent=None):
        super().__init__(x, y, w, h, parent=parent)
        super().setBrush(brush)

        # atype: tl, tr, bl, br
        self.atype = atype
        self.bbox = bbox_ref
        self.origin = QPointF(x, y)
        self.xywh = [x, y, w, h] # x, y is TL corner


    def mouseMoveEvent(self, event, passed_by_scene=False):
        super().mouseMoveEvent(event)

        # disable drew new bbox
        if passed_by_scene:
            self.bbox.currentScene.targetCreated = True
        else:
            self.bbox.currentScene.mouseDown = False
        new_pos = self.scenePos()
        # move other anckers acrodingly
        if self.atype == 'tl':
            self.bbox.tr.setY(new_pos.y())
            self.bbox.bl.setX(new_pos.x())
        elif self.atype == 'tr':
            self.bbox.tl.setY(new_pos.y())
            self.bbox.br.setX(new_pos.x())
        elif self.atype == 'bl':
            self.bbox.tl.setX(new_pos.x())
            self.bbox.br.setY(new_pos.y())
        elif self.atype == 'br':
            self.bbox.tr.setX(new_pos.x())
            self.bbox.bl.setY(new_pos.y())
        else:
            print("Ancker Error: Unknow type " + self.atype)
        # move lines
        self.bbox.redraw_lines_by_anckers()


    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        
        # upon release, record the change
        self.bbox.update()
        # self.bbox.reorder()
        # print(self.bbox.to_label_str())
        self.bbox.dScene.record_target_pos(self.bbox.target_idx)


    def abs_scenePos(self):
        # TL corner
        return self.origin + self.pos()


    def abs_scenePos_center(self):
        TL = self.abs_scenePos()
        TL.setX(TL.x() + self.xywh[2]/2)
        TL.setY(TL.y() + self.xywh[3]/2)
        return TL


    def centerX(self):
        return self.abs_scenePos_center().x()


    def centerY(self):
        return self.abs_scenePos_center().y()