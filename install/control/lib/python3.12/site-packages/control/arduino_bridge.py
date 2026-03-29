import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, TransformStamped
from nav_msgs.msg import Odometry
from tf2_ros import TransformBroadcaster
import serial
import threading
import time
import math


class ArduinoBridge(Node):
    def __init__(self):
        super().__init__('arduino_bridge')

        # =======================
        # Parameters
        # =======================
        self.declare_parameter('port', '/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0')
        self.declare_parameter('baud', 115200)

        port = self.get_parameter('port').value
        baud = self.get_parameter('baud').value

        self.ser = serial.Serial(port, baud, timeout=0.1)

        # =======================
        # Robot constants
        # =======================
        self.L = 0.176
        self.TICKS_PER_REV = 1940
        self.WHEEL_DIAMETER = 0.065

        self.DIST_PER_TICK = math.pi * self.WHEEL_DIAMETER / self.TICKS_PER_REV

        self.MAX_SPEED = 0.30
        self.MAX_PWM = 90
        self.DEADBAND = 5

        # =======================
        # State
        # =======================
        self.last_left = 0
        self.last_right = 0

        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0

        self.last_time = self.get_clock().now()

        # 🔥 NEW: thread-safe buffer
        self.lock = threading.Lock()
        self.latest_ticks = None

        # =======================
        # ROS interfaces
        # =======================
        self.create_subscription(Twist, '/cmd_vel', self.cmd_callback, 10)

        self.odom_pub = self.create_publisher(Odometry, '/odom', 10)
        self.tf_broadcaster = TransformBroadcaster(self)

        # 🔥 NEW: timer for odometry (main thread)
        self.create_timer(0.02, self.update_odometry)  # 50 Hz

        # =======================
        # Serial thread
        # =======================
        self.thread = threading.Thread(target=self.read_serial_loop)
        self.thread.daemon = True
        self.thread.start()

        self.get_logger().info("Odometry node started")

    # =======================
    # Deadband
    # =======================
    def apply_deadband(self, pwm):
        if abs(pwm) < self.DEADBAND:
            return 0
        return pwm

    # =======================
    # CMD_VEL → Arduino
    # =======================
    def cmd_callback(self, msg):
        v = msg.linear.x
        w = msg.angular.z

        v_left = v - (w * self.L / 2.0)
        v_right = v + (w * self.L / 2.0)

        pwm_left = int((v_left / self.MAX_SPEED) * self.MAX_PWM)
        pwm_right = int((v_right / self.MAX_SPEED) * self.MAX_PWM)

        pwm_left = max(min(pwm_left, self.MAX_PWM), -self.MAX_PWM)
        pwm_right = max(min(pwm_right, self.MAX_PWM), -self.MAX_PWM)

        pwm_left = self.apply_deadband(pwm_left)
        pwm_right = self.apply_deadband(pwm_right)

        cmd = f"CMD {pwm_left} {pwm_right}\n"
        self.ser.write(cmd.encode())

    # =======================
    # Serial Loop (NO ROS CALLS)
    # =======================
    def read_serial_loop(self):
        while rclpy.ok():
            try:
                line = self.ser.readline().decode(errors='ignore').strip()
                if line.startswith("ENC"):
                    _, l, r = line.split()

                    with self.lock:
                        self.latest_ticks = (int(l), int(r))

            except Exception as e:
                self.get_logger().error(str(e))
                time.sleep(1)

    # =======================
    # Odometry Update (MAIN THREAD)
    # =======================
    def update_odometry(self):
        with self.lock:
            if self.latest_ticks is None:
                return
            left, right = self.latest_ticks
            self.latest_ticks = None

        dl_ticks = left - self.last_left
        dr_ticks = right - self.last_right

        self.last_left = left
        self.last_right = right

        dl = dl_ticks * self.DIST_PER_TICK
        dr = dr_ticks * self.DIST_PER_TICK

        ds = (dr + dl) / 2.0
        dtheta = (dr - dl) / self.L

        now = self.get_clock().now()
        dt = (now - self.last_time).nanoseconds * 1e-9
        self.last_time = now

        if dt <= 0:
            return

        # Update pose
        self.x += ds * math.cos(self.theta)
        self.y += ds * math.sin(self.theta)
        self.theta += dtheta

        # Velocities
        vx = ds / dt
        vth = dtheta / dt

        self.publish_odom(now, vx, vth)

    # =======================
    # Publish Odom + TF
    # =======================
    def publish_odom(self, now, vx, vth):
        odom = Odometry()

        odom.header.stamp = now.to_msg()
        odom.header.frame_id = "odom"
        odom.child_frame_id = "base_link"

        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y

        qz = math.sin(self.theta / 2.0)
        qw = math.cos(self.theta / 2.0)

        odom.pose.pose.orientation.z = qz
        odom.pose.pose.orientation.w = qw

        odom.twist.twist.linear.x = vx
        odom.twist.twist.angular.z = vth

        self.odom_pub.publish(odom)

        # TF
        t = TransformStamped()
        future_time = now + rclpy.duration.Duration(seconds=0.05)
        t.header.stamp = future_time.to_msg()
        t.header.frame_id = "odom"
        t.child_frame_id = "base_link"

        t.transform.translation.x = self.x
        t.transform.translation.y = self.y

        t.transform.rotation.z = qz
        t.transform.rotation.w = qw

        self.tf_broadcaster.sendTransform(t)


def main():
    rclpy.init()
    node = ArduinoBridge()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()