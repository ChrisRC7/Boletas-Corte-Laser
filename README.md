# Control de Impresiones — Boletas de Corte Láser 🖨️ 

Aplicación de escritorio (CustomTkinter) para gestionar las **boletas de impresión 3D
/ corte láser** del LAIMI. Permite registrar cada solicitud y seguirla a lo
largo de sus **7 fases**, desde la recepción hasta la entrega (o cancelación).
Los datos se guardan en un archivo Excel (`control_impresiones.xlsx`).

El formulario de cada boleta imita la **boleta impresa**: todas las fases están
en una sola vista, una debajo de otra, cada una con su barra de color que se
**despliega u oculta** al hacer clic.

---

## 🎯 ¿Qué hace?

- Registra boletas con todos los datos del usuario y de la pieza.
- Acompaña cada boleta por sus fases, **validando los campos obligatorios** al
  avanzar de fase y al guardar.
- Calcula automáticamente el **precio** según los gramos de material.
- Permite **buscar** (por ID, carné, operador o cuenta) y **filtrar por fase**.
- En las fases de Revisión e Impresión ordena por **prioridad de impresión**
  (Curso y Evento → Asistencia → Personal; a igual prioridad, por fecha de recepción).
- Registra una lista de **fallos de impresión**. Una vez registrado, un fallo
  **no se puede eliminar** (queda en el historial de la boleta).
- Tiene un campo de **notas de impresión** en la Fase 3.
- **Autocompleta con el Active Directory** (solo lectura):
  - En **OPERADOR** se puede escribir el usuario del correo (con o sin
    `@estudiantec.cr`) o el carné: se sustituye por el nombre completo.
    Un nombre con espacios se deja tal cual.
  - Al escribir la **cuenta** o el **carné** en la Recepción se llenan nombre del
    usuario, cuenta, carrera, carné y teléfono: primero con los datos de boletas anteriores del
    mismo usuario y, si no tiene, con los del AD.
  - En **NOMBRE DEL USUARIO** también se puede escribir el correo o el carné: se
    pasan a su campo, se autocompleta todo y el nombre se sustituye por el real.
  - Si se cambia el carné o la cuenta por los de **otra persona**, sus datos
    reemplazan a los anteriores (no hace falta borrar los campos a mano).
- **Nombre del archivo** automático: `boleta-carné-n.º de impresión del usuario`
  (1 si es su primera boleta, 2 la segunda...).
- **⧉ Copiar**: crea una boleta nueva con toda la Recepción de la boleta
  seleccionada (para usuarios que traen varias impresiones), con el siguiente
  número de boleta, el siguiente número de impresión y la fecha/hora actual.
- **Color del filamento** en la Recepción: lista con los colores disponibles del
  material elegido (se pueden marcar como agotados en la Configuración).
- **Tipo de impresora** (MK4S, Core One Plus o Cualquiera) en la Revisión; la
  Impresión muestra dónde imprimir y solo deja elegir impresoras de ese tipo.
  Se puede desactivar desde la Configuración.
- **⚙ Configuración**: edita precio, materiales, colores, resoluciones,
  rellenos, usos/prioridades, impresoras y tipos **sin recompilar**. Se guarda
  en `configuracion.json` (junto al Excel); "Restaurar valores por defecto"
  vuelve a lo de `config.py`.
- **Correos por Outlook**: en la Impresión, «✉ Solicitar autorización» (costo
  de la pieza; marca la confirmación por «Correo Institucional») y «✉ Correo de
  inicio» (marca la casilla de notificación de inicio; si no hay fecha/hora de
  Impresión pone la de ahora); en el Despegado, «✉ Correo de finalización».
  Cada botón abre en Outlook clásico un **borrador** ya lleno (para
  `<cuenta>@estudiantec.cr`, con el asunto y texto de siempre); el operador lo
  revisa y pulsa Enviar. Los textos están en `src/boletas/correos.py`.
- **Desde PrusaSlicer…**: en la Recepción llena material, resolución y relleno;
  en la Revisión, eso más los gramos y el tiempo; en la Reimpresión, gramos y
  tiempo. La capa y el relleno se marcan en la opción más cercana y un
  filamento que no está en la lista va a «Otro»; si cambia algo ya lleno, lo
  avisa. Lee el G-code exportado (`.gcode` o `.bgcode`), o sliceando
  un proyecto `.3mf` (o un `.stl` si hay un perfil `.ini` en la Configuración)
  con `prusa-slicer-console.exe`. Si el perfil no tiene densidad de filamento
  los gramos se estiman con el volumen × densidad (`DENSIDAD_FILAMENTO`).
