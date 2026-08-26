#include "camaro_description/dynamic_footprint.hpp"

namespace camaro_nav
{

DynamicFootprintNode::DynamicFootprintNode(const rclcpp::NodeOptions & options)
: Node("dynamic_footprint_node", options)
{
  // ── Declara e lê parâmetros ──
  this->declare_parameter("wheelbase",          0.71);
  this->declare_parameter("half_width",         0.23);
  this->declare_parameter("half_length_front",  0.30);
  this->declare_parameter("half_length_rear",   0.30);
  this->declare_parameter("safety_margin",      0.05);
  this->declare_parameter("max_steering_angle", 0.6);
  this->declare_parameter("publish_rate_hz",    10.0);

  wheelbase_          = this->get_parameter("wheelbase").as_double();
  half_width_         = this->get_parameter("half_width").as_double();
  half_length_front_  = this->get_parameter("half_length_front").as_double();
  half_length_rear_   = this->get_parameter("half_length_rear").as_double();
  safety_margin_      = this->get_parameter("safety_margin").as_double();
  max_steering_angle_ = this->get_parameter("max_steering_angle").as_double();
  publish_rate_hz_    = this->get_parameter("publish_rate_hz").as_double();

  RCLCPP_INFO(get_logger(),
    "DynamicFootprint: wheelbase=%.2f half_width=%.2f front=%.2f rear=%.2f margin=%.2f",
    wheelbase_, half_width_, half_length_front_, half_length_rear_, safety_margin_);

  // ── Subscription: joint_states ──
  joint_state_sub_ = this->create_subscription<sensor_msgs::msg::JointState>(
    "/joint_states", 10,
    std::bind(&DynamicFootprintNode::jointStateCallback, this, std::placeholders::_1));

  // ── Publisher: footprint dinâmico ──
  footprint_pub_ = this->create_publisher<geometry_msgs::msg::PolygonStamped>(
    "/dynamic_footprint", rclcpp::QoS(10).transient_local());

  // ── Timer de publicação ──
  auto period = std::chrono::duration<double>(1.0 / publish_rate_hz_);
  timer_ = this->create_wall_timer(
    std::chrono::duration_cast<std::chrono::nanoseconds>(period),
    std::bind(&DynamicFootprintNode::timerCallback, this));
}

// ─────────────────────────────────────────────────────────────
// Callback: lê ângulo de esterço dos joint_states
// ─────────────────────────────────────────────────────────────
void DynamicFootprintNode::jointStateCallback(
  const sensor_msgs::msg::JointState::SharedPtr msg)
{
  double left_angle  = 0.0;
  double right_angle = 0.0;
  bool found_left    = false;
  bool found_right   = false;

  for (size_t i = 0; i < msg->name.size(); ++i) {
    if (msg->name[i] == kSteeringJointLeft) {
      left_angle = msg->position[i];
      found_left = true;
    } else if (msg->name[i] == kSteeringJointRight) {
      right_angle = msg->position[i];
      found_right = true;
    }
  }

  if (found_left && found_right) {
    // Média dos dois ângulos de steering (Ackermann não é idêntico nos dois lados)
    current_steering_angle_ = (left_angle + right_angle) / 2.0;
  } else if (found_left) {
    current_steering_angle_ = left_angle;
  } else if (found_right) {
    current_steering_angle_ = right_angle;
  }

  // Clamp para o limite físico do joint
  current_steering_angle_ = std::clamp(
    current_steering_angle_, -max_steering_angle_, max_steering_angle_);
}

// ─────────────────────────────────────────────────────────────
// Timer: publica o footprint recalculado
// ─────────────────────────────────────────────────────────────
void DynamicFootprintNode::timerCallback()
{
  auto polygon = computeFootprint(current_steering_angle_);
  footprint_pub_->publish(polygon);
}

// ─────────────────────────────────────────────────────────────
// Cálculo do polígono dinâmico
//
// Lógica:
//   - Sem esterço: retângulo simples do chassi + safety_margin
//   - Com esterço: expande a quina dianteira externa lateralmente
//     pelo overhang calculado geometricamente pelo arco Ackermann
//     e expande a quina traseira interna (efeito "tail swing")
// ─────────────────────────────────────────────────────────────
geometry_msgs::msg::PolygonStamped DynamicFootprintNode::computeFootprint(
  double steering_angle)
{
  geometry_msgs::msg::PolygonStamped polygon;
  polygon.header.stamp    = this->now();
  polygon.header.frame_id = "base_link";

  const double margin = safety_margin_;
  const double front  = half_length_front_ + margin;
  const double rear   = -(half_length_rear_ + margin);
  const double width  = half_width_ + margin;

  // Overhang da quina dianteira externa em curva
  double corner_overhang = computeCornerOverhang(std::abs(steering_angle));

  // Direção do esterço: positivo = curva à esquerda
  // Quina externa = direita quando vira à esquerda e vice-versa
  double left_expansion  = 0.0;
  double right_expansion = 0.0;

  if (steering_angle > 0.01) {
    // Curva à esquerda: quina dianteira direita é a externa
    right_expansion = corner_overhang;
  } else if (steering_angle < -0.01) {
    // Curva à direita: quina dianteira esquerda é a externa
    left_expansion = corner_overhang;
  }

  // Tail swing traseiro (menor que o frontal, ~30% do overhang)
  double tail_swing = corner_overhang * 0.3;

  // ── 4 vértices do polígono (sentido anti-horário) ──
  // Frente-esquerda
  geometry_msgs::msg::Point32 fl;
  fl.x = front;
  fl.y = width + left_expansion;
  fl.z = 0.0;

  // Frente-direita
  geometry_msgs::msg::Point32 fr;
  fr.x = front;
  fr.y = -(width + right_expansion);
  fr.z = 0.0;

  // Traseira-direita (com tail swing do lado oposto ao esterço)
  geometry_msgs::msg::Point32 rr;
  rr.x = rear;
  rr.y = -(width + (steering_angle > 0 ? tail_swing : 0.0));
  rr.z = 0.0;

  // Traseira-esquerda
  geometry_msgs::msg::Point32 rl;
  rl.x = rear;
  rl.y = width + (steering_angle < 0 ? tail_swing : 0.0);
  rl.z = 0.0;

  polygon.polygon.points = {fl, fr, rr, rl};

  return polygon;
}

// ─────────────────────────────────────────────────────────────
// Calcula o overhang lateral da quina dianteira externa
//
// Geometria Ackermann:
//   R = wheelbase / tan(steering_angle)   — raio de curvatura
//   A quina externa está a sqrt(R² + (wheelbase + half_length_front)²) do centro
//   O overhang lateral = distância_quina_ao_centro_do_arco - R - half_width
// ─────────────────────────────────────────────────────────────
double DynamicFootprintNode::computeCornerOverhang(double abs_steering)
{
  if (abs_steering < 0.01) {
    return 0.0;  // Reto — sem overhang
  }

  // Raio de curvatura do eixo traseiro (referência Ackermann)
  double R = wheelbase_ / std::tan(abs_steering);

  // Distância do centro de curvatura à quina dianteira externa
  // Centro de curvatura está perpendicular ao eixo traseiro a R metros
  double dist_to_front_corner = std::sqrt(
    std::pow(R + half_width_, 2.0) +
    std::pow(wheelbase_ + half_length_front_, 2.0)
  );

  // Overhang = quanto a quina sai além do raio + largura base
  double overhang = dist_to_front_corner - R - half_width_;

  // Clamp: nunca negativo e nunca maior que a largura do carro
  return std::clamp(overhang, 0.0, half_width_);
}

}  // namespace camaro_nav

// ─────────────────────────────────────────────────────────────
// main
// ─────────────────────────────────────────────────────────────
int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<camaro_nav::DynamicFootprintNode>();
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}