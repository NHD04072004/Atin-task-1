import sys
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot
import cv2
import queue
import numpy as np
from ultralytics import YOLO


class CaptureThread(QThread):
    frameCaptured = pyqtSignal(np.ndarray)

    def __init__(self, source: str | int = 0):
        super().__init__()
        self.source = source
        self.running = True

    def run(self):
        cap = cv2.VideoCapture(self.source)
        while self.running and cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            self.frameCaptured.emit(frame)
        cap.release()
        cv2.destroyAllWindows()

    def stop(self):
        self.running = False


class ProcessThread(QThread):
    frameProcessed = pyqtSignal(np.ndarray)

    def __init__(self, model_path: str = 'yolov8n.pt'):
        super().__init__()
        self.model = YOLO(model_path)
        self.running = True
        self.frame = None

    def setFrame(self, frame):
        self.frame = frame

    def run(self):
        while self.running:
            if self.frame is not None:
                results = self.model(self.frame)
                boxes = results[0].boxes.xyxy.cpu().numpy() if results else []
                for box in boxes:
                    x1, y1, x2, y2 = map(int, box[:4])
                    cv2.rectangle(self.frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                self.frameProcessed.emit(self.frame.copy())
                self.frame = None

    def stop(self):
        self.running = False


class DisplayThread(QThread):
    updateDisplay = pyqtSignal(np.ndarray)

    def __init__(self):
        super().__init__()
        self.running = True
        self.frame_queue = queue.Queue(maxsize=10)

    def setFrame(self, frame):
        try:
            self.frame_queue.get_nowait()
        except queue.Empty:
            pass
        self.frame_queue.put(frame)

    def run(self):
        while self.running:
            if self.frame_queue.empty():
                frame = self.frame_queue.get()
                self.updateDisplay.emit(frame)
            self.msleep(6)  # Approx 60 FPS

    def stop(self):
        self.running = False


class MainWindow(QWidget):
    def __init__(self, video_source: str | int = 0, model_path: str = 'yolov8n.pt'):
        super().__init__()
        self.setWindowTitle('Demo')
        self.label = QLabel()
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

        self.captureThread = CaptureThread(video_source)
        self.processThread = ProcessThread(model_path)
        self.displayThread = DisplayThread()

        self.captureThread.frameCaptured.connect(self.onFrameCaptured)
        self.processThread.frameProcessed.connect(self.onFrameProcessed)
        self.displayThread.updateDisplay.connect(self.onUpdateDisplay)

        self.captureThread.start()
        self.processThread.start()
        self.displayThread.start()

    @pyqtSlot(np.ndarray)
    def onFrameCaptured(self, frame):
        self.processThread.setFrame(frame)

    @pyqtSlot(np.ndarray)
    def onFrameProcessed(self, frame):
        self.displayThread.setFrame(frame)

    @pyqtSlot(np.ndarray)
    def onUpdateDisplay(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w

        from PyQt5.QtGui import QImage, QPixmap
        qt_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.label.setPixmap(QPixmap.fromImage(qt_img))

    def closeEvent(self, event):
        self.captureThread.stop()
        self.processThread.stop()
        self.displayThread.stop()

        self.captureThread.quit()
        self.processThread.quit()
        self.displayThread.quit()

        self.captureThread.wait()
        self.processThread.wait()
        self.displayThread.wait()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow(video_source=0, model_path='yolov8n-face.pt')
    window.show()
    sys.exit(app.exec_())
