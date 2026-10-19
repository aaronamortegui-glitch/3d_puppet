# Investigación: puppet 3D con rig + pose y cámara desde una foto (Blender)

*Fecha: octubre 2026 · Blender objetivo: 5.0 (Python 3.11) · GPU de referencia: RTX 5090 Laptop 24 GB*

Objetivo: tener un muñeco 3D (puppet) con rig completo, con muñecas y dedos (abrir y cerrar la mano), totalmente controlable. Desde **una sola foto** debe poder copiar:

- la **pose** del cuerpo y de las manos;
- la **cámara**: ángulo, distancia y focal.

Todo empaquetado como **addon instalable de Blender**.

Decisión de licencias del proyecto: el **uso es interno o de investigación**, así que se permiten modelos no comerciales (SMPL-X, etc.). Igual se marca la licencia de cada pieza.

---

## 1. Resumen de decisiones

| Pieza | Elección | Por qué |
|---|---|---|
| Puppet por defecto | **Maniquí procedural propio** generado en Python, con esqueleto **SMPL-X (55 joints, 15 huesos de dedos por mano)** | Sin riesgo de licencia (todo es código GPL nuestro). Los nombres de hueso coinciden 1:1 con lo que entregan los estimadores. Aspecto de maniquí de artista. |
| Controles de mano | Sliders de cerrar, pulgar y abrir (spread) por mano, más presets (open, fist, point, peace, thumbs up, grip, pinch) | Los huesos de dedo tienen el eje local X como eje de flexión, así que una rotación positiva cierra el dedo. |
| Backend **Lite** | **MediaPipe Tasks 1.1.1** (Pose Landmarker heavy + Hand Landmarker) dentro del Python de Blender | Apache-2.0, CPU, unos 1–2 s por foto, se instala con un botón. |
| Backend **Pro** | Servidor local (venv aparte, PyTorch cu128) con **SAM 3D Body** (Meta) → NLF → MediaPipe | SAM 3D Body es el estado del arte en cuerpo, manos y pies desde una foto y estima la focal. NLF es la alternativa fácil de instalar. |
| Focal / FOV | Usuario > EXIF > **MoGe-2** (Microsoft, MIT) > 35 mm por defecto | La mayoría de los modelos asumen una focal fija; sin focal correcta la distancia de cámara sale mal. |
| Retarget | **Por posiciones con referencia de twist** (swing + twist con marcos ortonormales) | Sirve para cualquier backend (MediaPipe, SMPL-X, MHR), porque todos entregan puntos 3D con nombre. Opcionalmente se pueden usar rotaciones SMPL-X directas. |
| Cámara | Mínimos cuadrados lineales de perspectiva para la traslación, conversión OpenCV → Blender y modo **AUTO sin roll** | Probado en un test de ida y vuelta: error de 3,6 px y focal exacta. |

---

## 2. Puppets 3D con rig (con dedos)

| Opción | Licencia | Dedos | Controles | Notas |
|---|---|---|---|---|
| **Maniquí procedural (este repo)** | GPL-3 (código propio) | 15 por mano (3 por dedo) | FK y sliders/presets de mano | Elegido por defecto. Esqueleto = SMPL-X. |
| SMPL-X Blender add-on (MPI / Meshcapade) | Modelo **no comercial**; Meshcapade fue adquirida por Epic (feb 2026) | 15 por mano (MANO) | FK, presets flat/relaxed | Máxima fidelidad con estimadores SMPL-X. No redistribuible: cada usuario trae su propio modelo. |
| MPFB2 (MakeHuman) | Código GPL; assets **CC0** | `game_engine`: 15 por mano; `default`: 15 + metacarpianos | Helpers IK; opción Rigify | La mejor base CC0 si se quiere un cuerpo realista. Naming tipo UE (`index_01_l`). |
| Rigify (incluido en Blender) | GPL | 15 + palm | IK/FK completo, *finger masters* (curl) | Ideal para animadores. Hay que escribir sobre los huesos FK/ORG y compensar la rest pose (A-pose). |
| Blender Studio Human Base Meshes | CC0 | sin rig | — | Malla para skinnear sobre Rigify o MPFB. |
| Blender Studio Rain / Storm | CC-BY | sí | CloudRig IK/FK | Rigs de animación pulidos, con naming propio. |
| Mixamo | Uso comercial OK, pero **prohibido redistribuir** los archivos | 15 por mano (`LeftHandIndex1-3`) | FK | Útil como perfil de retarget para personajes del usuario. |
| Auto-Rig Pro | Pago (~$50) | sí, con IK de dedos | IK/FK, fist | Solo del lado del usuario. |
| Quaternius Universal Base Characters | CC0 | 15 por mano (reportado) | FK | Low-poly, naming UE. |
| **MHR — Meta Momentum Human Rig** | **Apache-2.0** | sí | — | Rig nativo de SAM 3D Body; FBX con LODs y conversor SMPL ↔ MHR. |
| **Anny (NAVER)** | Apache-2.0 / CC0 | sí (104 huesos) | — | Modelo paramétrico de cuerpo (edades y formas), alternativa abierta a SMPL-X. |
| Ready Player Me | **Cerrado** (Netflix, ene 2026) | — | — | Descartado. |
| Kenney | CC0 | no tiene dedos | — | Descartado. |

