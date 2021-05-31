import sys
from os import listdir, system
import os.path
import os
import PySide2
from PySide2 import QtGui
from PySide2 import QtWidgets
from PySide2 import QtXml
from PySide2.QtMultimedia import QMediaContent, QMediaPlayer
from PySide2.QtMultimediaWidgets import QVideoWidget
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import (QApplication, QPushButton, QAction,
                            QFileDialog, QLabel, QGridLayout, QShortcut)
from PySide2.QtCore import QFile, QObject, QRectF, Qt, QUrl
from PySide2.QtGui import (QIcon, QPixmap, QImage, QCursor, QKeySequence)

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
        self.player_widget = QVideoWidget()
        self.player = QMediaPlayer(None, QMediaPlayer.VideoSurface)

        self.window.findChild(QGridLayout, "gridLayout").\
            addWidget(self.player_widget, 0, 0)

        self.player.setVideoOutput(self.player_widget)

        # open video action
        self.window.findChild(QAction, "actionOpen_video").\
            triggered.connect(self.load_video_from_dialog)

        # Play control through keyboard
        # space key for paly/pause
        QShortcut(QKeySequence("Space"), self.window).activated.\
            connect(self.play_pause)


    def show(self):
        self.window.show()


    def load_video_from_dialog(self):
        (file_dir, ext) = QFileDialog.getOpenFileName(\
                filter="Video files (*.mp4)")
        if file_dir != '':
            self.player.setMedia(
                QMediaContent(QUrl.fromLocalFile(file_dir)))
            self.player.play()


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