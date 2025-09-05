import sys
import os
from PyQt5.QtWidgets import (QApplication, QLabel, QWidget, QVBoxLayout, 
                            QHBoxLayout, QGridLayout, QPushButton, QRadioButton,
                            QButtonGroup, QFileDialog, QGroupBox,
                            QMessageBox)
from PyQt5.QtCore import pyqtSlot, QTimer
from PyQt5.QtGui import QFont
import cv2
import numpy as np
from core.video_capture import CaptureThread
from core.process import ProcessThread
from core.display import DisplayThread

class MainWindow(QWidget):
    def __init__(self, video_source: str | int = 0, model_path: str = 'yolov8n.pt'):
        super().__init__()
        self.setWindowTitle('Demo')

        self.detected_faces = []
        self.fps_counter = 0
        self.fps_timer = QTimer()
        self.fps_timer.timeout.connect(self.update_fps)
        self.fps_timer.start(500)  # Update per mini-second
        self.fps = 0
        
        self.current_video_source = video_source
        self.model_path = model_path
        
        self.init_ui()
        self.init_threads()

    def init_ui(self):
        main_layout = QHBoxLayout()
        left_panel = QVBoxLayout()
        
        """
        Left panel
        """
        control_group = QGroupBox("Video Source Control")
        control_layout = QVBoxLayout()
        self.source_group = QButtonGroup()
        self.camera_radio = QRadioButton("Camera")
        self.video_radio = QRadioButton("Video File")
        self.camera_radio.setChecked(True)
        
        self.source_group.addButton(self.camera_radio, 0)
        self.source_group.addButton(self.video_radio, 1)
        
        self.select_video_btn = QPushButton("Select Video File")
        self.start_btn = QPushButton("Start")
        self.stop_btn = QPushButton("Stop")
        
        source_layout = QHBoxLayout()
        source_layout.addWidget(self.camera_radio)
        source_layout.addWidget(self.video_radio)
        source_layout.addWidget(self.select_video_btn)
        
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)
        
        control_layout.addLayout(source_layout)
        control_layout.addLayout(button_layout)
        control_group.setLayout(control_layout)
        
        self.fps_label = QLabel("FPS: 0")
        self.fps_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.fps_label.setStyleSheet("color: green;")
        
        self.main_video_label = QLabel()
        self.main_video_label.setMinimumSize(640, 480)
        self.main_video_label.setStyleSheet("border: 2px solid black; background-color: gray;")
        
        left_panel.addWidget(control_group)
        left_panel.addWidget(self.fps_label)
        left_panel.addWidget(self.main_video_label)
        
        """
        Right panel
        """
        right_panel = QVBoxLayout()

        self.faces_grid = QGridLayout()
        self.face_labels = []
        
        for i in range(5):
            face_label = QLabel(f"Face {i+1}")
            face_label.setMinimumSize(150, 150)
            face_label.setStyleSheet("border: 1px solid gray;")
            face_label.setText(f"Face {i+1}\nNot detected")
            self.face_labels.append(face_label)
            
            row = i // 1  # 5 hàng, 1 cột
            col = i % 1
            self.faces_grid.addWidget(face_label, row, col)
        
        faces_widget = QWidget()
        faces_widget.setLayout(self.faces_grid)

        right_panel.addWidget(faces_widget)
        right_panel.addStretch()
        
        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        
        right_widget = QWidget()
        right_widget.setLayout(right_panel)
        
        main_layout.addWidget(left_widget, 2)  # 2/3
        main_layout.addWidget(right_widget, 1)  # 1/3
        
        self.setLayout(main_layout)

        self.select_video_btn.clicked.connect(self.select_video_file)
        self.start_btn.clicked.connect(self.start_capture)
        self.stop_btn.clicked.connect(self.stop_capture)

    def init_threads(self):
        self.captureThread = None
        self.processThread = None
        self.displayThread = None

    def select_video_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Video File", "", 
            "Video Files (*.mp4 *.avi *.mov *.mkv *.wmv);;All Files (*)"
        )
        if file_path:
            self.current_video_source = file_path
            self.video_radio.setChecked(True)

    def start_capture(self):
        if self.captureThread and self.captureThread.isRunning():
            return
            
        if self.camera_radio.isChecked():
            self.current_video_source = 0
        elif not hasattr(self, 'current_video_source') or isinstance(self.current_video_source, int):
            return
            
        self.captureThread = CaptureThread(self.current_video_source)
        self.processThread = ProcessThread(self.model_path)
        self.displayThread = DisplayThread()

        self.captureThread.frameCaptured.connect(self.onFrameCaptured)
        self.processThread.frameProcessed.connect(self.onFrameProcessed)
        self.processThread.facesDetected.connect(self.onFacesDetected)
        self.displayThread.updateDisplay.connect(self.onUpdateDisplay)

        self.captureThread.start()
        self.processThread.start()
        self.displayThread.start()

    def stop_capture(self):
        if self.captureThread:
            self.captureThread.stop()
        if self.processThread:
            self.processThread.stop()
        if self.displayThread:
            self.displayThread.stop()

    @pyqtSlot(np.ndarray)
    def onFrameCaptured(self, frame):
        if self.processThread:
            self.processThread.setFrame(frame)
        self.fps_counter += 1

    @pyqtSlot(np.ndarray)
    def onFrameProcessed(self, frame):
        if self.displayThread:
            self.displayThread.setFrame(frame)

    @pyqtSlot(list)
    def onFacesDetected(self, faces):
        self.detected_faces = faces[:5]  # top 5
        self.update_faces_display()

    @pyqtSlot(np.ndarray)
    def onUpdateDisplay(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w

        from PyQt5.QtGui import QImage, QPixmap
        qt_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        pixmap = QPixmap.fromImage(qt_img)
        scaled_pixmap = pixmap.scaled(self.main_video_label.size(), 1, 1)
        self.main_video_label.setPixmap(scaled_pixmap)

    def update_fps(self):
        self.fps = self.fps_counter
        self.fps_counter = 0
        self.fps_label.setText(f"FPS: {self.fps}")

    def update_faces_display(self):
        for i in range(5):
            if i < len(self.detected_faces):
                face_img = self.detected_faces[i]
                
                rgb_face = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_face.shape
                bytes_per_line = ch * w
                
                from PyQt5.QtGui import QImage, QPixmap
                qt_img = QImage(rgb_face.data, w, h, bytes_per_line, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qt_img)
                scaled_pixmap = pixmap.scaled(self.face_labels[i].size(), 1, 1)
                
                self.face_labels[i].setPixmap(scaled_pixmap)
                self.face_labels[i].setText("")
            else:
                self.face_labels[i].clear()

    def closeEvent(self, event):
        self.fps_timer.stop()
        
        if self.captureThread:
            self.captureThread.stop()
            self.captureThread.quit()
            self.captureThread.wait()
            
        if self.processThread:
            self.processThread.stop()
            self.processThread.quit()
            self.processThread.wait()
            
        if self.displayThread:
            self.displayThread.stop()
            self.displayThread.quit()
            self.displayThread.wait()
            
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow(video_source=0, model_path='runs/detect/train3/weights/best.pt')
    window.show()
    sys.exit(app.exec_())
