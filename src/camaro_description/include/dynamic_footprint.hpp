#pragma once

#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/joint_state.hpp>
#include <geometry_msgs/msg/polygon_stamped.hpp>
#include <geometry_msgs/msg/point32.hpp>
#include <vector>
#include <string>
#include <cmath>

namespace camaro_nav
{

/**
 * DynamicFootprintNode
 *
 * Subscreve /joint_states, lê o ângulo médio dos steering joints
 * (front_left_wheel_steering_joint e front_right_wheel_steering_joint),
 * recalcula o polígono real que o chassi vai varrer no próximo instante
 * e publica em /dynamic_footprint — que o collision_monitor e o costmap
 * usam como footprint atualizado.
 *
 * Parâmetros ROS2 (todos com defaults):
 *   wheelbase          (double) = 0.71   — distância entre eixos (m)
 *   half_width         (double) = 0.23   — metade da largura do chassi (m)
 *   half_length_front  (double) = 0.30   — distância do base_link à frente (m)
 *   half_length_rear   (double) = 0.30   — distância do base_link à traseira (m)
 *   safety_margin      (double) = 0.05   — margem extra em todos os lados (m)
 *   max_steering_angle (double) = 0.6    — limite do joint de steering (rad)
 *   publish_rate_hz    (double) = 10.0   — frequência de publicação (Hz)
 */
class DynamicFootprintNode : public rclcpp::Node
{
public:
  explicit DynamicFootprintNode(const rclcpp::NodeOptions & options = rclcpp::NodeOptions());

private:
  // Callbacks
  void jointStateCallback(const sensor_msgs::msg::JointState::SharedPtr msg);
  void timerCallback();

  // Cálculo do polígono
  geometry_msgs::msg::PolygonStamped computeFootprint(double steering_angle);

  // Calcula o overhang lateral da quina dianteira externa em curva
  double computeCornerOverhang(double steering_angle);

  // Subscriptions / Publishers
  rclcpp::Subscription<sensor_msgs::msg::JointState>::SharedPtr joint_state_sub_;
  rclcpp::Publisher<geometry_msgs::msg::PolygonStamped>::SharedPtr footprint_pub_;
  rclcpp::TimerBase::SharedPtr timer_;

  // Estado atual do steering
  double current_steering_angle_{0.0};

  // Parâmetros do Camaro (lidos do param server)
  double wheelbase_;
  double half_width_;
  double half_length_front_;
  double half_length_rear_;
  double safety_margin_;
  double max_steering_angle_;
  double publish_rate_hz_;

  // Nomes dos joints de steering no URDF
  const std::string kSteeringJointLeft  = "front_left_wheel_steering_joint";
  const std::string kSteeringJointRight = "front_right_wheel_steering_joint";
};

}  // namespace camaro_nav