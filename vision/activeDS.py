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
                            QListView, QGraphicsScene, QGraphicsView, 
                            QProgressDialog)
from PySide2.QtCore import QFile, QObject, QRectF, Qt
from PySide2.QtGui import (QIcon, QPixmap, QImage)

from PIL import Image
from bbox import BBox
from dataScene import DataScene
from ADS_config import label_table, modification_list, IMG_FOLDER, IMG_EXT, LEBEL_FOLDER
import train_val_spliter
import rename


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

        # show change history
        self.window.findChild(QAction, 'actionView_history').\
            triggered.connect(self.show_mods)

        # Tools -----------
        # data spliter
        self.window.findChild(QAction, 'actionData_spliter').\
            triggered.connect(self.run_spliter)
        # renamer
        self.window.findChild(QAction, 'actionRename').\
            triggered.connect(self.run_rename)

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
        # self.current_dataScene = DataScene(self.viewerScene, \
        #     self.viewerView, self.targetList)
        # self.targetList.itemDoubleClicked.connect(\
        #     self.current_dataScene.edit_target_class)

        # editing buttons ===============================================
        self.rmTargetButton = \
            self.window.findChild(QPushButton, 'rmTargetButton')
        self.undoButton = \
            self.window.findChild(QPushButton, 'undoButton')
        self.editButton = \
            self.window.findChild(QPushButton, 'editButton')
        self.deleteButton = \
            self.window.findChild(QPushButton, 'deletButton')


        self.rmTargetButton.setEnabled(False)
        self.undoButton.setEnabled(False)
        self.rmTargetButton.clicked.connect(self.remove_target)
        self.targetList_modified = False
        self.undoButton.clicked.connect(self.undo_mod)

        self.window.show()


    # Load active data set
    def load_adc(self):
        self.adc_folder_dir = QFileDialog.getExistingDirectory()
        if (not os.path.exists(self.adc_folder_dir + IMG_FOLDER)) \
            or (not os.path.exists(self.adc_folder_dir + LEBEL_FOLDER)):
            self.error_msg("Cannot find proper data in " + self.adc_folder_dir \
                + '\n' + "A proper data folder should have subfolders: " \
                + IMG_FOLDER + " and " + LEBEL_FOLDER)
            self.adc_folder_dir = ""
            return
        name_list = []
        for imgName in os.listdir(self.adc_folder_dir + IMG_FOLDER):
            dataName = imgName.split('.')[0] # remove extension
            name_list.append(dataName)
        self.current_data_dir = self.adc_folder_dir
        self.load_dataList(name_list)
        

    def load_dataList(self, nameList ,showThumbnail=True, progressBar=True):
        self.dataList.clear()
        if progressBar:
            progress = QProgressDialog("Loading data...", "Abort", \
                0, len(nameList), self.window)
            progress.setWindowModality(Qt.WindowModal)
        for i, dataName in enumerate(nameList):
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
                                [w, h], class_num)
                        bboxs.append(new_bbox)

                    label_table[dataName] = bboxs
            else:
                self.error_msg("Cannot find label: " + \
                    label_dir)
            
            self.dataList.addItem(newItem)
            if progressBar:
                progress.setValue(i)
                if progress.wasCanceled():
                    break
        if progressBar:
                progress.setValue(len(nameList))


    def load_viewer(self, highlight=-1):
        # self.viewerScene.clear()
        data_name = str(self.dataList.currentItem().text())
        # img_dir = self.current_data_dir + IMG_FOLDER \
        #     + '/' + data_name + '.' + IMG_EXT
        # img = QPixmap(img_dir)
        # w, h = img.size().toTuple()
        # self.viewerScene.addPixmap(img)

        # # reinitialize the target list
        # self.targetList.clear()
        self.rmTargetButton.setEnabled(False)
        # self.targetList_modified = False

        # for i, one_box in enumerate(label_table[data_name]):
        #     if highlight == i:
        #         one_box.drew_in_scene(self.viewerScene, highlight=True)
        #     else:
        #         one_box.drew_in_scene(self.viewerScene)
            
        #     newItem = QtWidgets.QListWidgetItem(str(one_box.cls))
        #     self.targetList.addItem(newItem)
        # self.viewerView.fitInView(QRectF(0, 0, w, h), Qt.KeepAspectRatio)
        # self.viewerScene.update()

        self.current_dataScene = DataScene(self.viewerScene, \
            self.viewerView, self.targetList, data_name, \
            self.current_data_dir)
        # setup edit trigger (double click or edit button)
        self.targetList.itemDoubleClicked.connect(self.current_dataScene.edit_target_class)
        self.editButton.clicked.connect(self.current_dataScene.edit_target_class)
        self.current_dataScene.show(highlight=highlight)


    def reload_viewer(self, highlight=-1):
        # # Same as load_viewer but without loading the target list
        # self.viewerScene.clear()
        # data_name = str(self.dataList.currentItem().text())
        # img_dir = self.current_data_dir + IMG_FOLDER \
        #     + '/' + data_name + '.' + IMG_EXT
        # img = QPixmap(img_dir)
        # w, h = img.size().toTuple()
        # self.viewerScene.addPixmap(img)
        # for i, one_box in enumerate(label_table[data_name]):
        #     if highlight == i:
        #         one_box.drew_in_scene(self.viewerScene, highlight=True)
        #     else:
        #         one_box.drew_in_scene(self.viewerScene)
        # self.viewerView.fitInView(QRectF(0, 0, w, h), Qt.KeepAspectRatio)
        # self.viewerScene.update()
        self.current_dataScene.update_viewer(highlight=highlight)


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


    def show_mods(self):
        self.info_msg(str(modification_list),\
            "Chnage History")


    # Tools ++++++++++++++++++++++++++++++++++++++++++++++++++
    def run_spliter(self):
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setText("The spliter will divide datas "\
             "into training set and validation set")
        msgBox.setStandardButtons(QMessageBox.Ok)
        msgBox.addButton(QMessageBox.Cancel)
        msgBox.setDefaultButton(QMessageBox.Ok)
        ret = msgBox.exec()
        if ret == QMessageBox.Ok:
            train_val_spliter.train_val_split()
        else:
            return


    def run_rename(self):
        data_folder_dir = QFileDialog.getExistingDirectory()
        if (not os.path.exists(data_folder_dir + IMG_FOLDER)) \
            or (not os.path.exists(data_folder_dir + LEBEL_FOLDER)):
            self.error_msg("Cannot find proper data in " + data_folder_dir \
                + '\n' + "A proper data folder should have subfolders: " \
                + IMG_FOLDER + " and " + LEBEL_FOLDER)
            return
        rename.back_ward_rename(data_folder_dir)


    # helpers ++++++++++++++++++++++++++++++++++++++++++++++++
    def error_msg(self, error_msg):
        error_window = QMessageBox()
        error_window.setIcon(QMessageBox.Critical)
        error_window.setText(error_msg)
        error_window.setWindowTitle("Error")
        error_window.setStandardButtons(QMessageBox.Ok)
        error_window.exec_()


    def warn_msg(self, warn_msg):
        error_window = QMessageBox()
        error_window.setIcon(QMessageBox.Warning)
        error_window.setText(warn_msg)
        error_window.setWindowTitle("Warning")
        error_window.setStandardButtons(QMessageBox.Ok)
        error_window.exec_()


    def info_msg(self, info_msg, title='Information'):
        error_window = QMessageBox()
        error_window.setIcon(QMessageBox.Information)
        error_window.setText(info_msg)
        error_window.setWindowTitle(title)
        error_window.setStandardButtons(QMessageBox.Ok)
        error_window.exec_()




    # def load_bbox(self):

        


if __name__ == '__main__':
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_EnableHighDpiScaling)
    form = Form('mainwindow.ui')
    sys.exit(app.exec_())