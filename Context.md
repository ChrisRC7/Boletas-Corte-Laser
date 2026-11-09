# Context.md

Contexto del proyecto para retomar el trabajo entre sesiones. Las reglas de
trabajo están en [CLAUDE.md](CLAUDE.md).

_Última revisión: 2026-11-09._

---

## Qué es y para quién

- **Usuario final:** operadores del LAIMI que reciben solicitudes de impresión
  3D / corte láser de estudiantes y las siguen hasta la entrega.
- **Responsable / quien pide cambios:** Aguirre ("el jefe"). Sus peticiones
  están en [Cambios que quiere Aguirre.md](Cambios%20que%20quiere%20Aguirre.md).
- **Referencia visual:** `Foto de Referencia.jpg` es la boleta en papel; el
  formulario digital la imita (barras de color por fase, casillas).
- Se usa en computadoras Windows del laboratorio, distribuido como `.exe`
  (PyInstaller).

## Flujo de una boleta

| # | Fase | Campos clave |
|---|------|--------------|
| 1 | Recepción | operador, fecha/hora, nombre del usuario, cuenta, carrera, carné, teléfono, uso (+detalle), pieza, **color del filamento**, observaciones, copias, material, resolución, relleno |
| 2 | Revisión y Preparación | gramos de material, tiempo de impresión, **precio** (= g × `PRECIO_POR_GRAMO`, 50 ₡), **tipo de impresora** (MK4S / Core One Plus / Cualquiera) |
| 3 | Impresión | confirmación del usuario (botón ✉ solicitar autorización), impresora (solo del tipo pedido), envío de correo (botón ✉ inicio), **lista de fallos** con fecha/hora/operador (solo se agregan, no se eliminan; JSON en `Fallo_Lista`), **notas de impresión** |
| 4 | Despegado de Piezas | observaciones, ¿imprimió bien?, correo (botón ✉ finalización) |
| 5 | Entrega de Piezas | verificación de cobro, recibido conforme |
| 6 | Cancelación | motivo de cancelación |

- **La fase «Reimpresión» se eliminó.** Al cargar un Excel con el formato de 7
  fases, el repositorio lo migra (`config.COLUMNAS_RENOMBRADAS` y
  `FASES_RENOMBRADAS`): la Cancelación pasa de `F7_*` a `F6_*`, las boletas en
  «6. Reimpresión» pasan a «5. Entrega de Piezas» y los datos de la antigua
  Reimpresión se conservan en columnas `Reimpresion_Antigua_*` al final del
  Excel (se descartan si estaban vacías).

- La fase actual se guarda en `Fase Actual`; `PhaseDetector` puede deducirla
  como la fase más avanzada con operador.
- En Revisión e Impresión el listado se ordena por prioridad de uso
  (Curso/Evento → Asistencia → Personal) y luego por fecha de recepción.
- Validación de campos obligatorios al avanzar de fase y al guardar
  (`catalogo.campos_obligatorios`, basado en `config.REQUIRED_FIELDS`). La
  Recepción se valida siempre al guardar; las demás fases, si tienen operador.
- Fecha y hora: al salir del campo (y al validar) se normalizan con
  `fechas.py` («1/2/2026» → «01/02/2026», «2:30 p.m.» o «14:30» → «02:30 PM»);
  si no se pueden leer, la validación lo indica.
- Cantidad de copias solo acepta números; teléfono, dígitos y `+ - ( )`.
- **Bloqueo de fases:** una fase se abre si las anteriores están completas (o
  si ya se llegó a ella); un clic en su barra la hace fase actual. Cancelación
  (`FASES_SIN_ORDEN`) solo exige la Recepción. Al guardar, `Fase Actual` =
  máx(fase más avanzada alcanzada, fase detectada por operadores), así volver
  atrás no retrocede la boleta. Al abrir se respeta la `Fase Actual` guardada
  si las fases previas están completas.
- Tiempo de impresión (Revisión): dos campos (horas/minutos) que se guardan
  juntos en `Tiempo_Impresion_HHMM` como `H:MM` (`PhaseSection.duration_field`).
