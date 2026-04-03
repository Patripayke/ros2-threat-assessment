import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32, Bool
import pyaudio
import numpy as np
import threading

class AudioNode(Node):
    def __init__(self):
        super().__init__('audio_node')
        self.energy_pub = self.create_publisher(Float32, '/audio/energy', 10)
        self.vad_pub = self.create_publisher(Bool, '/audio/voice_detected', 10)

        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=1024
        )

        
        self.running = True
        self.thread = threading.Thread(target=self.audio_loop)
        self.thread.daemon = True
        self.thread.start()
        self.get_logger().info('Audio node started')

    def audio_loop(self):
        while self.running:
            try:
                data = np.frombuffer(
                    self.stream.read(1024, exception_on_overflow=False),
                    dtype=np.int16)

                
                rms = float(np.sqrt(np.mean(data.astype(np.float32) ** 2)))

                
                voice_detected = rms > 500

                energy_msg = Float32()
                energy_msg.data = rms
                self.energy_pub.publish(energy_msg)

                vad_msg = Bool()
                vad_msg.data = voice_detected
                self.vad_pub.publish(vad_msg)

                if voice_detected:
                    self.get_logger().info(f'Audio: voice/sound detected — RMS {rms:.1f}')

            except Exception as e:
                self.get_logger().warn(f'Audio error: {e}')

    def destroy_node(self):
        self.running = False
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = AudioNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()