# CLAUDE.md

Guía para Claude Code (y cualquier asistente) al trabajar en este repositorio.
Para el contexto del dominio, el estado actual y las decisiones pendientes, lee
también [Context.md](Context.md). La documentación de usuario está en
[README.md](README.md).

---

## ⚠️ Reglas obligatorias (aplican en TODAS las sesiones)

1. **Código modular.** Todo cambio debe mantener (o mejorar) la separación por
   capas y la regla "una responsabilidad por archivo":
   - Constantes del dominio → `src/boletas/config.py`.
   - Acceso a datos → `src/boletas/repository.py` (la UI nunca toca pandas/Excel
     directamente).
   - Lógica de negocio sin interfaz → `src/boletas/services.py` (o un módulo
     nuevo dentro de `src/boletas/` si crece).
   - Apariencia (colores, fuentes) → `src/boletas/ui/theme.py`.
   - Cada fase del formulario → su propio archivo en `src/boletas/ui/phases/`.
   - Integraciones externas nuevas (p. ej. Active Directory, SQLite, red local)
     → en su propio módulo/paquete, detrás de una interfaz clara, nunca
     mezcladas con widgets.
   - Si un archivo empieza a mezclar responsabilidades, sepáralo.

2. **Git: nunca `pull` ni `push`.** Claude no ejecuta `git pull`, `git push`,
   `git fetch` + merge ni nada que traiga o envíe cambios del remoto. Claude
   **solo hace commits** locales (en una rama que no sea `main`). Al terminar la
   respuesta, **recordar al usuario que haga el `push`**.

3. **Active Directory (AD) = SOLO LECTURA.** Cualquier operación contra el AD,
   ya sea hecha por Claude (comandos, scripts, pruebas) o por la aplicación,
   debe ser exclusivamente de lectura (búsquedas/consultas `search`/`Get-AD*`).
   Prohibido: crear, modificar, mover, renombrar, deshabilitar o borrar
   objetos, cambiar contraseñas, atributos o membresías de grupos
   (`Set-AD*`, `New-AD*`, `Remove-AD*`, `Add-ADGroupMember`, `ldap modify/add/
   delete`, etc.). El código que acceda al AD debe exponer únicamente métodos
   de lectura y, cuando la librería lo permita, abrir la conexión en modo
   solo lectura.

4. **TODO.md.** Si existe un `TODO.md` en la raíz, mantenerlo actualizado en
   cada sesión: marcar las tareas hechas, listar las que faltan y añadir las
   nuevas que surjan.

---

## Resumen del proyecto

App de escritorio en **Python + CustomTkinter** para gestionar las boletas de
impresión 3D / corte láser del LAIMI. Cada boleta avanza por 7 fases y se
guarda en `control_impresiones.xlsx` (pandas + openpyxl).

## Comandos

```bash
pip install -r requirements.txt          # dependencias (customtkinter, pandas, openpyxl)
cd src && python main.py                 # ejecutar (el Excel se crea en el cwd)

# Empaquetar (.exe en src/dist/). Siempre con --collect-data customtkinter;
# no compilar con un main.spec viejo que no lo incluya.
cd src && python -m PyInstaller --onefile --windowed --noupx --collect-data customtkinter main.py
```

No hay suite de tests ni linter configurado. `services.py` y `repository.py`
se pueden probar sin abrir ventanas.

## Arquitectura (resumen)

```
src/main.py                 → arranca boletas.ui.main_window.App
src/boletas/config.py       → FASES, COLUMNAS, REQUIRED_FIELDS, opciones, precio
src/boletas/repository.py   → BoletaRepository (CRUD/búsqueda/filtro sobre el Excel)
src/boletas/services.py     → PricingService, PhaseDetector, UsuarioService (historial → AD)
src/boletas/directorio_ad.py → DirectorioAD: consultas al AD (solo lectura, vía PowerShell)
src/boletas/ui/main_window.py → App: listado, búsqueda, filtro por fase (controlador)
src/boletas/ui/boleta_form.py → BoletaForm: orquesta las secciones, navega, valida, guarda
src/boletas/ui/phases/      → una PhaseSection por fase + registro PHASE_CLASSES
src/boletas/ui/theme.py     → colores de cada fase y fuentes
```

Dependencias apuntan hacia adentro: UI → services/config → repository. La capa
de datos no importa nada de la UI.

### Añadir o cambiar una fase

1. `ui/phases/faseN_nombre.py`: subclase de `PhaseSection` con
   `build_widgets(frame)` y, si hace falta, `on_populate(data)` /
   `on_collect(form_data)`.
2. Registrarla en `ui/phases/__init__.py` (`PHASE_CLASSES`).
3. Añadirla a `config.FASES`, sus columnas a `config.COLUMNAS`, etiquetas en
   `config.FIELD_NAMES` y obligatorios en `config.REQUIRED_FIELDS`.
4. Color en `theme.PHASE_COLORS`.

`boleta_form.py` no debe contener lógica específica de ninguna fase.

## Convenciones

- Idioma: código, comentarios, docstrings, mensajes de UI y commits en
  **español**.
- Cada módulo empieza con un docstring explicando su responsabilidad; las
  secciones dentro de una clase se separan con comentarios `# --- Sección ---`.
- Los textos de opciones (`USO_OPTIONS`, `PRIORIDAD_USO`, `USO_CON_DETALLE`)
  deben coincidir **exactamente**.
- Los nombres de fase (`config.FASES`) se guardan tal cual en la columna
  `Fase Actual` del Excel: renombrar una fase implica migrar los datos
  existentes.
- Errores de guardado: el repositorio lanza la excepción, la UI la traduce a un
  `messagebox`.
- Al cambiar estructura o comportamiento, actualizar `README.md` y
  `Context.md` si corresponde.
