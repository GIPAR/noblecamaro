#include "camaro_description/ackermann_recovery.hpp"
#include <pluginlib/class_list_macros.hpp>

namespace camaro_nav
{

AckermannRecovery::AckermannRecovery()
: nav2_behaviors::TimedBehavior<BackUpAction>()
{}

// ─────────────────────────────────────────────────────────────
// onConfigure: lê parâmetros e cria pub/sub
// ─────────────────────────────────────────────────────────────
void AckermannRecovery::onConfigure()
{
  auto node = node_.lock();
  if (!node) {
    throw std::runtime_error("AckermannRecovery: node expirou em onConfigure");
  }

  // Declara parâmetros com defaults do Camaro
  node->declare_parameter("ackermann_recovery.wheelbase",           0.71);
  node->declare_parameter("ackermann_recovery.max_steering_angle",  0.6);
  node->declare_parameter("ackermann_recovery.robot_half_width",    0.23);
  node->declare_parameter("ackermann_recovery.robot_half_length",   0.30);
  node->declare_parameter("ackermann_recovery.backup_speed",        0.12);
  node->declare_parameter("ackermann_recovery.min_clearance_rear",  0.20);
  node->declare_parameter("ackermann_recovery.min_clearance_side",  0.15);
  node->declare_parameter("ackermann_recovery.three_point_speed",   0.08);
  node->declare_parameter("ackermann_recovery.max_maneuver_time",   30.0);
  node->declare_parameter("ackermann_recovery.scan_topic",          std::string("scan_filtered"));
  node->declare_parameter("ackermann_recovery.cmd_vel_topic",       std::string("cmd_vel_nav"));

  wheelbase_          = node->get_parameter("ackermann_recovery.wheelbase").as_double();
  max_steering_angle_ = node->get_parameter("ackermann_recovery.max_steering_angle").as_double();
  robot_half_width_   = node->get_parameter("ackermann_recovery.robot_half_width").as_double();
  robot_half_length_  = node->get_parameter("ackermann_recovery.robot_half_length").as_double();
  backup_speed_       = node->get_parameter("ackermann_recovery.backup_speed").as_double();
  min_clearance_rear_ = node->get_parameter("ackermann_recovery.min_clearance_rear").as_double();
  min_clearance_side_ = node->get_parameter("ackermann_recovery.min_clearance_side").as_double();
  three_point_speed_  = node->get_parameter("ackermann_recovery.three_point_speed").as_double();
  max_maneuver_time_  = node->get_parameter("ackermann_recovery.max_maneuver_time").as_double();
  scan_topic_         = node->get_parameter("ackermann_recovery.scan_topic").as_string();
  cmd_vel_topic_      = node->get_parameter("ackermann_recovery.cmd_vel_topic").as_string();

  // Raio mínimo de curvatura real do Camaro
  min_turning_radius_ = wheelbase_ / std::tan(max_steering_angle_);

  RCLCPP_INFO(node->get_logger(),
    "AckermannRecovery configurado: wheelbase=%.2f raio_min=%.2f m",
    wheelbase_, min_turning_radius_);

  // Publisher cmd_vel
  cmd_vel_pub_ = node->create_publisher<geometry_msgs::msg::Twist>(
    cmd_vel_topic_, rclcpp::SystemDefaultsQoS());

  // Subscriber scan
  scan_sub_ = node->create_subscription<sensor_msgs::msg::LaserScan>(
    scan_topic_, rclcpp::SensorDataQoS(),
    std::bind(&AckermannRecovery::scanCallback, this, std::placeholders::_1));
}

void AckermannRecovery::onCleanup()
{
  cmd_vel_pub_.reset();
  scan_sub_.reset();
  latest_scan_.reset();
}

// ─────────────────────────────────────────────────────────────
// onRun: chamado quando o Nav2 aciona o recovery
// ─────────────────────────────────────────────────────────────
nav2_behaviors::ResultStatus AckermannRecovery::onRun(
  const std::shared_ptr<const BackUpGoal> /*goal*/)
{
  if (!latest_scan_) {
    RCLCPP_WARN(logger_, "AckermannRecovery: sem dados do LIDAR ainda");
    return nav2_behaviors::ResultStatus{nav2_behaviors::Status::FAILED};
  }

  // Analisa o scan atual
  auto zones = analyzeScan(*latest_scan_);

  RCLCPP_INFO(logger_,
    "Zonas LIDAR — frente: %.2f  trás: %.2f  esq: %.2f  dir: %.2f",
    zones.front_min, zones.rear_min, zones.left_min, zones.right_min);

  // Decide qual manobra executar
  current_maneuver_ = decideManuever(zones);

  if (current_maneuver_ == ManeuverType::IMPOSSIBLE) {
    RCLCPP_ERROR(logger_, "AckermannRecovery: sem espaço para manobra!");
    return nav2_behaviors::ResultStatus{nav2_behaviors::Status::FAILED};
  }

  // Calcula distância segura de ré
  safe_backup_dist_ = computeSafeBackupDistance(zones);

  // Decide lado do esterço pelo maior espaço lateral
  steer_direction_ = (zones.left_min >= zones.right_min) ? 1 : -1;

  // Reinicia estado
  traveled_dist_      = 0.0;
  three_point_step_   = ThreePointStep::REVERSE_WITH_STEER;
  maneuver_start_time_ = node_.lock()->now();

  RCLCPP_INFO(logger_,
    "Manobra: %s | dist_ré: %.2f m | esterço: %s",
    current_maneuver_ == ManeuverType::SIMPLE_BACKUP ? "RÉ SIMPLES" : "3 PONTOS",
    safe_backup_dist_,
    steer_direction_ > 0 ? "ESQUERDA" : "DIREITA");

  return nav2_behaviors::ResultStatus{nav2_behaviors::Status::RUNNING};
}

// ─────────────────────────────────────────────────────────────
// onCycleUpdate: executado a cada ciclo do behavior_server
// ─────────────────────────────────────────────────────────────
nav2_behaviors::ResultStatus AckermannRecovery::onCycleUpdate()
{
  auto node = node_.lock();

  // Verifica timeout geral
  double elapsed = (node->now() - maneuver_start_time_).seconds();
  if (elapsed > max_maneuver_time_) {
    RCLCPP_WARN(logger_, "AckermannRecovery: timeout após %.1f s", elapsed);
    stopRobot();
    return nav2_behaviors::ResultStatus{nav2_behaviors::Status::FAILED};
  }

  switch (current_maneuver_) {
    case ManeuverType::SIMPLE_BACKUP:
      return executeSimpleBackup();
    case ManeuverType::THREE_POINT:
      return executeThreePoint();
    default:
      return nav2_behaviors::ResultStatus{nav2_behaviors::Status::FAILED};
  }
}

// ─────────────────────────────────────────────────────────────
// executeSimpleBackup: ré reta com distância calculada
// ─────────────────────────────────────────────────────────────
nav2_behaviors::ResultStatus AckermannRecovery::executeSimpleBackup()
{
  if (!latest_scan_) {
    stopRobot();
    return nav2_behaviors::ResultStatus{nav2_behaviors::Status::FAILED};
  }

  auto zones = analyzeScan(*latest_scan_);

  // Para se detectar obstáculo atrás muito perto
  if (zones.rear_min < min_clearance_rear_) {
    RCLCPP_INFO(logger_, "Ré simples: parou por obstáculo traseiro (%.2f m)", zones.rear_min);
    stopRobot();
    return nav2_behaviors::ResultStatus{nav2_behaviors::Status::SUCCEEDED};
  }

  // Para se atingiu a distância planejada
  if (traveled_dist_ >= safe_backup_dist_) {
    stopRobot();
    return nav2_behaviors::ResultStatus{nav2_behaviors::Status::SUCCEEDED};
  }

  // Publica ré reta
  publishCmdVel(-backup_speed_, 0.0);

  // Estimativa de distância percorrida por integração temporal
  // (ciclo do behavior_server ~ 0.1s com cycle_frequency=10Hz)
  traveled_dist_ += backup_speed_ * 0.1;

  return nav2_behaviors::ResultStatus{nav2_behaviors::Status::RUNNING};
}

// ─────────────────────────────────────────────────────────────
// executeThreePoint: manobra de 3 pontos Ackermann
//
// Passo 1: Ré com esterço máximo no lado com mais espaço
// Passo 2: Avança com esterço oposto (abre o ângulo)
// Passo 3: Ré reta curta para centralizar
// ─────────────────────────────────────────────────────────────
nav2_behaviors::ResultStatus AckermannRecovery::executeThreePoint()
{
  if (!latest_scan_) {
    stopRobot();
    return nav2_behaviors::ResultStatus{nav2_behaviors::Status::FAILED};
  }

  auto zones = analyzeScan(*latest_scan_);

  // Angular do esterço máximo em cada passo
  // Para Ackermann: angular_z = linear_x / turning_radius
  double angular_max = three_point_speed_ / min_turning_radius_;

  switch (three_point_step_)
  {
    // ── Passo 1: Ré com esterço ──
    case ThreePointStep::REVERSE_WITH_STEER:
    {
      // Para se bater atrás
      if (zones.rear_min < min_clearance_rear_) {
        RCLCPP_INFO(logger_, "3-pontos passo 1: parou por traseira (%.2f m)", zones.rear_min);
        stopRobot();
        three_point_step_ = ThreePointStep::FORWARD_WITH_STEER;
        traveled_dist_ = 0.0;
        return nav2_behaviors::ResultStatus{nav2_behaviors::Status::RUNNING};
      }

      if (traveled_dist_ >= safe_backup_dist_) {
        stopRobot();
        three_point_step_ = ThreePointStep::FORWARD_WITH_STEER;
        traveled_dist_ = 0.0;
        return nav2_behaviors::ResultStatus{nav2_behaviors::Status::RUNNING};
      }

      // Ré com esterço no lado com mais espaço
      publishCmdVel(-three_point_speed_, -steer_direction_ * angular_max);
      traveled_dist_ += three_point_speed_ * 0.1;
      return nav2_behaviors::ResultStatus{nav2_behaviors::Status::RUNNING};
    }

    // ── Passo 2: Avança com esterço oposto ──
    case ThreePointStep::FORWARD_WITH_STEER:
    {
      // Para se bater na frente
      if (zones.front_min < (robot_half_length_ + min_clearance_rear_)) {
        RCLCPP_INFO(logger_, "3-pontos passo 2: parou por frontal (%.2f m)", zones.front_min);
        stopRobot();
        three_point_step_ = ThreePointStep::REVERSE_STRAIGHT;
        traveled_dist_ = 0.0;
        return nav2_behaviors::ResultStatus{nav2_behaviors::Status::RUNNING};
      }

      if (traveled_dist_ >= safe_backup_dist_ * 0.5) {
        stopRobot();
        three_point_step_ = ThreePointStep::REVERSE_STRAIGHT;
        traveled_dist_ = 0.0;
        return nav2_behaviors::ResultStatus{nav2_behaviors::Status::RUNNING};
      }

      // Avança com esterço oposto
      publishCmdVel(three_point_speed_, steer_direction_ * angular_max);
      traveled_dist_ += three_point_speed_ * 0.1;
      return nav2_behaviors::ResultStatus{nav2_behaviors::Status::RUNNING};
    }

    // ── Passo 3: Ré reta final ──
    case ThreePointStep::REVERSE_STRAIGHT:
    {
      if (zones.rear_min < min_clearance_rear_ ||
          traveled_dist_ >= safe_backup_dist_ * 0.3)
      {
        stopRobot();
        three_point_step_ = ThreePointStep::DONE;
        return nav2_behaviors::ResultStatus{nav2_behaviors::Status::RUNNING};
      }

      publishCmdVel(-three_point_speed_, 0.0);
      traveled_dist_ += three_point_speed_ * 0.1;
      return nav2_behaviors::ResultStatus{nav2_behaviors::Status::RUNNING};
    }

    case ThreePointStep::DONE:
      RCLCPP_INFO(logger_, "Manobra de 3 pontos concluída!");
      return nav2_behaviors::ResultStatus{nav2_behaviors::Status::SUCCEEDED};

    default:
      return nav2_behaviors::ResultStatus{nav2_behaviors::Status::FAILED};
  }
}

// ─────────────────────────────────────────────────────────────
// analyzeScan: divide o LIDAR em 4 zonas e retorna distância mín
// ─────────────────────────────────────────────────────────────
AckermannRecovery::ScanZones AckermannRecovery::analyzeScan(
  const sensor_msgs::msg::LaserScan & scan)
{
  ScanZones zones{10.0, 10.0, 10.0, 10.0};

  int num_ranges = static_cast<int>(scan.ranges.size());
  if (num_ranges == 0) return zones;

  float angle = scan.angle_min;
  float step  = scan.angle_increment;

  for (int i = 0; i < num_ranges; ++i, angle += step) {
    float r = scan.ranges[i];
    if (!std::isfinite(r) || r < scan.range_min || r > scan.range_max) {
      continue;
    }

    double deg = std::fmod(angle * 180.0 / M_PI + 360.0, 360.0);

    // Frente: 0° ± 40°  ou  320°–360°
    if (deg <= 40.0 || deg >= 320.0) {
      zones.front_min = std::min(zones.front_min, static_cast<double>(r));
    }
    // Esquerda: 50°–130°
    else if (deg >= 50.0 && deg <= 130.0) {
      zones.left_min = std::min(zones.left_min, static_cast<double>(r));
    }
    // Trás: 140°–220°
    else if (deg >= 140.0 && deg <= 220.0) {
      zones.rear_min = std::min(zones.rear_min, static_cast<double>(r));
    }
    // Direita: 230°–310°
    else if (deg >= 230.0 && deg <= 310.0) {
      zones.right_min = std::min(zones.right_min, static_cast<double>(r));
    }
  }

  return zones;
}

// ─────────────────────────────────────────────────────────────
// decideManuever: escolhe a estratégia baseado nas zonas
// ─────────────────────────────────────────────────────────────
AckermannRecovery::ManeuverType AckermannRecovery::decideManuever(
  const ScanZones & zones)
{
  double available_rear = zones.rear_min - min_clearance_rear_;
  double corridor_width = zones.left_min + zones.right_min;

  // Sem espaço nenhum atrás
  if (available_rear <= 0.0) {
    return ManeuverType::IMPOSSIBLE;
  }

  // Espaço atrás suficiente E corredor largo o suficiente pro raio mínimo
  // → ré simples
  bool corridor_fits_turn = corridor_width >= (min_turning_radius_ * 2.0 + robot_half_width_ * 2.0);
  if (available_rear >= 0.25 && corridor_fits_turn) {
    return ManeuverType::SIMPLE_BACKUP;
  }

  // Corredor estreito mas tem algum espaço → tenta 3 pontos
  if (available_rear >= 0.15) {
    return ManeuverType::THREE_POINT;
  }

  return ManeuverType::IMPOSSIBLE;
}

// ─────────────────────────────────────────────────────────────
// computeSafeBackupDistance: calcula distância de ré com margem
// ─────────────────────────────────────────────────────────────
double AckermannRecovery::computeSafeBackupDistance(const ScanZones & zones)
{
  double available = zones.rear_min - min_clearance_rear_;
  // Usa 70% do espaço disponível como margem de segurança
  double safe = available * 0.70;
  // Limita entre 0.10m e 0.60m
  return std::clamp(safe, 0.10, 0.60);
}

// ─────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────
void AckermannRecovery::scanCallback(
  const sensor_msgs::msg::LaserScan::SharedPtr msg)
{
  latest_scan_ = msg;
}

void AckermannRecovery::publishCmdVel(double linear_x, double angular_z)
{
  geometry_msgs::msg::Twist cmd;
  cmd.linear.x  = linear_x;
  cmd.angular.z = angular_z;
  cmd_vel_pub_->publish(cmd);
}

void AckermannRecovery::stopRobot()
{
  publishCmdVel(0.0, 0.0);
}

}  // namespace camaro_nav

// ── Registro do plugin pro pluginlib ──
PLUGINLIB_EXPORT_CLASS(camaro_nav::AckermannRecovery, nav2_core::Behavior)