- **📋 Orden de impresión**: calcula e imprime el orden óptimo del día (ver abajo).

### Orden de impresión del día

Reparte los trabajos listos (Revisión completa o Reimpresión) entre las
impresoras activas:

- Orden por **prioridad de uso** y, a igual prioridad, el **más antiguo**.
- Cada trabajo va a una impresora del **tipo pedido** en la Revisión.
- Las impresoras **ocupadas** (boletas en Impresión) quedan libres al terminar
  (inicio + tiempo estimado) y conservan su filamento cargado.
- **Un rollo abierto por material y color**: los trabajos de un mismo filamento
  no se imprimen a la vez en dos impresoras, salvo que la demanda del día supere
  un rollo (`GRAMOS_POR_ROLLO`, 1 kg): entonces se permiten
  `ceil(gramos / 1000)` rollos a la vez.
- A igual hora de inicio se prefiere la impresora que ya tiene ese filamento.

En la ventana se pueden sacar impresoras del plan y recalcular. **Imprimir**
manda el reporte a la impresora predeterminada de Windows. Los trabajos sin
gramos/tiempo aparecen en "Sin programar".

### El formulario de una boleta

- Cada fase es una **barra de color** (los mismos colores de la boleta impresa)
  que se despliega u oculta al hacer clic. La barra muestra **✓** cuando la fase
  ya tiene operador y **● FASE ACTUAL** en la fase en curso.
- Las opciones (uso, material, resolución, relleno, impresora...) se marcan
  como en el papel, con casillas.
- **Una fase está bloqueada (🔒) mientras las anteriores no estén completas.**
  Al completarlas se desbloquea y se abre con un clic en su barra (igual que
  **Siguiente**). El selector de Fase Actual tampoco deja saltar fases
  incompletas; la **Cancelación** solo exige la Recepción completa.
- Volver a una fase anterior para corregir algo no retrocede la boleta: al
  guardar, queda en la fase más avanzada a la que se llegó.
- El **tiempo de impresión** se escribe en dos campos (horas y minutos) y se
  guarda como `H:MM`.
- La barra inferior tiene **Anterior / Siguiente** (valida los campos
  obligatorios antes de avanzar), el selector de **Fase Actual**,
  **Expandir todo / Contraer todo** y **Guardar Cambios**.
- Al abrir una boleta existente se despliega directamente su fase actual.

### Las 7 fases

1. Recepción
2. Revisión y Preparación
3. Impresión
4. Despegado de Piezas
5. Entrega de Piezas
6. Reimpresión
7. Cancelación

---

## 📁 Estructura del proyecto

El código está **modularizado por capas** para que sea fácil de mantener: cada
archivo tiene una única responsabilidad y las capas no se mezclan.

