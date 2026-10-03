#!/usr/bin/env bash
# Optional, sudo-free supplement for an existing ROS Jazzy installation.
# Normal installations should use rosdep; this only supplies the small packages
# missing from the NoMachine host used for the wall_demo verification.
set -eo pipefail
spot_workspace=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
source /opt/ros/jazzy/setup.bash
spot_deps="$spot_workspace/.ros-deps"
mkdir -p "$spot_deps/debs" "$spot_deps/root"
cd "$spot_deps/debs"
for package in tf2_sensor_msgs rosidl_default_generators rosidl_core_generators ament_lint_auto ament_lint_common; do
  if ! ros2 pkg prefix "$package" >/dev/null 2>&1; then
    apt-get download "ros-jazzy-${package//_/-}"
  fi
done
shopt -s nullglob
for archive in ./*.deb; do
  dpkg-deb --extract "$archive" "$spot_deps/root"
done
# This prefix supplements /opt/ros/jazzy; scripts/setup.zsh supplies its paths.
printf '# Supplemental prefix; source scripts/setup.zsh\n' > "$spot_deps/root/opt/ros/jazzy/local_setup.zsh"
printf 'Local ROS dependencies are in %s\n' "$spot_deps/root/opt/ros/jazzy"
