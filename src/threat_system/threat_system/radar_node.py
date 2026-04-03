import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge
import cv2
import numpy as np
import json

class RadarNode(Node):
    def __init__(self):
        super().__init__('radar_node')
        self.subscription = self.create_subscription(
            Image, '/camera/image_raw', self.process_frame, 10)
        self.publisher = self.create_publisher(String, '/radar/targets', 10)
        self.bridge = CvBridge()

       
        self.prev_gray = None
        self.get_logger().info('Radar node started')

    def process_frame(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        small = cv2.resize(frame, (320, 180))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)

        if self.prev_gray is None:
            self.prev_gray = gray
            return

       
        flow = cv2.calcOpticalFlowFarneback(
            self.prev_gray, gray, None,
            pyr_scale=0.5, levels=2, winsize=10,
            iterations=2, poly_n=5, poly_sigma=1.1, flags=0)

        self.prev_gray = gray

   
        magnitude, angle = cv2.cartToPolar(flow[..., 0], flow[..., 1])

       
        motion_mask = magnitude > 2.0
        targets = []

        if np.any(motion_mask):
        
            mask_uint8 = motion_mask.astype(np.uint8) * 255
            contours, _ = cv2.findContours(
                mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for cnt in contours:
                if cv2.contourArea(cnt) < 50:
                    continue

                x, y, w, h = cv2.boundingRect(cnt)

             
                region_mag = magnitude[y:y+h, x:x+w]
                region_ang = angle[y:y+h, x:x+w]
                avg_velocity = float(np.mean(region_mag))
                avg_angle = float(np.mean(region_ang))

               
                base_distance = np.random.uniform(0.5, 8.0)
                noisy_distance = base_distance + np.random.normal(0, 0.15)

                scale_x = frame.shape[1] / 320
                scale_y = frame.shape[0] / 180

                targets.append({
                    'x': round(x * scale_x),
                    'y': round(y * scale_y),
                    'w': round(w * scale_x),
                    'h': round(h * scale_y),
                    'velocity': round(avg_velocity, 2),
                    'angle_deg': round(np.degrees(avg_angle), 1),
                    'distance_m': round(noisy_distance, 2),
                    'is_fast': avg_velocity > 4.0
                })

        msg_out = String()
        msg_out.data = json.dumps(targets)
        self.publisher.publish(msg_out)

        if targets:
            fast = [t for t in targets if t['is_fast']]
            self.get_logger().info(
                f'Radar: {len(targets)} targets | {len(fast)} fast moving')

def main(args=None):
    rclpy.init(args=args)
    node = RadarNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()