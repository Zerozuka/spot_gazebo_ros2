#!/usr/bin/python3
"""Drive Spot briefly, verify motion and sensor delivery, then stop.

Run after scripts/setup.zsh and the wall_demo GUI launch. This is an open-loop
walking demonstration in the clear spawn area, not an autonomous navigator.
"""
import argparse
from collections import Counter
import json
import math
import os
import re
import shutil
from pathlib import Path
import subprocess
import time

import rclpy
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Image, Imu, JointState, PointCloud2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--duration', type=float, default=6.0, help='Simulation seconds')
    parser.add_argument('--speed', type=float, default=0.25, help='Forward speed in m/s')
    parser.add_argument('--output', type=Path, default=Path('.cache/wall_demo'))
    parser.add_argument('--capture', action='store_true', help='Capture the DISPLAY=:1001 desktop')
    parser.add_argument('--record', action='store_true', help='Record the DISPLAY=:1001 desktop to MP4')
    args = parser.parse_args()
    if args.record and (shutil.which('ffmpeg') is None or shutil.which('xdpyinfo') is None):
        parser.error('--record requires ffmpeg and xdpyinfo')
    if not (0 < args.duration <= 10 and 0 < args.speed <= 0.4):
        parser.error('Use duration in (0, 10] and speed in (0, 0.4] for the clear demo area')
    args.output.mkdir(parents=True, exist_ok=True)
    rclpy.init()
    node = rclpy.create_node('spot_walk_demo', parameter_overrides=[Parameter('use_sim_time', value=True)])
    pub = node.create_publisher(Twist, '/cmd_vel', 10)
    counts = Counter()
    poses = []
    fields = {}
    samples = {}

    def receive(key, msg):
        counts[key] += 1
        if key == 'odometry':
            p = msg.pose.pose.position
            q = msg.pose.pose.orientation
            roll = math.atan2(2 * (q.w * q.x + q.y * q.z), 1 - 2 * (q.x*q.x + q.y*q.y))
            pitch = math.asin(max(-1., min(1., 2 * (q.w * q.y - q.z * q.x))))
            poses.append({'t': msg.header.stamp.sec + msg.header.stamp.nanosec / 1e9,
                          'x': p.x, 'y': p.y, 'z': p.z, 'roll': roll, 'pitch': pitch})
        elif key == 'pointcloud':
            fields['pointcloud_frame'] = msg.header.frame_id
            fields['pointcloud_fields'] = [f.name for f in msg.fields]
        elif key == 'thermal_rgb':
            fields['thermal_encoding'] = msg.encoding
        samples[key] = True

    subscriptions = [node.create_subscription(typ, topic, lambda msg, key=key: receive(key, msg), qos_profile_sensor_data)
                     for key, typ, topic in [
                         ('odometry', Odometry, '/spot/odometry'),
                         ('joint_states', JointState, '/spot/joint_states'),
                         ('imu', Imu, '/imu/data'),
                         ('pointcloud', PointCloud2, '/velodyne_points'),
                         ('thermal_rgb', Image, '/spot/camera/thermal_rgb')]]
    capture_process = None
    video_process = None
    video_log = None
    video_start = None

    def stop_recording():
        nonlocal video_process, video_log
        if video_process is None:
            return
        process, video_process = video_process, None
        try:
            if process.poll() is None:
                process.communicate(input=b'q', timeout=20)
            if process.returncode != 0:
                raise RuntimeError('Screen recording failed; inspect recording.log')
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=5)
            raise RuntimeError('Screen recorder did not finalize the MP4')
        finally:
            video_log.close()
            video_log = None

    def hold_still(seconds):
        end_time = time.monotonic() + seconds
        while rclpy.ok() and time.monotonic() < end_time:
            pub.publish(Twist())
            rclpy.spin_once(node, timeout_sec=0.05)

    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
            pub.publish(Twist())
            if len(samples) == 5 and len(poses) >= 10 and pub.get_subscription_count():
                break
        else:
            raise RuntimeError(f'Robot/sensors not ready: {dict(counts)}')
        start = poses[-1].copy()
        if args.capture or args.record:
            # View from the north side of the clear aisle, avoiding blocker_br.
            camera_x, camera_y, camera_z = start['x'] + 3.0, start['y'] + 2.2, 2.3
            target_x = start['x'] + args.speed * args.duration * 0.45
            yaw = math.atan2(start['y'] - camera_y, target_x - camera_x)
            pitch = math.atan2(camera_z - 0.45, math.hypot(target_x - camera_x, start['y'] - camera_y))
            qx = -math.sin(pitch / 2) * math.sin(yaw / 2)
            qy = math.sin(pitch / 2) * math.cos(yaw / 2)
            qz = math.cos(pitch / 2) * math.sin(yaw / 2)
            qw = math.cos(pitch / 2) * math.cos(yaw / 2)
            request = (f'pose: {{position: {{x: {camera_x}, y: {camera_y}, z: {camera_z}}}, '
                       f'orientation: {{x: {qx}, y: {qy}, z: {qz}, w: {qw}}}}}')
            os.environ['DISPLAY'] = ':1001'
            subprocess.run(['gz', 'service', '-s', '/gui/move_to/pose', '--reqtype', 'gz.msgs.GUICamera',
                            '--reptype', 'gz.msgs.Boolean', '--timeout', '3000', '--req', request],
                           check=True, timeout=10)
        if args.record:
            hold_still(2.0)  # Allow the camera move to finish before recording.
            display_info = subprocess.check_output(['xdpyinfo', '-display', ':1001'], text=True)
            dimensions = re.search(r'dimensions:\s+(\d+x\d+)', display_info)
            if dimensions is None:
                raise RuntimeError('Could not determine the NoMachine display size')
            video_log = (args.output / 'recording.log').open('w')
            video_process = subprocess.Popen([
                'ffmpeg', '-y', '-loglevel', 'warning', '-f', 'x11grab',
                '-framerate', '20', '-video_size', dimensions.group(1), '-draw_mouse', '0',
                '-i', ':1001', '-vf', 'pad=ceil(iw/2)*2:ceil(ih/2)*2',
                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20',
                '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                str(args.output / 'spot_wall_demo_walking.mp4')],
                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=video_log)
            video_start = time.monotonic()
            hold_still(2.0)  # Include the standing pose at the start of the clip.
            if video_process.poll() is not None:
                stop_recording()
        start_clock = node.get_clock().now().nanoseconds / 1e9
        counts.clear()
        poses.clear()
        command = Twist()
        command.linear.x = args.speed
        deadline = time.monotonic() + 180
        captured = False
        print(f'Walking at {args.speed} m/s for {args.duration} simulation seconds; start={start}', flush=True)
        while rclpy.ok() and time.monotonic() < deadline:
            pub.publish(command)
            rclpy.spin_once(node, timeout_sec=0.05)
            elapsed = node.get_clock().now().nanoseconds / 1e9 - start_clock
            if poses and (poses[-1]['z'] < 0.25 or max(abs(poses[-1]['roll']), abs(poses[-1]['pitch'])) > 0.7):
                raise RuntimeError('Robot posture exceeded demo limits')
            if args.capture and not captured and elapsed >= args.duration / 2:
                capture_process = subprocess.Popen(['/usr/bin/import', '-display', ':1001', '-window', 'root',
                                                     str(args.output / 'spot_wall_demo_walking.png')])
                captured = True
            if elapsed >= args.duration:
                break
        else:
            raise RuntimeError('Simulation clock did not advance within 180 seconds')
        # Stop continuously for one simulation second before measuring the final pose.
        stop_clock = node.get_clock().now().nanoseconds / 1e9
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            pub.publish(Twist())
            rclpy.spin_once(node, timeout_sec=0.05)
            if node.get_clock().now().nanoseconds / 1e9 - stop_clock >= 1:
                break
        end = poses[-1]
        displacement = math.hypot(end['x'] - start['x'], end['y'] - start['y'])
        report = {'start': start, 'end': end, 'displacement_m': displacement,
                  'command_speed_mps': args.speed, 'command_duration_sim_s': args.duration,
                  'message_counts': dict(counts), 'max_abs_roll_rad': max(abs(p['roll']) for p in poses),
                  'max_abs_pitch_rad': max(abs(p['pitch']) for p in poses), **fields}
        report['passed'] = (displacement > args.speed * args.duration * 0.4
                            and fields.get('pointcloud_frame') == 'base_link'
                            and {'x','y','z','intensity','ring','time'} <= set(fields.get('pointcloud_fields', []))
                            and fields.get('thermal_encoding') == 'bgr8'
                            and all(counts[key] > 0 for key in samples))
        if args.record:
            hold_still(2.0)
            stop_recording()
            report['video_file'] = 'spot_wall_demo_walking.mp4'
            report['video_wall_duration_s'] = time.monotonic() - video_start
            report['video_playback_speed'] = 1.0
        (args.output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2), flush=True)
        if not report['passed']:
            raise RuntimeError('Motion/sensor checks failed; inspect verification.json')
    finally:
        if rclpy.ok():
            for _ in range(10):
                pub.publish(Twist())
                rclpy.spin_once(node, timeout_sec=0.05)
        stop_recording()
        if capture_process is not None:
            capture_process.wait(timeout=10)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
