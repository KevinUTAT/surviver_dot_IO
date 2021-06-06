import sys
from os import listdir, system
import os.path
import os
import PySide2
from PySide2 import QtGui
from PySide2 import QtWidgets
from PySide2 import QtXml
from PySide2.QtMultimedia import QMediaContent, QMediaPlayer
from PySide2.QtMultimediaWidgets import QGraphicsVideoItem
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import (QApplication, QPushButton, QAction,
                            QFileDialog, QLabel, QGridLayout, QShortcut,
                            QGraphicsView)
from PySide2.QtCore import QFile, QObject, QRectF, Qt, QUrl, QPointF
from PySide2.QtGui import (QIcon, QPixmap, QImage, QCursor, QKeySequence)

from player_scene import PlayerScene


# Main window for the visual tester 
class VTester(QObject):

    def __init__(self, ui_file, parent=None):
        super(VTester, self).__init__(parent)
        ui_file = QFile(ui_file)
        ui_file.open(QFile.ReadOnly)
        
        loader = QUiLoader()
        self.window = loader.load(ui_file)
        ui_file.close()

        # setup the video player
        # a graphic scene as base
        self.playerScene = PlayerScene(self)
        self.playerView = self.window.findChild(QGraphicsView, 'playerView')
        self.playerView.setScene(self.playerScene)
        self.playerView.setCursor(QCursor(PySide2.QtCore.Qt.CrossCursor))
        self.playerScene.link_view(self.playerView)
        self.playerView.setMouseTracking(True)
        # frontend of video player
        self.playerItem = QGraphicsVideoItem()
        self.playerScene.addItem(self.playerItem)
        self.playerItem.setAspectRatioMode(Qt.KeepAspectRatio)
        # backend of a video player
        self.player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.player.setVideoOutput(self.playerItem)

        # open video action
        self.window.findChild(QAction, "actionOpen_video").\
            triggered.connect(self.load_video_from_dialog)

        # Play control through keyboard
        # space key for paly/pause
        QShortcut(QKeySequence("Space"), self.window).activated.\
            connect(self.play_pause)


    def show(self):
        self.window.show()
        self.playerView.show()


    def load_video_from_dialog(self):
        (file_dir, ext) = QFileDialog.getOpenFileName(\
                filter="Video files (*.mp4)")
        if file_dir != '':
            self.player.setMedia(
                QMediaContent(QUrl.fromLocalFile(file_dir)))
            self.player.play()
            self.playerScene.fit_player(self.playerItem)


    # toggleing between paly and pause
    def play_pause(self):
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()





if __name__ == '__main__':
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_EnableHighDpiScaling)
    tester_window = VTester('visualtester.ui')
    tester_window.show()
    sys.exit(app.exec_())