"""Orden óptimo de impresión del día (sin interfaz).

Reparte los trabajos pendientes entre las impresoras activas respetando:

1. **Prioridad**: por tipo de uso (Curso/Evento → Asistencia → Personal) y, a
   igual prioridad, el trabajo recibido primero.
2. **Tipo de impresora**: cada trabajo solo va a impresoras del tipo que se
   pidió en la Revisión (o a cualquiera si se marcó "Cualquiera").
3. **Rollos abiertos**: normalmente hay un solo rollo abierto por material y
   color (un PLA negro, un PETG verde...), así que los trabajos de un mismo
   filamento no se imprimen a la vez en dos impresoras. Solo si la demanda del
   día de ese filamento supera un rollo (`config.GRAMOS_POR_ROLLO`) se permite
   abrir más: tantos rollos simultáneos como `ceil(gramos / gramos_por_rollo)`.
4. **Impresoras ocupadas**: las que tienen un trabajo en la Fase 3 quedan
   libres cuando ese trabajo termina (hora de inicio + tiempo estimado), y ya
   tienen cargado su filamento, así que se prefieren para trabajos del mismo.

Algoritmo (programación por lista): se recorren los trabajos en orden de
prioridad y cada uno se asigna a la impresora compatible donde puede empezar
antes sin superar el límite de rollos de su filamento; a igual hora de inicio
se prefiere la que ya tiene ese filamento cargado (evita cambios de rollo).

Los tiempos se manejan en minutos desde "ahora".
"""

import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from . import catalogo, config
from .services import PhaseDetector

SIN_COLOR = "(sin color)"


# --- Modelo -----------------------------------------------------------------
@dataclass
class Trabajo:
    boleta_id: int
    usuario: str
    pieza: str
    material: str
    color: str
    gramos: float
    minutos: int
    tipo_requerido: str
    prioridad: int
    recibido: datetime
    reimpresion: bool = False

    @property
    def filamento(self):
        return (self.material, self.color)


@dataclass
class Impresora:
    numero: int
    tipo: str
    libre_en: int = 0              # Minutos desde ahora hasta que queda libre.
    filamento: tuple = None        # (material, color) cargado, si se sabe.
    boleta_en_curso: int = None    # Boleta que está imprimiendo ahora.
    disponible: bool = True        # False = el operador la excluyó del plan.


@dataclass
class Asignacion:
    trabajo: Trabajo
    impresora: Impresora
    inicio: int
    fin: int
    cambio_filamento: bool


@dataclass
class Plan:
    generado: datetime
    asignaciones: list = field(default_factory=list)
    sin_programar: list = field(default_factory=list)   # (boleta_id, motivo)
    rollos: list = field(default_factory=list)          # (filamento, gramos, rollos)
    impresoras: list = field(default_factory=list)

    def hora(self, minutos):
        """Hora de reloj a partir de minutos desde la generación del plan."""
        momento = self.generado + timedelta(minutes=minutos)
        texto = momento.strftime(config.FORMATO_HORA)
        if momento.date() != self.generado.date():
            texto = momento.strftime("%d/%m ") + texto
        return texto


# --- Lectura de valores de las boletas -------------------------------------
def minutos_desde_texto(texto):
    """'2:30' -> 150. Un número solo se toma como horas ('1.5' -> 90). None si no se entiende."""
    texto = str(texto or "").strip()
    coincidencia = re.fullmatch(r"(\d+)\s*[:hH]\s*(\d{1,2})", texto)
    if coincidencia:
        return int(coincidencia.group(1)) * 60 + int(coincidencia.group(2))
    try:
        horas = float(texto.replace(",", "."))
    except ValueError:
        return None
    return round(horas * 60) if horas >= 0 else None


def gramos_desde_texto(texto):
    try:
        gramos = float(str(texto or "").strip().replace(",", "."))
    except ValueError:
        return None
    return gramos if gramos > 0 else None


def _fecha_hora(fecha, hora):
    try:
        return datetime.strptime(f"{fecha} {hora}".strip(), f"{config.FORMATO_FECHA} {config.FORMATO_HORA}")
    except ValueError:
        try:
            return datetime.strptime(str(fecha).strip(), config.FORMATO_FECHA)
        except ValueError:
            return None


def _filamento_de(registro):
    material = str(registro.get('Material', '')).strip()
    if material == config.MATERIAL_OTRO:
        material = str(registro.get('Material_Otro_Detalle', '')).strip() or config.MATERIAL_OTRO
    color = str(registro.get('Color_Filamento', '')).strip() or SIN_COLOR
    return material or "(sin material)", color


