import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from tm_system_msgs.msg import TrackedHumanList


class HumanSelectorNode(Node):

    def __init__(self):
        super().__init__('human_selector')
        self.sub = self.create_subscription(
            TrackedHumanList, '/humans/tracked', self.callback, 10)
        self.pub = self.create_publisher(
            PoseStamped, '/humans/target_point', 10)

    def callback(self, msg):
        output = PoseStamped()
        output.header = msg.header
        if msg.humans:
            target = msg.humans[0]
            output.pose.position.x = target.position.x
            output.pose.position.y = target.position.y
            output.pose.position.z = target.position.z
        self.pub.publish(output)


def main(args=None):
    rclpy.init(args=args)
    node = HumanSelectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
