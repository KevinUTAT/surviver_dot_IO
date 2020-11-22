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
from PySide2.QtGui import (QIcon, QPixmap, QImage, QCursor)

from PIL import Image
import shutil
from bbox import BBox
from dataScene import DataScene
from ADS_config import label_table, modification_list, IMG_FOLDER, IMG_EXT, LEBEL_FOLDER
import train_val_spliter
import rename
import detect


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
        
        # Load from video
        self.window.findChild(QAction, 'actionFrom_Video').\
            triggered.connect(self.get_active_from_video)

        # load save target mod action
        self.window.findChild(QAction, 'actionTarget_Modifications').\
            triggered.connect(self.save_mods)

        # show change history
        self.window.findChild(QAction, 'actionView_history').\
            triggered.connect(self.show_mods)
        
        # save active data to ..
        self.window.findChild(QAction, 'actionActive_data_to').\
            triggered.connect(self.save_active_to)

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
        self.viewerView.setCursor(QCursor(PySide2.QtCore.Qt.CrossCursor))

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
            self.window.findChild(QPushButton, 'deleteButton')


        self.rmTargetButton.setEnabled(False)
        self.undoButton.setEnabled(False)
        self.rmTargetButton.clicked.connect(self.remove_target)
        self.targetList_modified = False
        self.undoButton.clicked.connect(self.undo_mod)
        self.deleteButton.clicked.connect(self.remove_img)

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
        label_table.clear()
        modification_list.clear()
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


    def remove_img(self, dataname=None):
        # remove a imgage-label pair and mark it for deletion
        old_item_n_label = []
        if not dataname:
            dataname = self.current_dataScene.data_name
            data_idx = self.dataList.currentRow()
            data_item = self.dataList.item(data_idx)
        else:
            data_idx, data_item = self.find_data_by_name(dataname)
        # remove data item form datalist
        self.info_msg("The image and label of: \n"\
            + dataname + "\nwill be mark for deletion\n"\
            + "Deletion will not happen until action: \n"\
            + "Save -> Target modifications")

        if self.dataList.isItemSelected(data_item):
             # foucus on a different data 
            if data_idx < (self.dataList.count()-1):
                self.dataList.setCurrentRow(data_idx + 1)
            else:
                self.dataList.setCurrentRow(data_idx - 1)

        old_item_n_label.append((data_idx, data_item))
        self.dataList.takeItem(data_idx)

        # remove from labeltable
        old_item_n_label.append(label_table[dataname])
        del label_table[dataname]

        # mark for deletion
        mod = [dataname, -1, '', old_item_n_label]
        modification_list.append(mod)
        self.undoButton.setEnabled(True)


    def undo_mod(self):
        last_mod = modification_list[-1]
        data_name = last_mod[0]
        tar_idx = last_mod[1]
        # to undo a data deletion:
        # 1. resore itme in datalist
        # 2. resore label_table
        if tar_idx == -1:
            old_idx = last_mod[3][0][0]
            old_item = last_mod[3][0][1]
            old_label = last_mod[3][1]
            self.dataList.insertItem(old_idx, old_item)
            label_table[data_name] = old_label
        else:
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
            img_dir = self.current_data_dir + IMG_FOLDER \
                    + '/' + mod[0] + '.' + IMG_EXT
            if mod[1] == -1:
                os.remove(img_dir)
                os.remove(label_dir)
            else:
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


    def save_active_to(self):
        dest = QFileDialog.getExistingDirectory()
        if (not os.path.exists(dest + IMG_FOLDER)) \
            or (not os.path.exists(dest + LEBEL_FOLDER)):
            self.error_msg("Cannot find proper data in " + dest \
                + '\n' + "A proper data folder should have subfolders: " \
                + IMG_FOLDER + " and " + LEBEL_FOLDER)
            return
        dest_img_folder = dest + IMG_FOLDER
        dest_label_folder = dest + LEBEL_FOLDER
        for img in os.listdir(self.current_data_dir + IMG_FOLDER):

            source_img = self.current_data_dir + IMG_FOLDER \
                + '/' + img
            dest_img = dest_img_folder + '/' + img

            source_label = self.current_data_dir + LEBEL_FOLDER \
                + '/' + img.split('.')[0] + ".txt"
            dest_label = dest_label_folder + \
                '/' +img.split('.')[0] + ".txt"

            # do some check first:
            # 1. data with the same name not already there
            # 2. label exist for img
            if os.path.exists(dest_img):
                self.error_msg("Image " + dest_img + \
                    " already exist, it will not be moved")
                continue
            if os.path.exists(dest_label):
                self.error_msg("Label " + dest_label + \
                    " already exist, it will not be moved")
                continue
            if not os.path.exists(source_label):
                self.error_msg("The label " + source_label \
                    + " do not exist, data will not be moved")
                continue
            shutil.move(source_img, dest_img)
            shutil.move(source_label, dest_label)


    def get_active_from_video(self):
        (source_vid, ext) = QFileDialog.getOpenFileName(\
                filter="Video files (*.mp4 *.avi)")
        # show a dialog
        dialog = QInputDialog()
        label_text = "Input active threshold"
        text, okPressed = \
            QInputDialog.getText(dialog, \
            "Active Threshold", \
            label_text, \
            QLineEdit.Normal)
        if okPressed and text != '':
            active_thr = float(text)
        else:
            active_thr = 0.0
        progress = 0
        progress_bar = QProgressDialog("Detecting Video...", "Abort", \
                0, 100, self.window)
        progress_bar.setWindowModality(Qt.WindowModal)
        progress_bar.setValue(progress)
        detect.run_detect_video(source_vid, progress_bar, active_thr)

            


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
    def find_data_by_name(self, dataname):
        # return the row number and Qlistitem
        for item_idx in range(self.dataList.count()):
            cur_item = self.dataList.item(item_idx)
            if cur_item.text() == dataname:
                return item_idx, cur_item
        return None


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