import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import json

LEVELS = {
    1: {'label': 'CLEAR',    'min': 0.0,  'max': 0.2},
    2: {'label': 'LOW',      'min': 0.2,  'max': 0.4},
    3: {'label': 'MODERATE', 'min': 0.4,  'max': 0.6},
    4: {'label': 'HIGH',     'min': 0.6,  'max': 0.8},
    5: {'label': 'CRITICAL', 'min': 0.8,  'max': 1.01},
}

class ThreatNode(Node):
    def __init__(self):
        super().__init__('threat_node')
        self.subscription = self.create_subscription(
            String, '/fusion/scene', self.scene_callback, 10)
        self.publisher = self.create_publisher(String, '/threat/level', 10)

        self.current_level = 1
        self.prev_level = 1
        self.get_logger().info('Threat node started')

    def get_level(self, score):
        for level, info in LEVELS.items():
            if info['min'] <= score < info['max']:
                return level
        return 5

    def scene_callback(self, msg):
        scene = json.loads(msg.data)
        score = scene['fused_threat_score']
        level = self.get_level(score)

        output = {
            'level': level,
            'label': LEVELS[level]['label'],
            'score': score,
            'person_count': scene['person_count'],
            'moving_count': scene['moving_count'],
            'occluded_count': scene['occluded_count'],
            'fast_radar_targets': scene['fast_radar_targets'],
            'audio_energy': scene['audio_energy'],
            'voice_detected': scene['voice_detected'],
            'contributing_factors': scene['contributing_factors'],
            'tracks': scene['tracks'],
        }

        msg_out = String()
        msg_out.data = json.dumps(output)
        self.publisher.publish(msg_out)

        
        if level != self.prev_level:
            self.get_logger().info(
                f'THREAT LEVEL {level} — {LEVELS[level]["label"]} '
                f'(score: {score:.2f}) | {", ".join(scene["contributing_factors"])}')
            self.prev_level = level

def main(args=None):
    rclpy.init(args=args)
    node = ThreatNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()