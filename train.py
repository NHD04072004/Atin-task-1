from ultralytics import YOLO

def main():
    model = YOLO('yolov8n.pt', task='detect')
    model.train(
        data='WIDER_FACE_YOLO/train.yaml',
        epochs=10,
        batch=32,
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        flipud=0.5,
        fliplr=0.5,
        mosaic=1.0,
        mixup=0.0,
        auto_augment=True,
        workers=4
    )

if __name__ == "__main__":
    main()
