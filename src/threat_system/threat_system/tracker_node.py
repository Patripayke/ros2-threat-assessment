import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import json
import numpy as np

class Track:
    def __init__(self, track_id, detection):
        self.track_id = track_id
        self.label = detection['label']
        self.x = detection['x']
        self.y = detection['y']
        self.w = detection['w']
        self.h = detection['h']
        self.confidence = detection['confidence']
        self.hits = 1
        self.misses = 0
        self.history = [(self.x, self.y)]  # position history

    def center(self):
        return (self.x + self.w / 2, self.y + self.h / 2)

    def update(self, detection):
        self.x = detection['x']
        self.y = detection['y']
        self.w = detection['w']
        self.h = detection['h']
        self.confidence = detection['confidence']
        self.hits += 1
        self.misses = 0
        self.history.append((self.x, self.y))
        if len(self.history) > 30:
            self.history.pop(0)

    def is_moving(self):
        if len(self.history) < 5:
            return False
        dx = self.history[-1][0] - self.history[-5][0]
        dy = self.history[-1][1] - self.history[-5][1]
        return np.sqrt(dx**2 + dy**2) > 15

    def is_occluded(self):
        # track exists but hasn't been matched recently
        return self.misses > 0 and self.hits > 3

class TrackerNode(Node):
    def __init__(self):
        super().__init__('tracker_node')
        self.subscription = self.create_subscription(
            String, '/detections/objects', self.track_callback, 10)
        self.publisher = self.create_publisher(String, '/tracker/tracks', 10)

        self.tracks = []
        self.next_id = 0
        self.max_misses = 8      # frames before dropping a track
        self.iou_threshold = 0.2 # minimum overlap to match

        self.get_logger().info('Tracker node started')

    def iou(self, t, d):
        # intersection over union between track and detection
        tx1, ty1 = t.x, t.y
        tx2, ty2 = t.x + t.w, t.y + t.h
        dx1, dy1 = d['x'], d['y']
        dx2, dy2 = d['x'] + d['w'], d['y'] + d['h']

        ix1, iy1 = max(tx1, dx1), max(ty1, dy1)
        ix2, iy2 = min(tx2, dx2), min(ty2, dy2)

        if ix2 < ix1 or iy2 < iy1:
            return 0.0

        intersection = (ix2 - ix1) * (iy2 - iy1)
        union = t.w * t.h + d['w'] * d['h'] - intersection
        return intersection / union if union > 0 else 0.0

    def track_callback(self, msg):
        detections = json.loads(msg.data)

        # match detections to existing tracks
        matched_track_ids = set()
        matched_det_ids = set()

        for i, track in enumerate(self.tracks):
            best_iou = self.iou_threshold
            best_det = None
            best_det_id = None

            for j, det in enumerate(detections):
                if j in matched_det_ids:
                    continue
                if det['label'] != track.label:
                    continue
                score = self.iou(track, det)
                if score > best_iou:
                    best_iou = score
                    best_det = det
                    best_det_id = j

            if best_det is not None:
                track.update(best_det)
                matched_track_ids.add(i)
                matched_det_ids.add(best_det_id)
            else:
                track.misses += 1

        # create new tracks for unmatched detections
        for j, det in enumerate(detections):
            if j not in matched_det_ids:
                self.tracks.append(Track(self.next_id, det))
                self.next_id += 1

        # remove dead tracks
        self.tracks = [t for t in self.tracks if t.misses < self.max_misses]

        # publish active tracks
        output = []
        for track in self.tracks:
            output.append({
                'id': track.track_id,
                'label': track.label,
                'x': track.x,
                'y': track.y,
                'w': track.w,
                'h': track.h,
                'confidence': track.confidence,
                'hits': track.hits,
                'is_moving': int(track.is_moving()),
                'is_occluded': int(track.is_occluded()),
            })

        msg_out = String()
        msg_out.data = json.dumps(output)
        self.publisher.publish(msg_out)

        if output:
            for t in output:
                status = []
                if t['is_moving']:
                    status.append('moving')
                if t['is_occluded']:
                    status.append('OCCLUDED')
                status_str = ' | '.join(status) if status else 'static'
                self.get_logger().info(
                    f"Track #{t['id']} {t['label']} {t['confidence']:.0%} — {status_str}")

def main(args=None):
    rclpy.init(args=args)
    node = TrackerNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()