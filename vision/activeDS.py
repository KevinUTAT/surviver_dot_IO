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
                            QListView, QGraphicsScene, QGraphicsView)
from PySide2.QtCore import QFile, QObject, QRectF, Qt
from PySide2.QtGui import (QIcon, QPixmap, QImage)

from PIL import Image
from bbox import BBox


IMG_FOLDER = "/images"
IMG_EXT = 'png'
LEBEL_FOLDER = "/labels"

label_table = {}

# A modification is a array of [data_name, target_idx, new_data, old_data]
# to delete a target, set new_data to ''
# Old data is used to undo changes
modification_list = []


class Form(QObject):
    
    def __init__(self, ui_file, parent=None):
        super(Form, self).__init__(parent)
        ui_file = QFile(ui_file)
        ui_file.open(QFile.ReadOnly)
        
        loader = QUiLoader()
        self.window = loader.load(ui_file)
        ui_file.close()

        # system flags
        self.current_data_dir = "."

        # Menu actions ==================================================
        # Load ADS action
        self.window.findChild(QAction, 'loadAOAction').\
            triggered.connect(self.load_adc)

        # load save target mod action
        self.window.findChild(QAction, 'actionTarget_Modifications').\
            triggered.connect(self.save_mods)

        # Data list =====================================================
        self.dataList = \
            self.window.findChild(QListWidget, 'dataList')
        self.dataList.setViewMode(QListView.IconMode)
        self.dataList.setIconSize(PySide2.QtCore.QSize(128, 72))
        self.dataList.itemSelectionChanged.connect(self.load_viewer)

        # Data Viewer ===================================================
        self.viewerScene = QGraphicsScene(self)
        self.viewerView = self.window.findChild(QGraphicsView, 'dataViewer')
        self.viewerView.setScene(self.viewerScene)

        # Targets list ==================================================
        self.targetList = \
            self.window.findChild(QListWidget, 'targetList')
        self.targetList.itemSelectionChanged.connect(self.hightlight_target)
        self.rmTargetButton = \
            self.window.findChild(QPushButton, 'rmTargetButton')
        self.undoButton = \
            self.window.findChild(QPushButton, 'undoButton')
        self.rmTargetButton.setEnabled(False)
        self.undoButton.setEnabled(False)
        self.rmTargetButton.clicked.connect(self.remove_target)
        self.targetList_modified = False
        self.undoButton.clicked.connect(self.undo_mod)

        self.window.show()


    # Load active data set
    def load_adc(self):
        self.adc_folder_dir = QFileDialog.getExistingDirectory()
        name_list = []
        for imgName in os.listdir(self.adc_folder_dir + IMG_FOLDER):
            dataName = imgName.split('.')[0] # remove extension
            name_list.append(dataName)
        self.current_data_dir = self.adc_folder_dir
        self.load_dataList(name_list)
        

    def load_dataList(self, nameList ,showThumbnail=True):
        self.dataList.clear()
        for dataName in nameList:
            newItem = QtWidgets.QListWidgetItem(dataName)
            
            if showThumbnail:
                # boring img down sizing and img format converting
                img = Image.open(self.current_data_dir + IMG_FOLDER \
                    + '/' + dataName + '.' + IMG_EXT)
                w, h = img.size
                img = img.resize((int(w/20), int(h/20)))
                img = img.convert("RGBA")
                qimg = QImage(img.tobytes('raw', 'RGBA'), img.size[0], \
                    img.size[1], QImage.Format_RGBA8888)
                thumbnail = QIcon()
                thumbnail.addPixmap(QtGui.QPixmap.fromImage(qimg))
                newItem.setIcon(thumbnail)

                # pre load all the labels
                label_dir = self.current_data_dir + LEBEL_FOLDER \
                    + '/' + dataName + '.txt'
                if os.path.exists(label_dir):
                    with open(label_dir, 'r') as label_file:
                        bboxs = []
                        for line in label_file:
                            bbox_l = line.split()
                            class_num = int(bbox_l[0])
                            centerX = int(float(bbox_l[1]) * w)
                            centerY = int(float(bbox_l[2]) * h)
                            width = int(float(bbox_l[3]) * w)
                            height = int(float(bbox_l[4]) * h)
                            new_bbox = BBox([centerX, centerY, width, height],\
                                 class_num)
                            bboxs.append(new_bbox)

                        label_table[dataName] = bboxs
                else:
                    print("Cannot find label: " + \
                        label_dir)
            
            self.dataList.addItem(newItem)


    def load_viewer(self, highlight=-1):
        self.viewerScene.clear()
        data_name = str(self.dataList.currentItem().text())
        img_dir = self.current_data_dir + IMG_FOLDER \
            + '/' + data_name + '.' + IMG_EXT
        img = QPixmap(img_dir)
        w, h = img.size().toTuple()
        self.viewerScene.addPixmap(img)

        # reinitialize the target list
        self.targetList.clear()
        self.rmTargetButton.setEnabled(False)
        self.targetList_modified = False

        for i, one_box in enumerate(label_table[data_name]):
            if highlight == i:
                one_box.drew_in_scene(self.viewerScene, highlight=True)
            else:
                one_box.drew_in_scene(self.viewerScene)
            
            newItem = QtWidgets.QListWidgetItem(str(one_box.cls))
            self.targetList.addItem(newItem)
        self.viewerView.fitInView(QRectF(0, 0, w, h), Qt.KeepAspectRatio)
        self.viewerScene.update()


    def reload_viewer(self, highlight=-1):
        # Same as load_viewer but without loading the target list
        self.viewerScene.clear()
        data_name = str(self.dataList.currentItem().text())
        img_dir = self.current_data_dir + IMG_FOLDER \
            + '/' + data_name + '.' + IMG_EXT
        img = QPixmap(img_dir)
        w, h = img.size().toTuple()
        self.viewerScene.addPixmap(img)
        for i, one_box in enumerate(label_table[data_name]):
            if highlight == i:
                one_box.drew_in_scene(self.viewerScene, highlight=True)
            else:
                one_box.drew_in_scene(self.viewerScene)
        self.viewerView.fitInView(QRectF(0, 0, w, h), Qt.KeepAspectRatio)
        self.viewerScene.update()


    def hightlight_target(self):
        target_idx = self.targetList.currentRow()
        # print(target_idx)
        self.reload_viewer(target_idx)

        self.rmTargetButton.setEnabled(True)


    def remove_target(self):
        target2rm_idx = self.targetList.currentRow()
        data_name = str(self.dataList.currentItem().text())
        # delete one bbox from label_table[data_name]
        new_bboxs = []
        for i, one_box in enumerate(label_table[data_name]):
            if i != target2rm_idx:
                new_bboxs.append(one_box)
            else:
                del_box = one_box
        label_table[data_name] = new_bboxs

        # record modification
        mod = [data_name, target2rm_idx, '', del_box]
        modification_list.append(mod)

        self.undoButton.setEnabled(True)
        self.load_viewer()


    def undo_mod(self):
        last_mod = modification_list[-1]
        data_name = last_mod[0]
        tar_idx = last_mod[1]
        # insert old bbox back if deleted
        # else just restore old bbox
        if last_mod[2] == '':
            label_table[data_name].insert(tar_idx, last_mod[3])
        else:
            label_table[data_name][tar_idx] = last_mod[3]

        # then remove this modification form mod list
        del modification_list[-1]

        if len(modification_list) == 0:
            self.undoButton.setEnabled(False)
        self.load_viewer()
        


    def save_mods(self):
        for mod in modification_list:
            label_dir = self.current_data_dir + LEBEL_FOLDER \
                    + '/' + mod[0] + '.txt'
            with open(label_dir, 'r') as label_file:
                lines = label_file.readlines()
            if mod[2] == '':
                del lines[mod[1]]
            else:
                lines[mod[1]] = mod[2]

            with open(label_dir, 'w') as label_file:
                label_file.writelines(lines)
        modification_list.clear()






    # def load_bbox(self):

        


if __name__ == '__main__':
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_EnableHighDpiScaling)
    form = Form('mainwindow.ui')
    sys.exit(app.exec_())