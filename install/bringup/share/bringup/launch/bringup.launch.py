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

    # -----------------------------
    # Files
    # -----------------------------
    teleop_config = os.path.join(control_pkg, 'config', 'teleop.yaml')

    slam_config = os.path.join(control_pkg, 'config', 'slam.yaml')

   
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
        # SLAM Toolbox (DELAYED START)
        # ----------------------------------
        TimerAction(
            period=3.0,  # delay in seconds (IMPORTANT)
            actions=[
                IncludeLaunchDescription(
                    PythonLaunchDescriptionSource(
                        os.path.join(
                            get_package_share_directory('slam_toolbox'),
                            'launch',
                            'online_sync_launch.py'
                        )
                    ),
                    launch_arguments={
                        'use_sim_time': 'false',
                        'slam_params_file': slam_config,
                    }.items(),
                )
            ]
        ),

        # ----------------------------------
        # Map Server
        # ----------------------------------
        # Node(
        #     package='nav2_map_server',
        #     executable='map_server',
        #     name='map_server',
        #     output='screen',
        #     parameters=[{
        #         'yaml_filename': '/home/jeffreyjene/Maps/my_map.yaml'
        #     }]
        # ),

        # # ----------------------------------
        # # AMCL (localization)
        # # ----------------------------------
        # Node(
        #     package='nav2_amcl',
        #     executable='amcl',
        #     name='amcl',
        #     output='screen',
        #     parameters=[{
        #         'base_frame_id': 'base_link',
        #         'odom_frame_id': 'odom',
        #         'scan_topic': 'scan'
        #     }]
        # ),

        # # ----------------------------------
        # # Lifecycle manager (required!)
        # # ----------------------------------
        # Node(
        #     package='nav2_lifecycle_manager',
        #     executable='lifecycle_manager',
        #     name='lifecycle_manager_localization',
        #     output='screen',
        #     parameters=[{
        #         'use_sim_time': False,
        #         'autostart': True,
        #         'node_names': ['map_server', 'amcl']
        #     }]
        # ),

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