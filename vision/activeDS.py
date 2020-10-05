import sys
from os import listdir, system, execl
import os.path
import PySide2

# # this following is hard coded env switch only for pyinstaller
# # The python script will run with or with or without it
# plugin_path = "dep/platforms"
# os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path

from PySide2 import QtGui
from PySide2 import QtWidgets
from PySide2 import QtXml
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import (QApplication, QPushButton, 
                            QLineEdit, QPlainTextEdit, QComboBox, 
                            QCheckBox, QAction, QFileDialog, 
                            QMessageBox, QInputDialog, QListWidget, 
                            QListView)
from PySide2.QtCore import QFile, QObject
from PySide2.QtGui import QIcon, QPixmap, QImage

from PIL import Image


IMG_FOLDER = "/images"
IMG_EXT = 'png'


class Form(QObject):
    
    def __init__(self, ui_file, parent=None):
        super(Form, self).__init__(parent)
        ui_file = QFile(ui_file)
        ui_file.open(QFile.ReadOnly)
        
        loader = QUiLoader()
        self.window = loader.load(ui_file)
        ui_file.close()

        # Menu actions ==================================================
        # Load ADS action
        self.window.findChild(QAction, 'loadAOAction').\
            triggered.connect(self.load_adc)

        # Data list =====================================================
        self.dataList = \
            self.window.findChild(QListWidget, 'dataList')
        self.dataList.setViewMode(QListView.IconMode)
        self.dataList.setIconSize(PySide2.QtCore.QSize(128, 72))

        # Data Viewer ===================================================

        # The foolwing enable custom style sheet
        # self.window.setAttribute(PySide2.QtCore.Qt.WA_StyledBackground)
        # self.window.setStyleSheet(open('app.qss').read())
        self.window.show()


    # Load active data set
    def load_adc(self):
        self.adc_folder_dir = QFileDialog.getExistingDirectory()
        name_list = []
        for imgName in os.listdir(self.adc_folder_dir + IMG_FOLDER):
            dataName = imgName.split('.')[0] # remove extension
            name_list.append(dataName)
        self.load_dataList(name_list)
        

    def load_dataList(self, nameList, showThumbnail=True):
        for dataName in nameList:
            newItem = QtWidgets.QListWidgetItem(dataName)
            
            if showThumbnail:
                # boring img down sizing and img format converting
                img = Image.open(self.adc_folder_dir + IMG_FOLDER \
                    + '/' + dataName + '.' + IMG_EXT)
                w, h = img.size
                img = img.resize((int(w/20), int(h/20)))
                img = img.convert("RGBA")
                qimg = QImage(img.tobytes('raw', 'RGBA'), img.size[0], img.size[1], QImage.Format_RGBA8888)
                thumbnail = QIcon()
                thumbnail.addPixmap(QtGui.QPixmap.fromImage(qimg))
                newItem.setIcon(thumbnail)

            self.dataList.addItem(newItem)


if __name__ == '__main__':
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    app = QApplication(sys.argv)
    app.setAttribute(PySide2.QtCore.Qt.AA_EnableHighDpiScaling)
    form = Form('mainwindow.ui')
    sys.exit(app.exec_())