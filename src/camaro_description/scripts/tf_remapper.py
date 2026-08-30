#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from tf2_msgs.msg import TFMessage
from nav_msgs.msg import Odometry

class FrameRemapper(Node):
    def __init__(self):
        super().__init__('frame_remapper')
        
        # --- TF ---
        self.tf_pub = self.create_publisher(TFMessage, '/tf', 10)
        self.tf_sub = self.create_subscription(TFMessage, '/tf_gz', self.tf_callback, 10)
        
        # --- Odometria ---
        self.odom_pub = self.create_publisher(Odometry, '/odom', 10)
        self.odom_sub = self.create_subscription(Odometry, '/odom_gz', self.odom_callback, 10)
        
        self.get_logger().info('Frame Remapper pronto! Corrigindo TF e Odometria (smart_camaro/* -> *)')

    def tf_callback(self, msg):
        for t in msg.transforms:
            if t.header.frame_id.startswith('smart_camaro/'):
                t.header.frame_id = t.header.frame_id.replace('smart_camaro/', '')
            if t.child_frame_id.startswith('smart_camaro/'):
                t.child_frame_id = t.child_frame_id.replace('smart_camaro/', '')
        self.tf_pub.publish(msg)

    def odom_callback(self, msg):
        if msg.header.frame_id.startswith('smart_camaro/'):
            msg.header.frame_id = msg.header.frame_id.replace('smart_camaro/', '')
        if msg.child_frame_id.startswith('smart_camaro/'):
            msg.child_frame_id = msg.child_frame_id.replace('smart_camaro/', '')
        self.odom_pub.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = FrameRemapper()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()