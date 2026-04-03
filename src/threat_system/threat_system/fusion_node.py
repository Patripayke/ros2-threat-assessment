import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Float32, Bool
import json

class FusionNode(Node):
    def __init__(self):
        super().__init__('fusion_node')

        
        self.create_subscription(String, '/tracker/tracks', self.tracks_callback, 10)
        self.create_subscription(String, '/radar/targets', self.radar_callback, 10)
        self.create_subscription(Float32, '/audio/energy', self.audio_energy_callback, 10)
        self.create_subscription(Bool, '/audio/voice_detected', self.audio_vad_callback, 10)

        self.publisher = self.create_publisher(String, '/fusion/scene', 10)

        
        self.tracks = []
        self.radar_targets = []
        self.audio_energy = 0.0
        self.voice_detected = False

        
        self.create_timer(0.1, self.fuse)
        self.get_logger().info('Fusion node started')

    def tracks_callback(self, msg):
        self.tracks = json.loads(msg.data)

    def radar_callback(self, msg):
        self.radar_targets = json.loads(msg.data)

    def audio_energy_callback(self, msg):
        self.audio_energy = msg.data

    def audio_vad_callback(self, msg):
        self.voice_detected = msg.data

    def fuse(self):
        scene = {
            'person_count': 0,
            'moving_count': 0,
            'occluded_count': 0,
            'fast_radar_targets': 0,
            'audio_energy': round(self.audio_energy, 1),
            'voice_detected': int(self.voice_detected),
            'fused_threat_score': 0.0,
            'tracks': self.tracks,
            'contributing_factors': []
        }

        factors = []
        threat_score = 0.0

        
        people = [t for t in self.tracks if t['label'] == 'person']
        scene['person_count'] = len(people)
        scene['moving_count'] = sum(1 for t in self.tracks if t['is_moving'])
        scene['occluded_count'] = sum(1 for t in self.tracks if t['is_occluded'])

        
        if len(people) > 0:
            threat_score += 0.2
            factors.append('person_detected')

        if len(people) > 1:
            threat_score += 0.15 * (len(people) - 1)
            factors.append(f'{len(people)}_people')

        
        moving_people = [t for t in people if t['is_moving']]
        if moving_people:
            threat_score += 0.2
            factors.append('person_moving')

        
        if scene['occluded_count'] > 0:
            threat_score += 0.15
            factors.append('occlusion_detected')

        
        fast_targets = [t for t in self.radar_targets if t['is_fast']]
        scene['fast_radar_targets'] = len(fast_targets)

        if fast_targets:
            threat_score += 0.15
            factors.append('fast_radar_target')

       
        if self.audio_energy > 2000:
            threat_score += 0.2
            factors.append('loud_audio')
        elif self.audio_energy > 800:
            threat_score += 0.1
            factors.append('elevated_audio')

        if self.voice_detected:
            threat_score += 0.1
            factors.append('voice_detected')

        
        scene['fused_threat_score'] = round(min(threat_score, 1.0), 3)
        scene['contributing_factors'] = factors

        msg_out = String()
        msg_out.data = json.dumps(scene)
        self.publisher.publish(msg_out)

        if threat_score > 0.1:
            self.get_logger().info(
                f"Threat score: {scene['fused_threat_score']:.2f} | "
                f"Factors: {', '.join(factors)}")

def main(args=None):
    rclpy.init(args=args)
    node = FusionNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()