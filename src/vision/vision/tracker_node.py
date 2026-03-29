#!/home/jeffreyjene/cv_env/bin/python

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import Twist
from cv_bridge import CvBridge
import cv2
from ultralytics import YOLO
import time



class VisionTracker(Node):
    def __init__(self):
        super().__init__('vision_tracker')

        self.last_time = 0
        self.process_interval = 0.2  # seconds (5 FPS)

        self.bridge = CvBridge()
        self.model = YOLO("yolov8n.pt")

        self.sub = self.create_subscription(
            Image,
            '/image_raw',
            self.image_callback,
            10)

        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.debug_pub = self.create_publisher(Image, '/debug_image', 10)

    def image_callback(self, msg):

        now = time.time()
        if now - self.last_time < self.process_interval:
            return
        self.last_time = now

        frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        frame = cv2.resize(frame, (224, 224))

        results = self.model(frame)

        h, w, _ = frame.shape
        center_x = w // 2

        twist = Twist()
        found = False

        for r in results:
            for box in r.boxes:
                cls = int(box.cls[0])
                label = self.model.names[cls]

                if label == "person":
                    found = True

                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    obj_center = (x1 + x2) // 2

                    error = obj_center - center_x

                    # control
                    twist.angular.z = -0.003 * error
                    twist.linear.x = 0.1

                    # draw box
                    cv2.rectangle(frame, (x1,y1), (x2,y2), (0,255,0), 2)
                    cv2.putText(frame, "PERSON", (x1, y1-10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)

        if not found:
            twist.linear.x = 0.0
            twist.angular.z = 0.0

        self.cmd_pub.publish(twist)

        debug_msg = self.bridge.cv2_to_imgmsg(frame, 'bgr8')
        self.debug_pub.publish(debug_msg)


def main():
    rclpy.init()
    node = VisionTracker()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()

    