- Columnas nuevas: `Color_Filamento` (F1) y `Tipo_Impresora` (F2); el
  repositorio las añade a Excels viejos al cargar.

## Persistencia actual

- Un único Excel `control_impresiones.xlsx` en el directorio de trabajo.
- Se carga entero en memoria (DataFrame, todo como `str` salvo `ID Boleta`).
- Se guarda en el momento al crear, editar o borrar una boleta (no al cerrar).
  Si falla (p. ej. el Excel abierto en Office), el cambio se deshace también en
  memoria y la UI lo avisa. La escritura es atómica (temporal + `os.replace`).
- Las columnas que no están en `config.COLUMNAS` se conservan al final.
- El ID nuevo es `max(ID) + 1`.
- **Limitación:** no soporta varias PCs escribiendo a la vez (último que guarda
  pisa al otro) y falla si el Excel está abierto en Office.

## Estado del repositorio

- Rama de trabajo: `Chris-Development`; rama principal: `main` (PRs en GitHub,
  `ChrisRC7`).
- `build/`, `dist/`, `*.spec`, los `.xlsx` y `configuracion.json` están
  ignorados: el `.exe` se distribuye fuera del repositorio y los datos tienen
  información personal de los usuarios. (Antes de esto, `main.exe` y un Excel
  de ejemplo estaban versionados y siguen en el historial de git).
- Con pandas 3 las columnas leídas con `dtype=str` solo aceptan texto: el
  repositorio convierte todo a texto al guardar (`_como_texto`).
- No hay tests automáticos.

## Peticiones pendientes (de "Cambios que quiere Aguirre.md")

1. Base de datos en una **Jetson Nano** en red local (falta router).
2. Que **dos PCs** puedan escribir sin conflictos de sincronización.
3. Apartado para **notas tipo post-it**.
4. ~~Autollenar datos a partir del carné~~ ✅ Hecho (ver "Active Directory").
5. Lista de **cursos por carrera** con desplegable y buscador.
6. Migrar a **SQLite** y añadir **export de resumen con métricas** (pendiente
   preguntar a Aguirre qué métricas quiere).
7. ~~Quitar la opción de eliminar fallos~~ ✅ Hecho.
8. ~~Renombrar Fase 7 "Cancelada" → "Cancelación"~~ ✅ Hecho (el repositorio
   migra los valores viejos al cargar, vía `config.FASES_RENOMBRADAS`).
9. ~~Editor de valores configurables~~ ✅ Hecho: ventana ⚙ Configuración
   dentro de la app, guarda en `configuracion.json` (`ajustes.py`). Al cargar se
   revisa la estructura y la coherencia; si no es válido se usan los valores
   por defecto y se avisa.

Otras funciones (2026-11-09): **orden de impresión del día** (`planificador.py`,
un rollo abierto por material+color salvo demanda > `GRAMOS_POR_ROLLO`),
colores por material, tipo de impresora, bloqueo de fases, autocompletado
desde el campo Nombre y reemplazo de datos al cambiar de persona.

## Active Directory (implementado)

- Módulo `src/boletas/directorio_ad.py` (`DirectorioAD`), solo lectura. Usa
  `DirectorySearcher` de Windows vía PowerShell con las credenciales de la
  sesión: no hay contraseñas ni librerías extra. Dominio `ESTUDIANTES.TEC.CR`.
- Atributos: `sAMAccountName` = cuenta (usuario del correo; los correos siempre
  son `@estudiantec.cr`), `employeeID` = carné, `name` = nombre completo,
  `mail` = correo, `description` = "SEDE - CARRERA".
- **Operador** (todas las fases): si se escribe una cuenta (con o sin
  `@estudiantec.cr`) o un carné, se sustituye por el nombre completo. Un texto
  con espacios (un nombre) se deja tal cual; una sola palabra que no exista en
  el AD también.
