# SMART CAMARO

Projeto em desenvolvimento que busca migrar e evoluir o robô Camaro do ROS1 para o ROS2 Jazzy, implementando navegação autônoma em um veículo com direção Ackermann voltado para delivery, utilizando Gazebo Harmonic como ambiente de simulação

1. O projeto inclui a simulação completa do robô com SLAM e navegação autônoma via Nav2
2. Abra "Simulação.md" para ler o tutorial de como utilizar a simulação
3. O robô físico é equipado com uma câmera ZED 2 e um LiDAR — a integração dos sensores reais está planejada para etapas futuras
4. Por utilizar direção Ackermann, o projeto possui desafios e soluções de navegação distintos dos robôs diferenciais

## Especificações Técnicas Principais

- **Direção**: Ackermann (distância entre eixos 0.71m, bitola 0.46m)
- **Chassi**: collision box 0.6 x 0.46 x 0.15m — malha real 1.2 x 0.66 x 0.36m
- **Rodas**: `rodanova.glb` (diâmetro 0.22m, largura 0.072m)
- **LiDAR**: `lidarA2` em (0.55, 0, 0.06)m sobre o `base_link` (colado na parte de baixo do chassi, na altura das rodas)
- **Raio mínimo de curvatura**: 1.04m
- **Configurações completas**: `SIMULAÇÃO.MD` (seção "Especificações Técnicas")

## Regras de Projeto 🚀📋

Para a plena organização e desenvolvimento do projeto, todos os commits de novas contribuições devem ser feitos fora do branch principal:

- Crie uma nova branch com o nome do seu enfoque no projeto
- Ou faça commit no branch chamado "Desenvolvimento"
