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
from PySide2.QtGui import (QIcon, QPixmap, QImage, QCursor)


class PlayerScene(QGraphicsScene):

    def __init__(self, parent):
        super().__init__(parent)


    def link_view(self, view):
        self.view_ref = view


    # zoom to fit the video
    def fit_player(self, playerItem):
        playerItem.setSize(QSizeF(3840, 2160)) # hard code to 4k for now, will work for any size of 16:9
        self.view_ref.fitInView(playerItem, Qt.KeepAspectRatio)