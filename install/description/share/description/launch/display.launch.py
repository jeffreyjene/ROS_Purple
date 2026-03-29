from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import Command
from launch_ros.substitutions import FindPackageShare
import os


def generate_launch_description():

    pkg_share = FindPackageShare('description').find('description')

    xacro_file = os.path.join(pkg_share, 'urdf', 'robot.urdf.xacro')

    return LaunchDescription([

        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{
                'robot_description': Command(['xacro ', xacro_file])
            }]
        ),

        Node(
            package='rviz2',
            executable='rviz2',
            output='screen'
        )
    ])