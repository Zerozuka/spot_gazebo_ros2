# Source this file from zsh: source scripts/setup.zsh
spot_workspace="${${(%):-%N}:A:h:h}"
source /opt/ros/jazzy/setup.zsh
spot_local_ros="$spot_workspace/.ros-deps/root/opt/ros/jazzy"
if [[ -d "$spot_local_ros" ]]; then
  export AMENT_PREFIX_PATH="$spot_local_ros:${AMENT_PREFIX_PATH:-}"
  export CMAKE_PREFIX_PATH="$spot_local_ros:${CMAKE_PREFIX_PATH:-}"
  export LD_LIBRARY_PATH="$spot_local_ros/lib:${LD_LIBRARY_PATH:-}"
  export PYTHONPATH="$spot_local_ros/lib/python3.12/site-packages:${PYTHONPATH:-}"
fi
if [[ -f "$spot_workspace/install/local_setup.zsh" ]]; then
  source "$spot_workspace/install/local_setup.zsh"
fi
export DISPLAY=:1001
unset spot_workspace spot_local_ros
# Keep this demo separate from other ROS / Gazebo sessions on the host.
export ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-71}
export GZ_PARTITION=${GZ_PARTITION:-spot_gazebo_jazzy}
