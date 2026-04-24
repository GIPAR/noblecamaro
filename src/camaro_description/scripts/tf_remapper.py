#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from tf2_msgs.msg import TFMessage

class TfRemapper(Node):
    def __init__(self):
        super().__init__('tf_remapper')
        self.publisher_ = self.create_publisher(TFMessage, '/tf', 10)
        self.subscription = self.create_subscription(
            TFMessage,
            '/tf_gz',
            self.tf_callback,
            10
        )
        self.get_logger().info('TF Remapper iniciado! Remapeando smart_camaro/* -> *')

    def tf_callback(self, msg):
        for transform in msg.transforms:
            # Remove prefixo smart_camaro/ do frame_id
            if transform.header.frame_id.startswith('smart_camaro/'):
                transform.header.frame_id = transform.header.frame_id.replace('smart_camaro/', '')
            
            # Remove prefixo smart_camaro/ do child_frame_id
            if transform.child_frame_id.startswith('smart_camaro/'):
                transform.child_frame_id = transform.child_frame_id.replace('smart_camaro/', '')
        
        self.publisher_.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = TfRemapper()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
