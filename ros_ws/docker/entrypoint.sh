#!/bin/bash
set -e
sudo chown -R ros:ros /ros_ws/build /ros_ws/install /ros_ws/log 2>/dev/null || true
exec "$@"
