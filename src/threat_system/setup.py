from setuptools import find_packages, setup

package_name = 'threat_system'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='prateek',
    maintainer_email='prateek@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'camera_node = threat_system.camera_node:main',
            'thermal_node = threat_system.thermal_node:main',
            'radar_node = threat_system.radar_node:main',
            'audio_node = threat_system.audio_node:main',
            'detector_node = threat_system.detector_node:main',
            'tracker_node = threat_system.tracker_node:main',
            'fusion_node = threat_system.fusion_node:main',
            'threat_node = threat_system.threat_node:main',
            'dashboard_node = threat_system.dashboard_node:main',
            'logger_node = threat_system.logger_node:main',
        ],
    },
)
