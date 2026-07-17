cmake_minimum_required(VERSION 3.8)
project(camaro_description)

# ============================================================
# Dependências existentes (não alteradas)
# ============================================================
find_package(ament_cmake REQUIRED)
find_package(rclpy REQUIRED)
find_package(tf2_msgs REQUIRED)

# ============================================================
# Novas dependências C++ — Camadas 1 e 2
# ============================================================
find_package(rclcpp REQUIRED)
find_package(rclcpp_lifecycle REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(nav2_core REQUIRED)
find_package(nav2_behaviors REQUIRED)
find_package(nav2_util REQUIRED)
find_package(nav2_msgs REQUIRED)
find_package(pluginlib REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_ros REQUIRED)

# ============================================================
# CAMADA 1 — Nó de footprint dinâmico
# ============================================================
add_executable(dynamic_footprint_node
  src/dynamic_footprint_node.cpp
)
ament_target_dependencies(dynamic_footprint_node
  rclcpp
  rclcpp_lifecycle
  geometry_msgs
  sensor_msgs
  tf2
  tf2_ros
  nav2_util
)

# ============================================================
# CAMADA 2 — Plugin de recovery behavior Ackermann
# ============================================================
add_library(ackermann_recovery_plugin SHARED
  src/ackermann_recovery.cpp
)
ament_target_dependencies(ackermann_recovery_plugin
  rclcpp
  rclcpp_lifecycle
  geometry_msgs
  sensor_msgs
  nav2_core
  nav2_behaviors
  nav2_util
  nav2_msgs
  pluginlib
  tf2
  tf2_ros
)
# Necessário pro pluginlib encontrar o plugin em runtime
pluginlib_export_plugin_description_file(nav2_core plugins/camaro_recovery_plugin.xml)

# ============================================================
# Includes
# ============================================================
target_include_directories(dynamic_footprint_node PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)
target_include_directories(ackermann_recovery_plugin PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)

# ============================================================
# Scripts Python existentes (não alterados)
# ============================================================
install(PROGRAMS
  ${CMAKE_CURRENT_SOURCE_DIR}/scripts/tf_remapper.py
  ${CMAKE_CURRENT_SOURCE_DIR}/scripts/camaro_teleop.py
  DESTINATION lib/${PROJECT_NAME}
)

# ============================================================
# Install — binários C++ novos
# ============================================================
install(TARGETS
  dynamic_footprint_node
  ackermann_recovery_plugin
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY include/
  DESTINATION include
)

# ============================================================
# Recursos existentes (não alterados)
# ============================================================
install(
  DIRECTORY urdf meshes launch config worlds models maps behavior_trees plugins
  DESTINATION share/${PROJECT_NAME}
)

ament_package()