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
- En las fases de Revisión e Impresión ordena por **prioridad de impresión**.
- Registra una lista dinámica de **fallos de impresión**.

### Las 7 fases

1. Recepción
2. Revisión y Preparación
3. Impresión
4. Despegado de Piezas
5. Entrega de Piezas
6. Reimpresión
7. Cancelada

---

## 📁 Estructura del proyecto

El código está **modularizado por capas** para que sea fácil de mantener: cada
archivo tiene una única responsabilidad y las capas no se mezclan.

```
Boletas Corte Laser/
├── README.md                  # Este archivo
└── src/
    ├── main.py                # Punto de entrada (arranca la app)
    ├── boletas/               # Paquete de la aplicación
    │   ├── __init__.py
    │   ├── config.py          # Constantes: fases, columnas, opciones, precio
    │   ├── repository.py      # Acceso a datos (Excel)        [patrón Repository]
    │   ├── services.py        # Lógica de negocio (precio, detección de fase)
    │   └── ui/                # Interfaz gráfica (CustomTkinter)
    │       ├── __init__.py
    │       ├── theme.py       # Colores de cada fase y fuentes (imitan la boleta)
    │       ├── main_window.py # Ventana principal (listado, búsqueda, filtros)
    │       ├── boleta_form.py # Orquestador del formulario (arma secciones, navega, guarda)
    │       └── phases/        # Una fase por archivo (cada sección es independiente)
    │           ├── __init__.py            # Registro de fases (PHASE_CLASSES)
    │           ├── base.py                # PhaseSection: clase base de una fase
    │           ├── fase1_recepcion.py
    │           ├── fase2_revision.py
    │           ├── fase3_impresion.py
    │           ├── fase4_despegado.py
    │           ├── fase5_entrega.py
    │           ├── fase6_reimpresion.py
    │           └── fase7_cancelada.py
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
| `services.py`        | Cálculos reutilizables sin interfaz: precio y detección de la fase actual.       | Servicios sin estado |
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
pip install customtkinter pandas openpyxl
cd "Boletas Corte Laser/src"
python main.py
```

El archivo `control_impresiones.xlsx` se busca/crea en el directorio desde el
que se ejecuta la aplicación.

---

## 📦 Empaquetar como ejecutable (.exe)

El proyecto incluye `main.spec` para [PyInstaller](https://pyinstaller.org/):

```bash
cd "Boletas Corte Laser/src"
python -m PyInstaller --onefile --windowed --strip --noupx --collect-data customtkinter main.py
```

El ejecutable queda en `src/dist/`. PyInstaller detecta automáticamente los
módulos del paquete `boletas/` al seguir los imports desde `main.py`.
`--collect-data customtkinter` incluye los archivos de temas que CustomTkinter
necesita en tiempo de ejecución.

---

## 🧩 Cómo hacer cambios habituales

| Quiero…                                   | Edito…                                              |
|-------------------------------------------|-----------------------------------------------------|
| Añadir/renombrar una fase                 | `config.py` → `FASES` (y `REQUIRED_FIELDS`)         |
| Cambiar el precio por gramo               | `config.py` → `PRECIO_POR_GRAMO`                    |
| Añadir una opción de material/uso         | `config.py` → `MATERIAL_OPTIONS` / `USO_OPTIONS`    |
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
