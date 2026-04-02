import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np
import json

LEVEL_COLORS = {
    1: (0, 255, 0),      # green
    2: (0, 255, 255),    # yellow
    3: (0, 165, 255),    # orange
    4: (0, 0, 255),      # red
    5: (0, 0, 180),      # dark red
}

class DashboardNode(Node):
    def __init__(self):
        super().__init__('dashboard_node')

        self.create_subscription(Image, '/camera/image_raw', self.frame_callback, 10)
        self.create_subscription(Image, '/thermal/image', self.thermal_callback, 10)
        self.create_subscription(String, '/threat/level', self.threat_callback, 10)

        self.bridge = CvBridge()
        self.frame = None
        self.thermal = None
        self.threat = None

        self.create_timer(1/30, self.render)
        self.get_logger().info('Dashboard node started')

    def frame_callback(self, msg):
        self.frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

    def thermal_callback(self, msg):
        self.thermal = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

    def threat_callback(self, msg):
        self.threat = json.loads(msg.data)

    def draw_tracks(self, frame, tracks, color):
        for t in tracks:
            x, y, w, h = t['x'], t['y'], t['w'], t['h']
            tid = t['id']
            label = t['label']
            conf = t['confidence']
            moving = t['is_moving']
            occluded = t['is_occluded']

            # box color based on state
            box_color = (0, 165, 255) if moving else (0, 255, 0)
            if occluded:
                box_color = (0, 0, 255)

            cv2.rectangle(frame, (x, y), (x+w, y+h), box_color, 2)

            # label
            status = 'MOV' if moving else ('OCC' if occluded else 'STA')
            text = f'#{tid} {label} {conf:.0%} [{status}]'
            cv2.putText(frame, text, (x, y-8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 1)

        return frame

    def draw_hud(self, frame, threat):
        h, w = frame.shape[:2]
        level = threat['level']
        label = threat['label']
        score = threat['score']
        color = LEVEL_COLORS[level]

        # top bar background
        cv2.rectangle(frame, (0, 0), (w, 60), (20, 20, 20), -1)

        # threat level text
        cv2.putText(frame, f'THREAT LEVEL {level} — {label}',
            (10, 38), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)

        # score bar
        bar_w = int((w - 200) * score)
        cv2.rectangle(frame, (10, 48), (w-190, 56), (60, 60, 60), -1)
        cv2.rectangle(frame, (10, 48), (10 + bar_w, 56), color, -1)
        cv2.putText(frame, f'{score:.2f}', (w-180, 56),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        # sensor panel bottom
        cv2.rectangle(frame, (0, h-80), (w, h), (20, 20, 20), -1)

        # people count
        cv2.putText(frame, f'People: {threat["person_count"]}',
            (10, h-55), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        # moving
        cv2.putText(frame, f'Moving: {threat["moving_count"]}',
            (10, h-35), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        # occluded
        cv2.putText(frame, f'Occluded: {threat["occluded_count"]}',
            (10, h-15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        # radar
        cv2.putText(frame, f'Radar targets: {threat["fast_radar_targets"]}',
            (160, h-55), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        # audio energy bar
        audio = min(threat['audio_energy'] / 3000.0, 1.0)
        audio_bar = int(200 * audio)
        cv2.putText(frame, 'Audio:', (160, h-35),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.rectangle(frame, (210, h-45), (410, h-30), (60, 60, 60), -1)
        cv2.rectangle(frame, (210, h-45), (210+audio_bar, h-30),
            (0, 255, 255) if threat['voice_detected'] else (100, 200, 100), -1)

        # contributing factors
        factors = ', '.join(threat['contributing_factors']) if threat['contributing_factors'] else 'none'
        cv2.putText(frame, f'Factors: {factors}',
            (160, h-15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)

        return frame

    def render(self):
        if self.frame is None or self.threat is None:
            return

        # main frame with tracks
        display = self.frame.copy()
        display = self.draw_tracks(display, self.threat['tracks'], (0, 255, 0))
        display = self.draw_hud(display, self.threat)

        # thermal panel — small in corner
        if self.thermal is not None:
            th = cv2.resize(self.thermal, (320, 180))
            display[65:245, display.shape[1]-325:display.shape[1]-5] = th
            cv2.rectangle(display,
                (display.shape[1]-325, 65),
                (display.shape[1]-5, 245), (100, 100, 100), 1)
            cv2.putText(display, 'THERMAL',
                (display.shape[1]-320, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 200, 200), 1)

        cv2.imshow('Threat Assessment System', display)
        cv2.waitKey(1)

    def destroy_node(self):
        cv2.destroyAllWindows()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = DashboardNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()