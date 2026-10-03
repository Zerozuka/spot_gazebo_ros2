# Spot Simulation in Gazebo

A ROS 2 Jazzy simulation package for the Boston Dynamics Spot robot using Gazebo Harmonic (Gazebo Sim 8). This package provides:

- Full URDF/SDF robot description for simulation
- Integration with CHAMP quadruped controller
- Launch files for easy simulation setup
- Gazebo world configurations
- ROS 2/Gazebo bridge configuration for sensor and control interfaces

<div style="display: flex; gap: 10px;">
    <img src="assets/walking_rviz.gif" height="200">
    <img src="assets/simple_tunnel_nav.gif" height="200">
    <img src="assets/edgar_mine_nav.gif" height="200">
</div>

## ROS graph
![rosgraph](assets/rosgraph.png)

## Note
1. Spot meshes are bundled; worlds can also reference Gazebo Fuel assets.
2. The SDF includes LiDAR, IMU, thermal, body camera and depth sensors. Rendering all sensors can be expensive on a software-rendered virtual desktop.

## Included packages

* `champ` - Core CHAMP quadruped controller integration package adapted for ROS 2 Jazzy and Spot
* `champ_base` - Base implementation of quadruped controller with gait generators and kinematics
* `champ_config` - Configuration package containing robot-specific parameters and settings for the CHAMP quadruped controller
* `champ_msgs` - Custom ROS 2 message definitions for quadruped control and state information
* `spot_bringup` - Launch files and configuration to start Spot simulation with all required nodes
* `spot_description` - URDF and SDF robot description files defining Spot's model for ROS 2 and Gazebo
* `spot_gazebo` - Ignition Gazebo simulation specific files including worlds and simulation plugins
    * [Simple Tunnel](https://app.gazebosim.org/OpenRobotics/fuel/worlds/Tunnel%20Simple%2002)

        <div style="display: flex; gap: 10px;">
            <img src="assets/simple_tunnel_1.png" height="200" width="400">
            <img src="assets/simple_tunnel_2.png" height="200" width="200">
        </div>

    * [Edgar Mine](https://app.gazebosim.org/OpenRobotics/fuel/models/Edgar%20Mine%20Virtual%20STIX)

        <div style="display: flex; gap: 10px;">
            <img src="assets/edgar_mine_2.png" height="200" width="400">
            <img src="assets/edgar_mine_1.png" height="200" width="200">
        </div>

## Install

### Requirements

- Ubuntu 24.04
- [ROS 2 Jazzy](https://docs.ros.org/en/jazzy/Installation.html)
- [Gazebo Harmonic](https://gazebosim.org/docs/harmonic/install/)

## Usage

1. Install dependencies
    ```bash
    cd ~/ros2_ws
    source /opt/ros/jazzy/setup.bash
    sudo rosdep init
    rosdep update
    rosdep install --from-paths src --ignore-src -r -i -y --rosdistro jazzy
    ```
2. Build the project
    ```bash
    colcon build --symlink-install --cmake-args -DBUILD_TESTING=OFF -DPython3_EXECUTABLE=/usr/bin/python3
    ```
3. Source the workspace
    ```bash
    source ~/ros2_ws/install/setup.sh
    ```
4. Launch the simulation
    ```bash
    ros2 launch spot_bringup spot.gazebo.launch.py
    ```

## Jazzy / NoMachine wall_demo

The [wall_demo guide](docs/JAZZY_WALL_DEMO.md) includes the environment setup,
GUI launch on `DISPLAY=:1001`, a bounded walking verification, and captured images.
The bundled world preserves [liudazhi/wall_demo](https://app.gazebosim.org/liudazhi/fuel/worlds/wall_demo)
geometry and adds Spot, an Ogre2 sensor renderer and a GUI camera.

From this repository root, after building:

```zsh
source scripts/setup.zsh
export DISPLAY=:1001
ros2 launch spot_bringup spot.gazebo.launch.py world_file:=wall_demo.sdf
```

In another terminal, use the same setup and run:

```zsh
source scripts/setup.zsh
/usr/bin/python3 scripts/walk_demo.py --capture
```

This sends a short forward velocity command and then stops. It verifies odometry,
posture and sensor delivery; it is not autonomous navigation. Run it once from the
clear spawn area, or restart the world before repeating it.

## Tasks Demonstration

### SLAM
<div style="display: flex; gap: 10px;">
    <img src="assets/demo_MOLA_rviz.png" width="400">
</div>

### LiDAR Odometry
<div style="display: flex; gap: 10px;">
    <img src="assets/trajectory_comparison.png" width="400">
</div>

### Object Detection, Segmentation and Pose Estimation
<div style="display: flex; gap: 10px;">
    <img src="assets/yolo_thermal_1.png" height="200" width="200">
    <img src="assets/yolo_thermal_3.png" height="200" width="200">
    <img src="assets/yolo_thermal_2.png" height="200" width="200">
</div>

### Navigation
1. Start the gazebo siimulation
```
ros2 launch spot_bringup spot.gazebo.launch.py rviz:=false
```

2. Use `SLAM` to build a map
```
ros2 launch spot_navigation online_async_launch.py
```

3. Once the map is built and saved
```
ros2 launch spot_navigation localization_launch.py map:=simple_tunnel.yaml use_sim_time:=true rviz:=true
```
NOTE currently the quality of AMCL is really bad so better find something better to use

## TODO
1. Integrate a better controller like
    * https://github.com/ShuoYangRobotics/A1-QP-MPC-Controller
    * https://github.com/dfki-ric-underactuated-lab/dfki-quad
    * https://github.com/bostoncleek/quadruped_control


## Acknowledgement
* [champ](https://github.com/chvmp/champ/tree/ros2) ros2 branch.
* [spot_config](https://github.com/chvmp/robots/tree/master/configs/spot_config) with some modification.
* [spot_description](https://github.com/clearpathrobotics/spot_ros) for URDF.
