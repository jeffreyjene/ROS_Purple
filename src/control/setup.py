from setuptools import find_packages, setup
from glob import glob
import os

package_name = 'control'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/control']),
        ('share/control', ['package.xml']),

        # 🔥 ADD THIS
        (os.path.join('share', 'control', 'config'),
            glob('config/*.yaml')),

        # (optional if you have launch files)
        (os.path.join('share', 'control', 'launch'),
            glob('launch/*.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='jeffreyjene',
    maintainer_email='jeffreyjene@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'arduino_bridge = control.arduino_bridge:main',
        ],
    },
)