# --- Servicio ---------------------------------------------------------------
class PlanificadorService:
    """Arma el plan de impresión a partir de las boletas del repositorio."""

    def __init__(self, repositorio):
        self.repositorio = repositorio

    def estado_actual(self, ahora=None):
        """Lee las boletas: (trabajos pendientes, impresoras con su ocupación, sin programar)."""
        ahora = ahora or datetime.now()
        impresoras = {
            i["numero"]: Impresora(numero=i["numero"], tipo=i.get("tipo", ""))
            for i in catalogo.impresoras_activas()
        }
        trabajos, sin_programar = [], []

        for registro in self.repositorio.registros():
            fase = config.FASES.index(PhaseDetector.detectar_fase_actual(registro))
            boleta_id = int(registro.get('ID Boleta') or 0)

            if fase == 0:
                if str(registro.get('F1_Operador', '')).strip():
                    sin_programar.append((boleta_id, "Pendiente de Revisión (faltan gramos y tiempo)"))
            elif fase == 1 or (fase == 2 and not str(registro.get('Impresora_Num', '')).strip()):
                self._agregar_trabajo(registro, 'Uso_Material_g', 'Tiempo_Impresion_HHMM',
                                      trabajos, sin_programar, reimpresion=False)
            elif fase == 2:
                self._marcar_ocupada(registro, impresoras, ahora)
            elif fase == 5:
                self._agregar_trabajo(registro, 'F6_Uso_Material_g', 'F6_Tiempo_Impresion_HHMM',
                                      trabajos, sin_programar, reimpresion=True)

        return trabajos, sorted(impresoras.values(), key=lambda i: i.numero), sin_programar

    @staticmethod
    def _agregar_trabajo(registro, col_gramos, col_tiempo, trabajos, sin_programar, reimpresion):
        boleta_id = int(registro.get('ID Boleta') or 0)
        gramos = gramos_desde_texto(registro.get(col_gramos))
        minutos = minutos_desde_texto(registro.get(col_tiempo))
        if gramos is None or not minutos:
            sin_programar.append((boleta_id, "Faltan los gramos o el tiempo de impresión"))
            return
        material, color = _filamento_de(registro)
        trabajos.append(Trabajo(
            boleta_id=boleta_id,
            usuario=str(registro.get('Nombre_Usuario', '') or registro.get('Cuenta', '')).strip(),
            pieza=str(registro.get('Nombre_Pieza', '')).strip(),
            material=material, color=color, gramos=gramos, minutos=minutos,
            tipo_requerido=str(registro.get('Tipo_Impresora', '')).strip(),
            prioridad=catalogo.prioridad_uso(str(registro.get('Uso', '')).strip()),
            recibido=_fecha_hora(registro.get('F1_Fecha', ''), registro.get('F1_Hora', '')) or datetime.max,
            reimpresion=reimpresion,
        ))

    @staticmethod
    def _marcar_ocupada(registro, impresoras, ahora):
        try:
            numero = int(float(str(registro.get('Impresora_Num', '')).strip()))
        except ValueError:
            return
        impresora = impresoras.get(numero)
        if impresora is None:
            return  # Impresora inactiva o que ya no existe.
        inicio = _fecha_hora(registro.get('F3_Fecha', ''), registro.get('F3_Hora', ''))
        minutos = minutos_desde_texto(registro.get('Tiempo_Impresion_HHMM'))
        restante = 0
        if inicio and minutos:
            restante = max(0, math.ceil((inicio + timedelta(minutes=minutos) - ahora).total_seconds() / 60))
        impresora.libre_en = max(impresora.libre_en, restante)
        impresora.filamento = _filamento_de(registro)
        impresora.boleta_en_curso = int(registro.get('ID Boleta') or 0)


# --- Algoritmo --------------------------------------------------------------
def orden_prioridad(trabajos):
    """Prioridad de uso, luego el más antiguo, luego el número de boleta."""
    return sorted(trabajos, key=lambda t: (t.prioridad, t.recibido, t.boleta_id))


def _primer_inicio(impresora, duracion, libre_en, intervalos, limite):
    """Primer minuto >= libre_en en que el filamento no supera `limite` impresoras a la vez."""
    candidatos = sorted({libre_en} | {fin for num, _ini, fin in intervalos
                                      if num != impresora.numero and fin > libre_en})
    for inicio in candidatos:
        fin = inicio + duracion
        ocupadas = {num for num, ini, f in intervalos
                    if num != impresora.numero and ini < fin and f > inicio}
        if len(ocupadas) < limite:
            return inicio
    return candidatos[-1]


