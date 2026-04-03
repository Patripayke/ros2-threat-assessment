import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import json
import csv
import os
from datetime import datetime

class LoggerNode(Node):
    def __init__(self):
        super().__init__('logger_node')
        self.subscription = self.create_subscription(
            String, '/threat/level', self.log_callback, 10)

     
        self.log_dir = os.path.expanduser('~/threat_ws/logs')
        os.makedirs(self.log_dir, exist_ok=True)

  
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_path = os.path.join(self.log_dir, f'session_{timestamp}.csv')

        with open(self.log_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'threat_level', 'label', 'score',
                'person_count', 'moving_count', 'occluded_count',
                'fast_radar_targets', 'audio_energy', 'voice_detected',
                'contributing_factors'
            ])

        self.prev_level = None
        self.get_logger().info(f'Logger node started — saving to {self.log_path}')

    def log_callback(self, msg):
        data = json.loads(msg.data)
        level = data['level']

      
        with open(self.log_path, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'),
                level,
                data['label'],
                data['score'],
                data['person_count'],
                data['moving_count'],
                data['occluded_count'],
                data['fast_radar_targets'],
                data['audio_energy'],
                data['voice_detected'],
                '|'.join(data['contributing_factors'])
            ])

        if level != self.prev_level:
            self.get_logger().info(
                f'Logged level change: {self.prev_level} → {level} '
                f'({data["label"]}) score: {data["score"]:.2f}')
            self.prev_level = level

def main(args=None):
    rclpy.init(args=args)
    node = LoggerNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()