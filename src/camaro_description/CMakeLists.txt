cmake_minimum_required(VERSION 3.8)
project(smart_camaro)

find_package(ament_cmake REQUIRED)
find_package(rclpy REQUIRED)
find_package(tf2_msgs REQUIRED)

# Instala o nó Python tf_remapper (caminho absoluto)
install(PROGRAMS
  ${CMAKE_CURRENT_SOURCE_DIR}/scripts/tf_remapper.py
  DESTINATION lib/${PROJECT_NAME}
)

# Instala diretórios de recursos
install(
  DIRECTORY urdf meshes launch config worlds models maps
  DESTINATION share/${PROJECT_NAME}
)

ament_package()