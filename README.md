# 3D Puppet — Pose y cámara desde una foto (addon de Blender)

Addon de **Blender 4.2+ / 5.0** con un **maniquí 3D con rig completo**: muñecas y 15 huesos de dedos por mano, para abrir y cerrar la mano. A partir de **una sola foto** copia:

- la **pose** del cuerpo y de las manos;
- la **cámara**: ángulo, distancia, focal y la foto como fondo.

La investigación completa (puppets con rig, modelos de pose, cámara, licencias) está en **[docs/RESEARCH.md](docs/RESEARCH.md)**.

## Qué incluye

- **Puppet procedural** con esqueleto SMPL-X (55 joints) y aspecto de maniquí de madera. Es 100 % código: no depende de assets de terceros.
- **Controles de mano**: sliders para cerrar, pulgar y abrir (spread) por mano. Presets *Open, Relaxed, Fist, Point, Peace, Thumbs up, Grip, Pinch*.
- **Pose From Photo** con dos backends:
  - **Lite**: MediaPipe dentro de Blender. Corre en CPU y se instala con un botón.
  - **Pro**: servidor local en GPU con SAM 3D Body (Meta), NLF y MediaPipe, más MoGe-2 para la focal.
- **Cámara**: se crea una cámara con la focal y la posición que reproducen la foto, y la foto queda de fondo. El modo **AUTO** mantiene el horizonte nivelado.

## Instalación

1. Empaqueta el addon. En Windows también puedes comprimir la carpeta `puppet_pose/` a mano.
   ```bash
   blender --command extension build --source-dir puppet_pose --output-dir dist
   ```
2. En Blender ve a *Edit → Preferences → Get Extensions → ⌄ → Install from Disk…* y elige `dist/puppet_pose-0.1.0.zip`.
3. Abre el panel en *Vista 3D → barra lateral (N) → pestaña **Puppet***.

### Backend Lite (MediaPipe)
En el panel, elige **Lite** y pulsa **Install Lite Dependencies**. Instala MediaPipe en la carpeta de usuario del addon y descarga los modelos (unos 30 MB). Necesita internet una sola vez.

### Backend Pro (servidor local en GPU)
```bat
cd server
install_server.bat         :: venv + PyTorch CUDA 12.8 + MediaPipe + MoGe-2
install_sam3d.bat          :: opcional: SAM 3D Body (pide acceso en HF + "hf auth login")
run_server.bat             :: http://127.0.0.1:8765
```
En Blender elige **Pro**, pulsa *Check Server* y luego *Pose From Photo*. El servidor también funciona por línea de comandos:
```bat
run_server.bat --once foto.jpg --method nlf --out resultado.json
```
Después ese JSON se aplica con **Load Result JSON**.

## Funciona solo, sin Claude

Todo corre **en local**: el addon dentro de Blender y el servidor en tu GPU. No usa Claude ni ningún servicio en la nube; internet solo hace falta la primera vez, para descargar los modelos.

- **Desde Blender:** panel *Puppet* → *Pose From Photo*.
- **Por lotes:** procesa una carpeta entera de fotos:
  ```bat
  samples\run_samples.bat                      :: usa samples\photos con el mejor método disponible
  samples\run_samples.bat D:\mis_fotos nlf      :: otra carpeta, método fijo (auto | nlf | mediapipe | sam3d_body)
  ```
  Por cada foto crea en `samples/results/`:
  - `<foto>_<método>.json`: la pose y la cámara.
  - `<foto>_<método>.blend`: el puppet posado, con la cámara que copia ángulo, distancia y focal y la foto de fondo.
  - `<foto>_<método>_overlay.png`: el puppet superpuesto a la foto, para revisar.

## Copiar la cámara de la foto

La cámara se reconstruye en tres pasos:

1. **Focal:** se toma de tu valor manual, si no del EXIF, si no de la estimación de MoGe-2.
2. **Ángulo:** sale de la gravedad que estima GeoCalib (pitch y roll reales); si no está disponible, de la postura del cuerpo con el horizonte nivelado.
3. **Distancia y encuadre:** se ajustan con *Fit Camera to Photo*, que mueve la cámara hasta que las articulaciones visibles del puppet coinciden con las de la foto. Funciona aunque la foto esté recortada (medio cuerpo).

## Uso

1. **Add Puppet**, o deja que *Pose From Photo* lo cree solo.
2. Elige la foto, el backend y, si quieres, fuerza la focal (35 mm equivalente; 0 = automática).
3. **Pose From Photo**. Se posan el cuerpo y los dedos, se crea la cámara `Puppet_Cam` como cámara activa y la foto queda de fondo. Mira por la cámara con `Numpad 0`.
4. Ajusta a mano en Pose Mode, con los sliders de manos o con **Re-apply Last Result** cambiando opciones (orientación, solo cuerpo o solo manos, keyframes).

## Estructura

```
puppet_pose/            addon / extensión (GPL-3.0-or-later)
  skeleton.py           esqueleto SMPL-X, rest pose y landmarks
  puppet_builder.py     armature + maniquí segmentado
  hand_controls.py      curl / spread / presets
  retarget.py           puntos 3D con nombre -> rotaciones de hueso (swing + twist)
  camera_utils.py       OpenCV <-> Blender, focal, cámara + fondo
  pose_apply.py         aplica un resultado (pose + cámara + suelo)
  backends/             mediapipe_lite (en Blender), server_client (HTTP)
server/                 servidor Pro (venv propio, PyTorch)
  pose_server.py        /health, /estimate, --once
  methods/              sam3d_method, nlf_method, mediapipe_method, focal (MoGe-2), detect
tests/                  tests que corren en Blender en modo background
docs/RESEARCH.md        investigación completa
```

## Tests
```bash
blender -b --factory-startup --python tests/test_roundtrip.py
blender -b --factory-startup --python tests/test_lite_render.py -- <carpeta-site-packages-con-mediapipe>
```

## Licencias
El código del addon es GPL-3.0-or-later. Los modelos tienen sus propias licencias; **varios son solo para investigación o uso no comercial**:

| Modelo | Licencia |
|---|---|
| MediaPipe | Apache-2.0 |
| SAM 3D Body | SAM License, pesos con acceso controlado |
| NLF | pesos no comerciales |
| SMPL-X | no comercial |
| MoGe-2 | MIT |

El detalle está en [docs/RESEARCH.md](docs/RESEARCH.md).