**Conclusión:** el puppet que viene con el addon es el maniquí procedural. Usa los nombres de SMPL-X, así que los resultados de cualquier estimador se aplican sin tablas de mapeo. Para personajes propios (Mixamo, Rigify, MPFB, UE), el siguiente paso es agregar **perfiles de mapeo de huesos**. El retarget por posiciones ya funciona con cualquier esqueleto si se le da la tabla de nombres.

---

## 3. Estimación de pose 3D desde una foto (cuerpo + dedos + cámara)

| Método | Licencia (código / pesos) | Manos | Cámara | Instalación en Windows + 5090 |
|---|---|---|---|---|
| **SAM 3D Body** (Meta, 2025-26) | SAM License (permite uso comercial con restricciones); pesos con acceso controlado en HF | **Sí**, 21 keypoints por mano (MHR70) | Perspectiva completa; FOV con MoGe-2; acepta `cam_int` | Media. Evitamos detectron2 pasando nosotros las cajas de persona (Faster R-CNN de torchvision). |
| Fast SAM 3D Body (ECCV 26) | MIT, usa los pesos de SAM 3D Body | sí | igual | ~65 ms en 5090; scripts bash (WSL). |
| **NLF** (Neural Localizer Fields) | MIT / pesos **no comerciales** | sí (SMPL-X, manos algo débiles) | Perspectiva; acepta intrínsecos | **Fácil**: un solo archivo TorchScript. |
| Multi-HMR / Multi-HMR 2 (NAVER) | CC BY-NC-SA / NC | sí (calidad moderada) | Intrínsecos opcionales | Fácil a media. |
| SMPLer-X / SMPLest-X | S-Lab NC | sí (gruesas) | Focal fija | Difícil (torch 1.12 + mmcv), no compatible con la 5090 sin recompilar. |
| AiOS, OSX, Hand4Whole, PIXIE | NC | sí | Focal fija o débil | Legacy, difícil. |
| 4D-Humans (HMR2), TokenHMR, CameraHMR | NC (SMPL) | **no** | CameraHMR estima FOV (HumanFoV) | — |
| WiLoR / HaMeR | NC (MANO) | Solo manos (lo mejor en dedos) | Weak perspective | Útil para refinar dedos sobre recortes de mano. |
| **MediaPipe** Pose + Hands / Holistic | Apache-2.0 | 21 por mano | Ninguna (la resolvemos nosotros) | Trivial. Corre en el Python de Blender. |
| RTMW / DWPose (rtmlib, ONNX) | Apache | 133 keypoints 2D | — | Fácil, pero solo 2D. |

**Estimación de cámara:**
- **MoGe-2**: MIT, da FOV y profundidad métrica.
- **GeoCalib**: Apache / CC-BY, da focal y **dirección de la gravedad**, o sea pitch y roll reales.
- **Depth Pro**: Apple, licencia por confirmar.
- **Depth Anything 3**: Apache en los modelos chicos.
- **VGGT**: tiene una variante comercial.

**Pipeline elegido:**

- **Lite (en Blender):**
  1. MediaPipe extrae los landmarks 3D métricos del cuerpo y las manos; las manos se asignan a la muñeca más cercana.
  2. La focal sale del EXIF, o de un valor manual, o de 35 mm por defecto.
  3. La traslación de cámara se resuelve por mínimos cuadrados con los landmarks 2D.
  4. Retarget al puppet.