```
Boletas Corte Laser/
├── README.md                  # Este archivo
├── requirements.txt           # Dependencias de Python
└── src/
    ├── main.py                # Punto de entrada (arranca la app)
    ├── boletas/               # Paquete de la aplicación
    │   ├── __init__.py
    │   ├── config.py          # Constantes: fases, columnas, opciones, precio (valores por defecto)
    │   ├── ajustes.py         # Lee/guarda configuracion.json (opciones editables sin recompilar)
    │   ├── catalogo.py        # Consultas sobre las opciones (usos, colores, impresoras)
    │   ├── planificador.py    # Orden óptimo de impresión del día
    │   ├── repository.py      # Acceso a datos (Excel)        [patrón Repository]
    │   ├── services.py        # Lógica de negocio (precio, fase, autocompletado de usuarios)
    │   ├── directorio_ad.py   # Consultas al Active Directory (solo lectura)
    │   ├── prusaslicer.py     # Gramos y tiempo desde G-code/3MF de PrusaSlicer
    │   ├── correos.py         # Plantillas de los correos al usuario (autorización, inicio, finalización)
    │   ├── outlook.py         # Abre los correos como borrador en Outlook (COM vía PowerShell)
    │   └── ui/                # Interfaz gráfica (CustomTkinter)
    │       ├── __init__.py
    │       ├── theme.py       # Colores de cada fase y fuentes (imitan la boleta)
    │       ├── main_window.py # Ventana principal (listado, búsqueda, filtros)
    │       ├── boleta_form.py # Orquestador del formulario (arma secciones, navega, guarda)
    │       ├── config_window.py # Ventana de Configuración
    │       ├── plan_window.py # Ventana del orden de impresión
    │       ├── tabla_editable.py # Tabla de filas editable (usada en la Configuración)
    │       ├── importar_slicer.py # Botón «Desde PrusaSlicer…» (Recepción, Revisión, Reimpresión)
    │       ├── enviar_correo.py # Botones «✉ …» que abren los correos en Outlook (Impresión, Despegado)
    │       └── phases/        # Una fase por archivo (cada sección es independiente)
    │           ├── __init__.py            # Registro de fases (PHASE_CLASSES)
    │           ├── base.py                # PhaseSection: clase base de una fase
    │           ├── fase1_recepcion.py
    │           ├── fase2_revision.py
    │           ├── fase3_impresion.py
    │           ├── fase4_despegado.py
    │           ├── fase5_entrega.py
    │           ├── fase6_reimpresion.py
    │           └── fase7_cancelacion.py
    ├── main.spec              # Configuración de PyInstaller
    └── build/, dist/          # Artefactos generados al empaquetar
```

---

## 🧱 Arquitectura y patrones de diseño

El proyecto sigue una **separación en capas** clásica. La regla principal es que
las dependencias apuntan "hacia adentro": la interfaz usa los servicios y el
repositorio, pero la lógica de datos no sabe nada de la interfaz.

```
        ┌──────────────────────────────┐
        │        UI (CustomTkinter)     │  main_window.py · boleta_form.py
        │  ventanas, botones, widgets   │
        └───────────────┬──────────────┘
                        │ usa
        ┌───────────────┴──────────────┐
        │      Servicios + Config       │  services.py · config.py
        │  reglas de negocio y ajustes  │
        └───────────────┬──────────────┘
                        │ usa
        ┌───────────────┴──────────────┐
        │      Repository (datos)       │  repository.py
        │  lee/escribe el Excel         │
        └──────────────────────────────┘
```

| Capa / módulo        | Responsabilidad                                                                 | Patrón |
|----------------------|---------------------------------------------------------------------------------|--------|
| `config.py`          | Único lugar con las constantes del dominio (fases, columnas, opciones, precio). | Configuración centralizada |
| `repository.py`      | Toda la lectura/escritura del Excel y las consultas (CRUD, búsqueda, filtros).  | **Repository** |
| `services.py`        | Cálculos reutilizables sin interfaz: precio, detección de la fase actual y autocompletado de usuarios (historial → AD). | Servicios |
| `directorio_ad.py`   | Búsquedas de estudiantes en el Active Directory (solo lectura).                  | Adaptador |
| `prusaslicer.py`     | Lee gramos y tiempo del G-code de PrusaSlicer (texto o binario) o slicea un 3MF/STL con su consola. | Adaptador |
| `correos.py`         | Asunto y cuerpo HTML de los correos al usuario a partir de los datos de la boleta. | Plantillas |
| `outlook.py`         | Abre un correo como borrador en Outlook clásico (nunca lo envía solo).           | Adaptador |
| `ui/main_window.py`  | Ventana principal: actúa como **controlador** entre la vista y el repositorio.   | Separación vista/lógica |
| `ui/theme.py`        | Colores de cada fase y fuentes. Único lugar con la apariencia visual.            | Configuración centralizada |
| `ui/boleta_form.py`  | **Orquestador** del formulario: arma las secciones desplegables, navega y guarda; no conoce el detalle de cada fase. | Separación vista/lógica |
| `ui/phases/`         | **Una fase por archivo.** Cada fase (sección desplegable) es una clase autocontenida con sus widgets, callbacks y carga/guardado. | **Strategy / Plugin** |

### Cada fase es un archivo independiente

El formulario está diseñado para que **cambiar o añadir una fase solo toque su
propio archivo**, sin afectar a las demás. Cada fase es una subclase de
`PhaseSection` (en `ui/phases/base.py`) que implementa:

