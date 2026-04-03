import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np

class ThermalNode(Node):
    def __init__(self):
        super().__init__('thermal_node')
        self.subscription = self.create_subscription(
            Image, '/camera/image_raw', self.process_frame, 10)
        self.publisher = self.create_publisher(Image, '/thermal/image', 10)
        self.bridge = CvBridge()
        self.get_logger().info('Thermal node started')

    def process_frame(self, msg):

        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

       
        small = cv2.resize(frame, (640, 360))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

       
        thermal = cv2.applyColorMap(gray, cv2.COLORMAP_INFERNO)

       
        noise = np.random.normal(0, 5, thermal.shape).astype(np.int16)
        thermal = np.clip(thermal.astype(np.int16) + noise, 0, 255).astype(np.uint8)

      
        thermal = cv2.resize(thermal, (frame.shape[1], frame.shape[0]))

        out_msg = self.bridge.cv2_to_imgmsg(thermal, encoding='bgr8')
        out_msg.header = msg.header
        self.publisher.publish(out_msg)

def main(args=None):
    rclpy.init(args=args)
    node = ThermalNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()