- **Cuenta / Carné** (Fase 1): llenan nombre del usuario (`Nombre_Usuario`),
  cuenta, carrera, carné y teléfono. Primero se buscan boletas anteriores del usuario
  (`BoletaRepository.buscar_datos_usuario`); si no hay, se consulta el AD. Solo
  se busca si el valor cambió; los datos encontrados **reemplazan** a los
  anteriores y se borran los autocompletados que el usuario nuevo no tenga
  (lo escrito a mano se conserva). En **Nombre del usuario** también se acepta
  correo o carné. Los estudiantes no suelen tener teléfono en el AD.
- Las consultas al AD corren en segundo plano (`BoletaForm.en_segundo_plano`).
  Si la PC no está en el dominio, simplemente no se autocompleta nada.

## Correos por Outlook (implementado)

- Plantillas en `src/boletas/correos.py` (sin UI), copiadas de los correos que
  el LAIMI enviaba a mano: autorización (costo), inicio y finalización. El
  asunto lleva `<Nombre_Pieza> (BOLETA <ID>)`; el destinatario es
  `Cuenta + AD_DOMINIO_CORREO`.
- `src/boletas/outlook.py` crea el correo con COM (`Outlook.Application`) vía
  PowerShell y lo **muestra** (`Display`), nunca lo envía: el operador revisa
  y pulsa Enviar. Solo funciona con Outlook clásico (el "Outlook nuevo" no
  tiene COM). La primera vez Outlook puede tardar en abrir (timeout 120 s).
- Botones en `ui/enviar_correo.py`: al abrir el borrador marcan la casilla
  correspondiente (autorización → `Confirmacion_Usuario` = «Correo
  Institucional»; inicio → `F3_Envio_Correo`; finalización → `F4_Envio_Correo`).
- Los emojis de los textos son aproximados a los de la plantilla original.

## PrusaSlicer (implementado)

- Módulo `src/boletas/prusaslicer.py` (sin UI) y botón en
  `ui/importar_slicer.py`. Recepción: material (`filament_type`), resolución
  (`layer_height`) y relleno (`fill_density`). Revisión: eso + gramos y tiempo.
- La conversión a opciones de la boleta está en `catalogo.material_desde_slicer`
  (FLEX → «Flex (TPU)» por coincidir con una palabra; desconocido → «Otro» con
  el tipo en el detalle) y `catalogo.opcion_cercana` (capa 0.3 → 0.28).
- Tras llenar valores se llama `PhaseSection.on_valores_externos(claves)` en
  cada fase; la Recepción lo usa para refrescar colores y el campo «Otro».
- G-code de texto: busca `; estimated printing time (normal mode) = …` y
  `; total filament used [g] = …` al final del archivo. `.bgcode` (MK4/Core
  One): lee los bloques de metadatos `clave=valor` (sin comprimir o deflate).
- `.3mf`: se slicea con la configuración del propio proyecto. `.stl`/`.obj`:
  necesita `PRUSASLICER_PERFIL` (un `.ini` exportado). Se ejecuta
  `prusa-slicer-console.exe --export-gcode` en una carpeta temporal.
- Si el perfil tiene densidad 0, PrusaSlicer da 0 g: se usa
  `cm³ × filament_density` (o `config.DENSIDAD_FILAMENTO`) y se avisa.
- El tiempo se redondea hacia arriba al minuto.
- Probado con PrusaSlicer 2.9.6.

## Notas de diseño para lo que viene

- **SQLite / Jetson:** reemplazar solo `repository.py` manteniendo la misma
  interfaz pública (`load`, `save`, `all`, `search`, `filter_by_phase`,
  `get_next_id`, `get_by_id`, `add`, `update`, `delete`). Así la UI no cambia.
- **Opciones editables:** `config.py` tiene los valores por defecto;
  `ajustes.cargar()` (al arrancar `App`) aplica `configuracion.json` encima.
  Nada debe capturar valores de `config` al importar (p. ej. como valor por
  defecto de un parámetro): leerlos en tiempo de ejecución.
