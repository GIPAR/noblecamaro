#pragma once

#include <rclcpp/rclcpp.hpp>
#include <rclcpp_lifecycle/lifecycle_node.hpp>
#include <geometry_msgs/msg/twist.hpp>
#include <sensor_msgs/msg/laser_scan.hpp>
#include <nav2_behaviors/timed_behavior.hpp>
#include <nav2_msgs/action/back_up.hpp>
#include <cmath>
#include <string>
#include <vector>
#include <algorithm>

namespace camaro_nav
{

/**
 * AckermannRecovery
 *
 * Plugin de recovery behavior pro Nav2 que substitui o BackUp padrão.
 * Em vez de ré fixa, ele:
 *
 *  1. Lê o /scan_filtered dividido em 4 zonas (frente, trás, esq, dir)
 *  2. Calcula o espaço livre atrás com margem de segurança
 *  3. Decide a manobra:
 *     - Espaço atrás suficiente → ré simples com distância calculada
 *     - Corredor estreito       → sequência de "3 pontos" Ackermann
 *                                 (ré com esterço + avança com esterço oposto)
 *  4. Publica cmd_vel_nav em malha fechada até completar a manobra
 *     ou atingir timeout
 *
 * Parâmetros Nav2 (behavior_server/ros__parameters):
 *   ackermann_recovery:
 *     wheelbase            = 0.71
 *     max_steering_angle   = 0.6
 *     robot_half_width     = 0.23
 *     robot_half_length    = 0.30
 *     backup_speed         = 0.12   (m/s, positivo — invertido internamente)
 *     min_clearance_rear   = 0.20   (m — margem mínima atrás)
 *     min_clearance_side   = 0.15   (m — margem mínima lateral)
 *     three_point_speed    = 0.08   (m/s durante manobra de 3 pontos)
 *     max_maneuver_time    = 30.0   (s — timeout total)
 *     scan_topic           = "scan_filtered"
 *     cmd_vel_topic        = "cmd_vel_nav"
 */
class AckermannRecovery : public nav2_behaviors::TimedBehavior<nav2_msgs::action::BackUp>
{
public:
  using BackUpAction = nav2_msgs::action::BackUp;
  using BackUpGoal   = BackUpAction::Goal;

  AckermannRecovery();
  ~AckermannRecovery() override = default;

  // Interface TimedBehavior
  nav2_behaviors::ResultStatus onRun(const std::shared_ptr<const BackUpGoal> goal) override;
  nav2_behaviors::ResultStatus onCycleUpdate() override;
  void onConfigure() override;
  void onCleanup() override;

  // Interface nav2_core::Behavior — diz qual camada do costmap este
  // recovery precisa. Não usamos o costmap diretamente (usamos o LIDAR
  // crudo), então pedimos a camada mais simples possível.
  nav2_core::CostmapInfoType getResourceInfo() override
  {
    return nav2_core::CostmapInfoType::NONE;
  }

private:
  // ── Estrutura de leitura do LIDAR ──
  struct ScanZones {
    double front_min;   // distância mínima na frente (0° ± 30°)
    double rear_min;    // distância mínima atrás (180° ± 30°)
    double left_min;    // distância mínima esquerda (90° ± 45°)
    double right_min;   // distância mínima direita (270° ± 45°)
  };

  // ── Tipos de manobra ──
  enum class ManeuverType {
    SIMPLE_BACKUP,    // ré simples com distância calculada
    THREE_POINT,      // manobra de 3 pontos Ackermann
    IMPOSSIBLE        // sem saída — falha o recovery
  };

  // ── Etapas da manobra de 3 pontos ──
  enum class ThreePointStep {
    REVERSE_WITH_STEER,   // ré com esterço máximo
    FORWARD_WITH_STEER,   // avança com esterço oposto
    REVERSE_STRAIGHT,     // ré reta final (abre espaço)
    DONE
  };

  // Leitura e análise do LIDAR
  ScanZones analyzeScan(const sensor_msgs::msg::LaserScan & scan);
  void scanCallback(const sensor_msgs::msg::LaserScan::SharedPtr msg);

  // Decisão de manobra
  ManeuverType decideManuever(const ScanZones & zones);
  double computeSafeBackupDistance(const ScanZones & zones);

  // Execução
  nav2_behaviors::ResultStatus executeSimpleBackup();
  nav2_behaviors::ResultStatus executeThreePoint();
  void publishCmdVel(double linear_x, double angular_z);
  void stopRobot();

  // Publicação / Subscription
  rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr cmd_vel_pub_;
  rclcpp::Subscription<sensor_msgs::msg::LaserScan>::SharedPtr scan_sub_;

  // Estado da manobra
  sensor_msgs::msg::LaserScan::SharedPtr latest_scan_;
  ManeuverType current_maneuver_{ManeuverType::SIMPLE_BACKUP};
  ThreePointStep three_point_step_{ThreePointStep::REVERSE_WITH_STEER};
  double safe_backup_dist_{0.0};
  double traveled_dist_{0.0};
  rclcpp::Time maneuver_start_time_;
  int steer_direction_{1};   // +1 esquerda, -1 direita

  // Parâmetros
  double wheelbase_;
  double max_steering_angle_;
  double robot_half_width_;
  double robot_half_length_;
  double backup_speed_;
  double min_clearance_rear_;
  double min_clearance_side_;
  double three_point_speed_;
  double max_maneuver_time_;
  std::string scan_topic_;
  std::string cmd_vel_topic_;

  // Raio mínimo de curvatura calculado no configure
  double min_turning_radius_;
};

}  // namespace camaro_nav