- **Pro (servidor local en la GPU):**
  1. Focal: valor del usuario, si no EXIF, si no MoGe-2.
  2. Pose: **SAM 3D Body** (cuerpo, manos, pies, focal). Si no está instalado, **NLF** (SMPL-X); si tampoco, MediaPipe.
  3. El servidor normaliza la salida a puntos 3D con nombre en espacio de cámara OpenCV. La convención de ejes y unidades se detecta sola por reproyección.

---

## 4. Integración en Blender

### Formato del addon
- **Extensión de Blender (4.2+)**: `blender_manifest.toml` con permisos `files` y `network`, más un `bl_info` para instalarlo como addon legacy.
- **Dependencias del modo lite**: se instalan con pip en el directorio de usuario de la extensión (`extension_path_user`), **nunca** en Program Files.
  - numpy queda fijado a la versión de Blender (1.26.4 en 5.0).
  - Probado: `mediapipe 1.1.1` importa bien en el Python 3.11 de Blender 5.0.1.
- **Ojo:** Blender 5.1+ usa **Python 3.13**. Las dependencias compiladas se reinstalan con el botón; el servidor pro no se ve afectado porque corre en su propio proceso.
- **PyTorch nunca va dentro de Blender** (conflictos de DLL, ~3 GB). Va en el servidor (`server/.venv`) y Blender le habla por HTTP local (`127.0.0.1:8765`) usando solo la stdlib.

### Retarget (`puppet_pose/retarget.py`)
1. Cada hueso tiene una spec con un vector primario (p. ej. hombro → codo) y un vector secundario opcional para el twist:
   - brazo superior: plano del codo;
   - antebrazo y mano: línea índice-meñique;
   - pelvis: línea de caderas;
   - cabeza: orejas y nariz.
2. Los mismos nombres se evalúan en la rest pose del puppet y en el resultado del modelo. Así **no hace falta que coincidan los ejes de hueso** entre rigs.
3. Con dos vectores se construye un marco ortonormal: `G = F(target) · F(rest)ᵀ`. Con uno solo se aplica el swing mínimo sobre la rotación del padre.
4. Si el vector secundario es degenerado (brazo o pierna recta), se cae al swing.
5. De global a local: `basis = R_restᵀ · G_parentᵀ · G · R_rest`.
6. `spine2` se interpola (slerp) entre `spine1` y `spine3` para repartir la torsión.
7. Hay una ruta alternativa con **rotaciones SMPL-X directas** (axis-angle): `G_j = G_parent · C·R_j·C⁻¹`.

### Cámara (`puppet_pose/camera_utils.py`, `pose_apply.py`)
- **Focal:** `lens_mm = f_px · sensor_width / max(W, H)` con `sensor_fit = AUTO` y sensor de 36 mm. Desde EXIF 35 mm equivalente: `f_px = f35 / 43.27 · diag_px`.
- **Punto principal:** `shift_x = (W/2 − cx)/max(W,H)`, `shift_y = (cy − H/2)/max(W,H)`.
- **Traslación:** `f(X+tx) − (u−cx)(Z+tz) = 0` y lo mismo en y. Es lineal en `t`, así que se resuelve por mínimos cuadrados ponderados por visibilidad.
- **Frames:**
  - OpenCV: x a la derecha, y hacia abajo, z hacia adelante.
  - W_c (marco interno): `(x, z, −y)`, con la cámara en el origen mirando a +Y.
  - Cámara de Blender: `Euler(90°, 0, 0)` en W_c.
- **Modos de orientación:**
  - **AUTO** (por defecto): la cámara mantiene el **horizonte nivelado** (roll 0). El pitch sale del vector "arriba" del cuerpo (torso, más piernas si están rectas) y el yaw lo normaliza para que el puppet mire a −Y. Lo inclinado de la toma queda en la cámara, que es lo que pasa en la vida real.
  - **UPRIGHT**: el torso queda vertical y toda la inclinación pasa a la cámara (pitch y roll).
  - **LEVEL**: la cámara sin pitch ni roll; la inclinación queda en el puppet.
  - **NONE**: la cámara en el origen.
- **Escala:** el puppet tiene proporciones fijas. Se escala la posición del sujeto por la razón de longitudes (torso + piernas + brazos), así se mantiene el encuadre.
- **Suelo:** se baja el puppet hasta que su punto más bajo toque z = 0, y la cámara se mueve con él.
- **Foto de fondo:** la foto se pone como imagen de fondo de la cámara (alpha 0,6), con la resolución de render igual a la de la foto. Si la foto trae rotación EXIF, se guarda una copia enderezada porque Blender ignora el EXIF.

