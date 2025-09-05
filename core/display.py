from PyQt5.QtCore import QThread, pyqtSignal
import queue
import numpy as np
import time

class DisplayThread(QThread):
    updateDisplay = pyqtSignal(np.ndarray)

    def __init__(self):
        super().__init__()
        self.running = True
        self.frame_queue = queue.Queue(maxsize=10)

    def setFrame(self, frame):
        try:
            while not self.frame_queue.empty():
                try:
                    self.frame_queue.get_nowait()
                except queue.Empty:
                    break
        except:
            pass
        
        try:
            self.frame_queue.put_nowait(frame)
        except queue.Full:
            pass

    def run(self):
        while self.running:
            try:
                if not self.frame_queue.empty():
                    frame = self.frame_queue.get_nowait()
                    self.updateDisplay.emit(frame)
                else:
                    self.msleep(1)
            except queue.Empty:
                self.msleep(1)

    def stop(self):
        self.running = False