def planificar(trabajos, impresoras, sin_programar=(), gramos_por_rollo=None, ahora=None):
    """Devuelve un `Plan` con la asignación de cada trabajo a una impresora."""
    gramos_por_rollo = gramos_por_rollo or config.GRAMOS_POR_ROLLO
    plan = Plan(generado=ahora or datetime.now(), sin_programar=list(sin_programar),
                impresoras=list(impresoras))
    disponibles = [i for i in impresoras if i.disponible]

    # Demanda del día por filamento -> cuántos rollos pueden estar abiertos a la vez.
    demanda = {}
    for t in trabajos:
        demanda[t.filamento] = demanda.get(t.filamento, 0) + t.gramos
    limite = {f: max(1, math.ceil(g / gramos_por_rollo)) for f, g in demanda.items()}
    plan.rollos = sorted(((f, g, limite[f]) for f, g in demanda.items()), key=lambda r: (-r[1], r[0]))

    # Estado de cada impresora y uso de cada filamento en el tiempo.
    libre = {i.numero: i.libre_en for i in disponibles}
    cargado = {i.numero: i.filamento for i in disponibles}
    intervalos = {}  # filamento -> [(impresora, inicio, fin)]
    for i in disponibles:
        if i.filamento and i.libre_en > 0:
            intervalos.setdefault(i.filamento, []).append((i.numero, 0, i.libre_en))

    for trabajo in orden_prioridad(trabajos):
        compatibles = [i for i in disponibles if catalogo.tipo_compatible(trabajo.tipo_requerido, i.tipo)]
        if not compatibles:
            tipo = trabajo.tipo_requerido or "cualquiera"
            plan.sin_programar.append((trabajo.boleta_id, f"No hay impresoras disponibles de tipo {tipo}"))
            continue

        usos = intervalos.setdefault(trabajo.filamento, [])
        mejor = None
        for impresora in compatibles:
            inicio = _primer_inicio(impresora, trabajo.minutos, libre[impresora.numero],
                                    usos, limite[trabajo.filamento])
            cambio = cargado[impresora.numero] != trabajo.filamento
            clave = (inicio, cambio, impresora.numero)
            if mejor is None or clave < mejor[0]:
                mejor = (clave, impresora, inicio, cambio)

        _clave, impresora, inicio, cambio = mejor
        fin = inicio + trabajo.minutos
        plan.asignaciones.append(Asignacion(trabajo, impresora, inicio, fin, cambio))
        libre[impresora.numero] = fin
        cargado[impresora.numero] = trabajo.filamento
        usos.append((impresora.numero, inicio, fin))

    plan.asignaciones.sort(key=lambda a: (a.inicio, a.impresora.numero))
    return plan


# --- Reporte ----------------------------------------------------------------
def nombre_filamento(filamento):
    material, color = filamento
    return f"{material} {color}"


def duracion_texto(minutos):
    return f"{minutos // 60}:{minutos % 60:02d}"


def plan_a_texto(plan):
    """Reporte en texto plano, listo para imprimir."""
    lineas = [
        "LAIMI - ORDEN DE IMPRESIÓN",
        f"Generado: {plan.generado.strftime(config.FORMATO_FECHA)} {plan.generado.strftime(config.FORMATO_HORA)}",
        "",
        "ESTADO DE LAS IMPRESORAS",
    ]
    for i in plan.impresoras:
        estado = "Fuera del plan" if not i.disponible else (
            f"Ocupada (boleta {i.boleta_en_curso}) hasta {plan.hora(i.libre_en)}" if i.libre_en > 0 else "Libre")
        cargado = f" · cargada con {nombre_filamento(i.filamento)}" if i.filamento else ""
        lineas.append(f"  Impresora {i.numero} ({i.tipo}): {estado}{cargado}")

    lineas += ["", "ROLLOS DEL DÍA (máximo abiertos a la vez)"]
    for filamento, gramos, rollos in plan.rollos:
        lineas.append(f"  {nombre_filamento(filamento):<28} {gramos:>8.0f} g  -> {rollos} rollo(s)")

    for impresora in [i for i in plan.impresoras if i.disponible]:
        propias = [a for a in plan.asignaciones if a.impresora is impresora]
        if not propias:
            continue
        lineas += ["", f"IMPRESORA {impresora.numero} ({impresora.tipo})"]
        for n, a in enumerate(propias, 1):
            t = a.trabajo
            cambio = "  [cambiar rollo]" if a.cambio_filamento else ""
            reimp = " (reimpresión)" if t.reimpresion else ""
            lineas.append(
                f"  {n}. {plan.hora(a.inicio)} - {plan.hora(a.fin)}  Boleta {t.boleta_id}{reimp}  "
                f"{nombre_filamento(t.filamento)}  {t.gramos:.0f} g  {duracion_texto(t.minutos)}  "
                f"P{t.prioridad}  {t.usuario}{cambio}"
            )

    if plan.sin_programar:
        lineas += ["", "SIN PROGRAMAR"]
        for boleta_id, motivo in sorted(plan.sin_programar):
            lineas.append(f"  Boleta {boleta_id}: {motivo}")
    return "\n".join(lineas) + "\n"
