# Context.md

Contexto del proyecto para retomar el trabajo entre sesiones. Las reglas de
trabajo están en [CLAUDE.md](CLAUDE.md).

_Última revisión: 2026-10-26._

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
| 1 | Recepción | operador, fecha/hora, cuenta, carrera, carné, teléfono, uso (+detalle), pieza, copias, material, resolución, relleno |
| 2 | Revisión y Preparación | gramos de material, tiempo de impresión, **precio** (= g × `PRECIO_POR_GRAMO`, 50 ₡) |
| 3 | Impresión | confirmación del usuario, impresora (1–7), envío de correo, **lista de fallos** (solo se agregan, no se eliminan), **notas de impresión** |
| 4 | Despegado de Piezas | observaciones, ¿imprimió bien?, correo |
| 5 | Entrega de Piezas | verificación de cobro, recibido conforme |
| 6 | Reimpresión | observaciones, gramos, tiempo, precio |
| 7 | Cancelación | motivo de cancelación |

- La fase actual se guarda en `Fase Actual`; `PhaseDetector` puede deducirla
  como la fase más avanzada con operador.
- En Revisión e Impresión el listado se ordena por prioridad de uso
  (Curso/Evento → Asistencia → Personal) y luego por fecha de recepción.
- Validación de campos obligatorios al avanzar de fase y al guardar
  (`config.REQUIRED_FIELDS`).

## Persistencia actual

- Un único Excel `control_impresiones.xlsx` en el directorio de trabajo.
- Se carga entero en memoria (DataFrame, todo como `str` salvo `ID Boleta`).
- Se guarda al cerrar la ventana principal, al guardar una boleta y al borrar.
- El ID nuevo es `max(ID) + 1`.
- **Limitación:** no soporta varias PCs escribiendo a la vez (último que guarda
  pisa al otro) y falla si el Excel está abierto en Office.

## Estado del repositorio

- Rama de trabajo: `Chris-Development`; rama principal: `main` (PRs en GitHub,
  `ChrisRC7`).
- `src/dist/main.exe` y `src/dist/control_impresiones.xlsx` están versionados
  (binario de distribución y datos de ejemplo). `build/` está ignorado.
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
9. Editor de valores configurables (material, resolución, relleno, impresora)
   desde un archivo, posiblemente como app aparte.

## Active Directory (implementado)

- Módulo `src/boletas/directorio_ad.py` (`DirectorioAD`), solo lectura. Usa
  `DirectorySearcher` de Windows vía PowerShell con las credenciales de la
  sesión: no hay contraseñas ni librerías extra. Dominio `ESTUDIANTES.TEC.CR`.
- Atributos: `sAMAccountName` = cuenta (usuario del correo; los correos siempre
  son `@estudiantec.cr`), `employeeID` = carné, `name` = nombre completo,
  `mail` = correo, `description` = "SEDE - CARRERA".
- **Operador** (todas las fases): si se escribe un correo o un carné, se
  sustituye por el nombre completo. Un texto sin `@` que no sea carné se deja
  tal cual.
- **Cuenta / Carné** (Fase 1): primero se buscan boletas anteriores del usuario
  (`BoletaRepository.buscar_datos_usuario`); si no hay, se consulta el AD. Solo
  se llenan campos vacíos. Los estudiantes no suelen tener teléfono en el AD.
- Las consultas al AD corren en segundo plano (`BoletaForm.en_segundo_plano`).
  Si la PC no está en el dominio, simplemente no se autocompleta nada.

## Notas de diseño para lo que viene

- **SQLite / Jetson:** reemplazar solo `repository.py` manteniendo la misma
  interfaz pública (`load`, `save`, `all`, `search`, `filter_by_phase`,
  `get_next_id`, `get_by_id`, `add`, `update`, `delete`). Así la UI no cambia.
- **Opciones editables (punto 9):** mover las listas de `config.py` a un archivo
  (JSON/TOML) leído por `config.py`, para que el resto del código no cambie.