### Addons y proyectos de referencia estudiados
- **PoseCap (Corridor, GPL-3)** es la referencia más parecida: extensión de Blender más un proceso GPU separado, con modo MediaPipe lite.
- **BlendArMocap** (GPL-3, descontinuado): matemática de MediaPipe → Rigify.
- **FreeMoCap addon** (AGPL, solo para estudiar).
- **SMPL-X add-on** (axis-angle → quaternion).
- **CEB 4D Humans** (venv externo con `.bat`).
- **MoPA** (servidor por socket).
- **Rokoko / Expy Kit / Retarget (KBS)** (mapeo de huesos).

---

## 5. Validación realizada

| Test | Resultado |
|---|---|
| `tests/test_roundtrip.py`: pose y cámara conocidas → puntos sintéticos → retarget a un puppet nuevo | Dirección de hueso con **error medio de 0,25°** (los dedos en 0°). Reproyección de **3,6 px**. Focal reconstruida **exacta** (33,75 mm). Modos UPRIGHT y AUTO con el mismo encuadre; **roll de AUTO = 0,00°**. PASS. |
| `tests/test_lite_render.py`: render EEVEE del maniquí posado → MediaPipe → puppet nuevo | Cámara reconstruida: **3,58 m de distancia igual a la original**, elevación de 8,3° frente a 7,6° reales, misma focal. MediaPipe **no detecta manos de madera** (normal) y confunde la profundidad de la pierna levantada. Con fotos reales de personas el detector rinde mucho mejor. |
| Presets de mano | Puño, señalar, paz, etc. se ven correctos. El pulgar cruza la palma. |
| Gravedad (test de ida y vuelta, cámara con roll de 12°) | Con `up_cam` conocido, el pitch y el roll de la cámara se recuperan **exactos** (−9,96° / 11,82°). |
| Servidor Pro: NLF + MoGe-2 + GeoCalib sobre el render del maniquí | La cadena completa corre en la RTX 5090 y entrega 72 puntos con manos. **MoGe-2 estimó una focal de ~36 mm (real 33,8)**. Pero tanto NLF como MediaPipe **interpretan el maniquí de cara lisa como visto de espaldas**, y GeoCalib no es fiable en una escena sintética sin estructura. **Hace falta validar con fotos reales de personas.** |
| Extensión instalada desde el zip (perfil aislado) | Instalar → activar → *Install Lite Dependencies* → *Pose From Photo* → *Re-apply*: todo OK en Blender 5.0.1. |

Notas de implementación aprendidas:
- Blender no admite que un operador registrado herede de otro operador registrado. Se usa un mixin.
- El TorchScript de NLF necesita `import torchvision` antes de `torch.jit.load`, para registrar `nms`.
- NLF tiene `estimate_smpl_batched(images, boxes)`: si su detector YOLO falla, se le pasan cajas externas.
- `glob('**')` no entra en carpetas que empiezan con punto, como `extensions/.user/`.
- La ambigüedad **frente/espalda** es el error más común con una sola foto. Se corrige con el botón *Flip Front/Back*, que intercambia izquierda y derecha y refleja la profundidad manteniendo la proyección 2D.

---

## 6. Limitaciones conocidas y siguientes pasos

1. **Ambigüedad de profundidad** en una sola foto: un miembro puede quedar "al revés" en profundidad. Se mitiga con el backend pro (SAM 3D Body).
2. **Manos pequeñas** en fotos de cuerpo entero: el siguiente paso es un segundo pase sobre un recorte de la mano a mayor resolución (WiLoR o el decoder de manos de SAM 3D Body).
3. ~~Gravedad real~~ **Hecho**: GeoCalib ya está integrado en el servidor (`up_cam`), y el modo AUTO lo usa para el pitch y el roll exactos. Falta validarlo con fotos reales.
4. **Perfiles de mapeo** para Mixamo, Rigify, MPFB y UE, para aplicar la pose a personajes propios.
5. **Refinamiento PnP** tras el retarget: ajustar la cámara al puppet ya posado, porque sus proporciones difieren de las del sujeto.
6. **Modo multi-persona** y video (pose por frame con suavizado).
