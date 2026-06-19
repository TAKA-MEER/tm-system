import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Float32MultiArray
import time
class DirectCtrlSelectorNode(Node):
    def __init__(self):
        super().__init__('direct_ctrl_selector')
        
        # Parameters
        self.declare_parameter('tread_width', 0.424) # 車輪の左右間隔 (m)
        self.declare_parameter('manual_timeout', 0.5) # 手動入力のタイムアウト (sec)
        self.declare_parameter('auto_timeout', 0.5) # 自動入力のタイムアウト (sec)
        self.declare_parameter('publish_rate', 20.0) # パブリッシュ周期 (Hz)
        
        self.tread_width = self.get_parameter('tread_width').value
        self.manual_timeout = self.get_parameter('manual_timeout').value
        self.auto_timeout = self.get_parameter('auto_timeout').value
        
        # Subscribers
        self.sub_cmd_vel_auto = self.create_subscription(
            Twist, '/cmd_vel', self.auto_cmd_callback, 10)
        self.sub_cmd_vel_manual = self.create_subscription(
            Twist, '/cmd_vel/manual', self.manual_cmd_callback, 10)
            
        # Publishers
        self.pub_crawler_cmd = self.create_publisher(
            Float32MultiArray, '/crawler/cmd', 10)
            
        # State
        self.latest_auto_msg = Twist()
        self.latest_manual_msg = Twist()
        self.last_auto_time = 0.0
        self.last_manual_time = 0.0
        
        # Timer
        timer_period = 1.0 / self.get_parameter('publish_rate').value
        self.timer = self.create_timer(timer_period, self.timer_callback)
        
        self.get_logger().info('Direct Control Selector Node has been started.')
    def auto_cmd_callback(self, msg):
        self.latest_auto_msg = msg
        self.last_auto_time = time.time()
    def manual_cmd_callback(self, msg):
        self.latest_manual_msg = msg
        self.last_manual_time = time.time()
        
    def timer_callback(self):
        current_time = time.time()
        
        active_msg = Twist()
        
        # Determine which command to use (manual takes priority)
        is_manual_active = (current_time - self.last_manual_time) < self.manual_timeout
        is_auto_active = (current_time - self.last_auto_time) < self.auto_timeout
        
        if is_manual_active:
            active_msg = self.latest_manual_msg
        elif is_auto_active:
            active_msg = self.latest_auto_msg
        else:
            # Both timed out, active_msg remains zero Twist (stop)
            pass
            
        # Convert to crawler commands (differential drive)
        v = active_msg.linear.x
        omega = active_msg.angular.z
        
        # v_l = v - (omega * d) / 2
        # v_r = v + (omega * d) / 2
        v_l = v - (omega * self.tread_width) / 2.0
        v_r = v + (omega * self.tread_width) / 2.0
        
        # 速度に変化があった場合のみログ出力 (ターミナルが埋まるのを防ぐため)
        if abs(v_l - getattr(self, '_last_v_l', -999)) > 0.001 or abs(v_r - getattr(self, '_last_v_r', -999)) > 0.001:
            self.get_logger().info(f"Target Velocity -> L: {v_l:.3f} m/s, R: {v_r:.3f} m/s")
            self._last_v_l = v_l
            self._last_v_r = v_r
        # Publish
        msg = Float32MultiArray()
        msg.data = [float(v_l), float(v_r)]
        self.pub_crawler_cmd.publish(msg)
def main(args=None):
    rclpy.init(args=args)
    node = DirectCtrlSelectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
if __name__ == '__main__':
    main()