- `build_widgets(frame)` — construye sus widgets dentro de su sección.
  La base ofrece ayudantes para armar la cuadrícula como en la boleta
  (`new_row`, `field`, `operator_row`, `radio_group`, `checkbox`...).
- `on_populate(data)` *(opcional)* — carga datos propios al editar (p. ej. la
  lista de fallos de la Fase 3 o el motivo de la Fase 7).
- `on_collect(form_data)` *(opcional)* — aporta datos propios al guardar.

El `BoletaForm` solo recorre el registro de fases (`ui/phases/__init__.py`) y
llama a estos métodos; no contiene lógica específica de ninguna fase.

**Para añadir una fase nueva:**

1. Crea `ui/phases/faseN_nombre.py` con una subclase de `PhaseSection`.
2. Regístrala en `ui/phases/__init__.py` (`PHASE_CLASSES`).
3. Añádela a `config.FASES` y sus campos obligatorios a `config.REQUIRED_FIELDS`.
4. Añade el color de su barra a `theme.PHASE_COLORS`.

No se toca el código de las otras fases ni el de `boleta_form.py`.

**Ventajas de esta organización**

- Para cambiar una fase, una opción o el precio basta con editar `config.py`.
- Si algún día se quiere pasar de Excel a una base de datos, solo se reescribe
  `repository.py`; la interfaz no cambia.
- La lógica de negocio (`services.py`) puede probarse sin abrir ninguna ventana.

---

## 🚀 Cómo ejecutarlo

Requisitos: **Python 3** con las dependencias instaladas.

```bash
cd "Boletas Corte Laser"
pip install -r requirements.txt
cd src
python main.py
```

El archivo `control_impresiones.xlsx` se busca/crea en el directorio desde el
que se ejecuta la aplicación.

---

## 📦 Empaquetar como ejecutable (.exe)

Con [PyInstaller](https://pyinstaller.org/):

```bash
cd "Boletas Corte Laser/src"
python -m PyInstaller --onefile --windowed --noupx --collect-data customtkinter main.py
```

El ejecutable queda en `src/dist/`. PyInstaller detecta automáticamente los
módulos del paquete `boletas/` al seguir los imports desde `main.py`.
`--collect-data customtkinter` incluye los archivos de temas que CustomTkinter
necesita en tiempo de ejecución; sin esa opción el `.exe` no abre.

> El comando regenera `main.spec`. No compiles con un `main.spec` antiguo
> (`pyinstaller main.spec`) si no incluye los datos de CustomTkinter.

---

## 🧩 Cómo hacer cambios habituales

| Quiero…                                   | Edito…                                              |
|-------------------------------------------|-----------------------------------------------------|
| Añadir/renombrar una fase                 | `config.py` → `FASES` (y `REQUIRED_FIELDS`)         |
| Cambiar precio, materiales, colores, usos/prioridades, impresoras... | **⚙ Configuración** en la app (sin recompilar). Los valores por defecto están en `config.py` (`PRECIO_POR_GRAMO`, `MATERIAL_OPTIONS`, `COLORES_POR_MATERIAL`, `USOS`, `IMPRESORAS`, `TIPOS_IMPRESORA`...) |
| Hacer editable un valor nuevo de `config.py` | Añadirlo a `ajustes.EDITABLES` y a `ui/config_window.py` |
| Cambiar el algoritmo del orden de impresión | `planificador.py`                                |
| Cambiar qué campos son obligatorios       | `config.py` → `REQUIRED_FIELDS`                     |
| Cambiar cómo se guardan/leen los datos    | `repository.py`                                     |
| Cambiar/añadir una **fase** del formulario| `ui/phases/faseN_*.py` (+ registro y `config.py`)   |
| Cambiar la ventana principal o la navegación | `ui/main_window.py` o `ui/boleta_form.py`        |
| Cambiar el color de una fase o la fuente  | `ui/theme.py` → `PHASE_COLORS` / `FONT_FAMILY`      |

---

## 🛠️ Dependencias

- Python 3
- [pandas](https://pandas.pydata.org/) — manejo de datos
- [openpyxl](https://openpyxl.readthedocs.io/) — lectura/escritura de Excel
- [CustomTkinter](https://customtkinter.tomschimansky.com/) — interfaz gráfica
  moderna sobre [tkinter](https://docs.python.org/3/library/tkinter.html)
