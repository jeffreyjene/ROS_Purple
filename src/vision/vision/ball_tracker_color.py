#!/home/jeffreyjene/cv_env/bin/python

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import Twist
from cv_bridge import CvBridge
import cv2
import time

class TennisBallTracker(Node):
    def __init__(self):
        super().__init__('tennis_ball_tracker')

        self.bridge = CvBridge()

        self.sub = self.create_subscription(
            Image,
            '/image_raw',
            self.image_callback,
            10)

        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.debug_pub = self.create_publisher(Image, '/debug_image', 10)

        # timing (limit CPU usage)
        self.last_time = 0
        self.process_interval = 0.1  # 10 FPS

    def image_callback(self, msg):
        now = time.time()
        if now - self.last_time < self.process_interval:
            return
        self.last_time = now

        frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        frame = cv2.resize(frame, (320, 240))

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Tennis ball color range (tune if needed)
        lower = (25, 80, 80)
        upper = (45, 255, 255)

        mask = cv2.inRange(hsv, lower, upper)

        # clean noise
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        twist = Twist()
        found = False

        if contours:
            largest = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest)

            if area > 300:
                found = True

                (x, y, w, h) = cv2.boundingRect(largest)
                cx = x + w // 2

                center_x = frame.shape[1] // 2
                error = cx - center_x

                # control
                twist.angular.z = -0.005 * error
                twist.linear.x = 0.1

                # draw box
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.circle(frame, (cx, y + h//2), 5, (0, 0, 255), -1)

        if not found:
            twist.linear.x = 0.0
            twist.angular.z = 0.0

        self.cmd_pub.publish(twist)

        # publish debug image
        debug_msg = self.bridge.cv2_to_imgmsg(frame, 'bgr8')
        self.debug_pub.publish(debug_msg)


def main():
    rclpy.init()
    node = TennisBallTracker()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()

    