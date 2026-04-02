import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge
from ultralytics import YOLO # type: ignore
import json
import cv2

class DetectorNode(Node):
    def __init__(self):
        super().__init__('detector_node')
        self.subscription = self.create_subscription(
            Image, '/camera/image_raw', self.detect_callback, 10)
        self.publisher = self.create_publisher(String, '/detections/objects', 10)
        self.bridge = CvBridge()

        # yolov8 nano — fastest, runs on CPU fine
        self.get_logger().info('Loading YOLOv8 model...')
        self.model = YOLO('yolov8n.pt')  # auto downloads on first run
        self.get_logger().info('Detector node ready')

        # skip frames to maintain speed
        self.frame_count = 0
        self.run_every = 3  # run YOLO every 3rd frame

    def detect_callback(self, msg):
        self.frame_count += 1
        if self.frame_count % self.run_every != 0:
            return

        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        small = cv2.resize(frame, (640, 360))

        results = self.model(small, verbose=False, conf=0.4)[0]

        detections = []
        for box in results.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            conf = float(box.conf[0])
            cls = int(box.cls[0])
            label = self.model.names[cls]

            # scale coords back to original frame size
            scale_x = frame.shape[1] / 640
            scale_y = frame.shape[0] / 360

            detections.append({
                'label': label,
                'confidence': round(conf, 2),
                'x': round(x1 * scale_x),
                'y': round(y1 * scale_y),
                'w': round((x2 - x1) * scale_x),
                'h': round((y2 - y1) * scale_y),
            })

        msg_out = String()
        msg_out.data = json.dumps(detections)
        self.publisher.publish(msg_out)

        if detections:
            labels = [f"{d['label']} {d['confidence']:.0%}" for d in detections]
            self.get_logger().info(f'Detected: {", ".join(labels)}')

def main(args=None):
    rclpy.init(args=args)
    node = DetectorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()