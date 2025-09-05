import cv2
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot

class CaptureThread(QThread):
    frameCaptured = pyqtSignal(np.ndarray)

    def __init__(self, source: str | int = 0):
        super().__init__()
        self.source = source
        self.running = True

    def run(self):
        cap = cv2.VideoCapture(self.source)
        
        if isinstance(self.source, int):
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_FPS, 30)
        
        if not cap.isOpened():
            print(f"Cannot open video source {self.source}")
            return
            
        while self.running and cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                if isinstance(self.source, str):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                else:
                    break
                    
            if frame is not None:
                self.frameCaptured.emit(frame)
            if isinstance(self.source, int):
                self.msleep(33)
            else:
                self.msleep(30)
        cap.release()

    def stop(self):
        self.running = False