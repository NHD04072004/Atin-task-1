from ultralytics import YOLO
import cv2
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal

class ProcessThread(QThread):
    frameProcessed = pyqtSignal(np.ndarray)
    facesDetected = pyqtSignal(list)

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
                detected_faces = []
                
                if results and len(results[0].boxes) > 0:
                    boxes = results[0].boxes.xyxy.cpu().numpy()
                    confidences = results[0].boxes.conf.cpu().numpy()
                    sorted_indices = np.argsort(confidences)[::-1]
                    
                    for idx in sorted_indices[:5]:  # Max 5 faces
                        box = boxes[idx]
                        conf = confidences[idx]
                        
                        x1, y1, x2, y2 = map(int, box[:4])
                        
                        cv2.rectangle(self.frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.putText(self.frame, f'{conf:.2f}', (x1, y1-10), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                        
                        if x1 >= 0 and y1 >= 0 and x2 < self.frame.shape[1] and y2 < self.frame.shape[0]:
                            face_img = self.frame[y1:y2, x1:x2]
                            if face_img.size > 0:
                                face_resized = cv2.resize(face_img, (150, 150))
                                detected_faces.append(face_resized)
                
                self.frameProcessed.emit(self.frame.copy())
                self.facesDetected.emit(detected_faces)
                self.frame = None
                
            self.msleep(10)

    def stop(self):
        self.running = False