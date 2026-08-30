# 🎨 meshes/ — Modelos 3D do Robô

Esta pasta contém os arquivos de malha 3D (mesh) do Camaro usados para visualização no Gazebo e no RViz2.

---

## 📄 Arquivos

| Arquivo | Formato | Usado para |
|---|---|---|
| `camaronovo.glb` | GLB (3D com textura) | ⭐ Modelo principal do robô no Gazebo |
| `rodanova.glb` | GLB (3D com textura) | Modelo 3D das rodas com textura |
| `camaro_model_final.stl` | STL (3D sem textura) | Versão alternativa do corpo |
| `chassi_camaro.stl` | STL (3D sem textura) | Só o chassi (sem rodas) |
| `roda_camaro.stl` | STL (3D sem textura) | Modelo simples de roda |

---

## 🔗 Como são usados

O arquivo `camaronovo.glb` é referenciado no `urdf/camaro.xacro`:

```xml
<mesh filename="package://camaro_description/meshes/camaronovo.glb"
      scale="0.0012 0.0012 0.0012"/>
```

O `scale` é necessário porque o modelo foi criado em milímetros — o fator `0.0012` converte para metros na escala correta do robô.

---

## ⚠️ Importante

Se o Gazebo não encontrar as meshes (robô invisível ou erro de carregamento), verifique se o `source install/setup.bash` foi executado. O ROS 2 precisa saber o caminho do pacote para resolver `package://camaro_description/meshes/`.

---

## 🛠️ Como substituir o modelo

1. Exporte o novo modelo em formato `.glb` ou `.stl` do seu software 3D
2. Coloque o arquivo nesta pasta
3. Edite `urdf/camaro.xacro` para apontar para o novo arquivo
4. Ajuste o `scale` conforme necessário
5. Recompile: `colcon build --symlink-install`
