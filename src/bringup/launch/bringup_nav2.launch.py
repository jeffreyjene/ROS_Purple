from launch.actions import TimerAction
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.conditions import IfCondition
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import Command
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():

    # -----------------------------
    # Package paths
    # -----------------------------
    control_pkg = FindPackageShare('control').find('control')
    nav_pkg = FindPackageShare('navigation').find('navigation')

    # -----------------------------
    # Files
    # -----------------------------
    teleop_config = os.path.join(control_pkg, 'config', 'teleop.yaml')

    slam_config = os.path.join(control_pkg, 'config', 'slam.yaml')

    nav2_config = os.path.join(nav_pkg, 'config', 'nav2.yaml')

    return LaunchDescription([


        # ----------------------------------
        # Arduino Bridge (Odometry)
        # ----------------------------------
        Node(
            package='control',
            executable='arduino_bridge',
            name='arduino_bridge',
            output='screen'
        ),



        # ----------------------------------
        # LiDAR
        # ----------------------------------
        Node(
            package='ldlidar_stl_ros2',
            executable='ldlidar_stl_ros2_node',
            name='ldlidar',
            output='screen',
            parameters=[{
                'product_name': 'LDLiDAR_LD06',
                'topic_name': 'scan',
                'frame_id': 'laser_frame',
                'port_name': '/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0',
                'port_baudrate': 230400,
                'laser_scan_dir': True,
                'enable_angle_crop_func': False
            }]
        ),

        # ----------------------------------
        # Static TF: base_link → laser_frame
        # ----------------------------------
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='laser_tf',
            arguments=[
                '0', '0', '0.20',   # x y z (meters)
                '0', '0', '0',      # roll pitch yaw (radians)
                'base_link',
                'laser_frame'
            ],
            output='screen'
        ),
        
        # ----------------------------------
        # Nav2
        # ----------------------------------
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(
                    get_package_share_directory('nav2_bringup'),
                    'launch',
                    'localization_launch.py'
                )
            ),
            launch_arguments={
                'use_sim_time': 'false',
                'map': '/home/jeffreyjene/Maps/my_map.yaml',
                'params_file': nav2_config
            }.items(),
        ),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(
                    get_package_share_directory('nav2_bringup'),
                    'launch',
                    'navigation_launch.py'
                )
            ),
            launch_arguments={
                'use_sim_time': 'false',
                'map': '/home/jeffreyjene/Maps/my_map.yaml',
                'params_file': nav2_config,
                'use_sim_time': 'false',
                'autostart': 'true',
            }.items(),
        ),

        # ----------------------------------
        # Joystick
        # ----------------------------------
        Node(
            package='joy',
            executable='joy_node',
            name='joy_node',
            output='screen'
        ),

        # ----------------------------------
        # Teleop
        # ----------------------------------
        Node(
            package='teleop_twist_joy',
            executable='teleop_node',
            name='teleop_twist_joy',
            output='screen',
            parameters=[teleop_config]
        ),

    ])