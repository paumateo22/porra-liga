"""06 — Motor de puntuación.

Reglas (todas configurables en config/settings.json):
  · Acierto 1X2               -> +1
  · Acierto exacto            -> +1 adicional (un exacto vale 2 en total)
  · Bonus de rendimiento      -> según aciertos 1X2 en la jornada (8:+2, 9:+3, 10:+5)
  · Ganador/perdedor jornada  -> +1 / -1, solo para quien haya pronosticado
                                 más del 55% de los partidos de esa jornada
  · Desempates                -> jornadas ganadas, exactos, 1X2

Salidas:
  · participantes/<slug>/estadisticas/historial_puntos.json
  · data/clasificacion.json
  · data/reportes/reporte_06_jornadas.json
"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import (
    ANALISIS_DIR,
    CALENDARIO_FILE,
    CLASIFICACION_FILE,
    REALIDAD_FILE,
    REPORTES_DIR,
    cargar_json,
    cargar_nombres_mostrados,
    cargar_settings,
    carpeta_participante,
    clave_partido,
    desofuscar_marcador,
    guardar_json,
    listar_participantes,
    signo,
)

ESTADO_FINALIZADO = "finished"


def cargar_pronosticos(slug_jugador):
    """Devuelve {'J01': {id_partido: (gl, gv)}} de un jugador.

    El marcador se guarda ofuscado en el fichero (campo "marcador"); aquí es
    donde se descodifica, del lado del servidor, para poder puntuar. Los
    pronósticos ilegibles (fichero manipulado a mano) se ignoran sin más.
    """
    carpeta = carpeta_participante(slug_jugador) / "pronosticos"
    salida = {}
    if not carpeta.exists():
        return salida
    for fichero in sorted(carpeta.glob("J*.json")):
        datos = cargar_json(fichero, {})
        clave = fichero.stem
        marcadores = {}
        for p in datos.get("predicciones", []):
            if p.get("marcador") is None:
                continue
            try:
                marcadores[p["id"]] = desofuscar_marcador(p["marcador"], p["fecha"], clave)
            except Exception:  # noqa: BLE001
                continue
        salida[clave] = marcadores
    return salida


def calcular_bonus(aciertos, config_bonus):
    if not config_bonus:
        return 0
    if aciertos < config_bonus.get("umbral_minimo", 99):
        return 0
    return config_bonus.get("tabla", {}).get(str(aciertos), 0)


def evaluar_jornada(clave, partidos_reales, total_partidos, pronosticos_todos, settings):
    """Calcula el desglose de una jornada para todos los jugadores."""
    pts = settings["puntuaciones"]
    hab = settings["habilitadores"]

    finalizados = [p for p in partidos_reales if p["estado"] == ESTADO_FINALIZADO]
    cerrada = len(finalizados) == total_partidos and total_partidos > 0
    if not finalizados:
        return None

    reales = {p["id"]: p for p in finalizados}
    umbral = pts.get("porcentaje_minimo_participacion", 0.55)

    filas = {}
    for slug_jugador, pron in pronosticos_todos.items():
        mis = pron.get(clave, {})
        if not mis:
            continue

        aciertos_1x2 = aciertos_exactos = 0
        detalle = {}
        for pid, (gl, gv) in mis.items():
            real = reales.get(pid)
            if not real:
                continue  # partido aún no jugado
            acierto_1x2 = signo(gl, gv) == signo(real["goles_local"], real["goles_visitante"])
            acierto_exacto = (
                int(gl) == int(real["goles_local"]) and int(gv) == int(real["goles_visitante"])
            )
            aciertos_1x2 += int(acierto_1x2 and hab.get("acierto_1x2", 1))
            aciertos_exactos += int(acierto_exacto and hab.get("acierto_exacto", 1))
            puntos_partido = (
                acierto_1x2 * pts["puntos_1x2"] * hab.get("acierto_1x2", 1)
                + acierto_exacto * pts["puntos_exacto"] * hab.get("acierto_exacto", 1)
            )
            detalle[clave_partido(real["local"], real["visitante"])] = {
                "id": pid,
                "pronostico": f"{gl}-{gv}",
                "real": f"{real['goles_local']}-{real['goles_visitante']}",
                "acierto_1x2": bool(acierto_1x2),
                "acierto_exacto": bool(acierto_exacto),
                "puntos": puntos_partido,
            }

        puntos_partidos = sum(d["puntos"] for d in detalle.values())
        bonus = (
            calcular_bonus(aciertos_1x2, pts.get("bonus_rendimiento"))
            if hab.get("bonus_rendimiento", 1) else 0
        )
        pronosticados = len(mis)

        filas[slug_jugador] = {
            "partidos_pronosticados": pronosticados,
            "partidos_evaluados": len(detalle),
            "aciertos_1x2": aciertos_1x2,
            "aciertos_exactos": aciertos_exactos,
            "puntos_partidos": puntos_partidos,
            "bonus_rendimiento": bonus,
            "elegible_jornada": (pronosticados / total_partidos) > umbral if total_partidos else False,
            "es_ganador_jornada": False,
            "es_perdedor_jornada": False,
            "puntos_ganador_perdedor": 0,
            "puntos_totales": puntos_partidos + bonus,
            "detalle": detalle,
        }

    # Ganador / perdedor de la jornada: se calcula un resultado PROVISIONAL
    # siempre que haya al menos un partido jugado, no solo cuando la jornada
    # está completa. Además de quién va ganando/perdiendo ahora mismo, se
    # calcula si eso ya es matemáticamente imposible que cambie: a cada
    # jugador le puede quedar, como mucho, tantos aciertos 1X2 extra como
    # partidos pendientes tenga pronosticados (en el mejor de los casos, los
    # acierta todos). Si con ese máximo nadie más podría alcanzar al que va
    # primero (o esquivar al que va último), el resultado ya es seguro.
    #
    # Los PUNTOS de verdad (+1/-1 en la clasificación) solo se reparten
    # cuando la jornada está cerrada de verdad — esto es solo para mostrarlo
    # en la web con el aviso correspondiente, no cambia cómo puntúa nadie.
    resultado_jornada = None
    if hab.get("ganador_perdedor_jornada", 1):
        elegibles = {s: f for s, f in filas.items() if f["elegible_jornada"]}
        if len(elegibles) >= 2:
            actuales = {s: f["aciertos_1x2"] for s, f in elegibles.items()}
            maximo, minimo = max(actuales.values()), min(actuales.values())

            if maximo != minimo:
                ganadores_prov = sorted(s for s, v in actuales.items() if v == maximo)
                perdedores_prov = sorted(s for s, v in actuales.items() if v == minimo)

                if cerrada:
                    ganador_seguro = perdedor_seguro = True
                else:
                    restantes = {
                        s: sum(1 for pid in pronosticos_todos.get(s, {}).get(clave, {}) if pid not in reales)
                        for s in elegibles
                    }
                    potencial_max = {s: actuales[s] + restantes[s] for s in elegibles}
                    ganador_seguro = len(ganadores_prov) == 1 and all(
                        potencial_max[s] < maximo for s in elegibles if s != ganadores_prov[0]
                    )
                    perdedor_seguro = len(perdedores_prov) == 1 and all(
                        actuales[s] > potencial_max[perdedores_prov[0]] for s in elegibles if s != perdedores_prov[0]
                    )

                resultado_jornada = {
                    "ganadores": ganadores_prov,
                    "perdedores": perdedores_prov,
                    "ganador_seguro": ganador_seguro,
                    "perdedor_seguro": perdedor_seguro,
                }

                if cerrada:
                    for s in ganadores_prov:
                        filas[s]["es_ganador_jornada"] = True
                        filas[s]["puntos_ganador_perdedor"] += pts["ganador_jornada"]
                        filas[s]["puntos_totales"] += pts["ganador_jornada"]
                    for s in perdedores_prov:
                        filas[s]["es_perdedor_jornada"] = True
                        filas[s]["puntos_ganador_perdedor"] += pts["perdedor_jornada"]
                        filas[s]["puntos_totales"] += pts["perdedor_jornada"]

    return {"cerrada": cerrada, "filas": filas, "resultado_jornada": resultado_jornada}


def main():
    settings = cargar_settings()
    calendario = cargar_json(CALENDARIO_FILE, None)
    realidad = cargar_json(REALIDAD_FILE, {})

    # config/nombres.txt solo decora a quien YA esté registrado (es decir,
    # a quien ya haya mandado al menos un pronóstico real). No da de alta a
    # nadie por su cuenta: mientras no exista un pronóstico con ese nombre
    # base, la línea de nombres.txt se ignora sin más — ni aparece en la
    # clasificación ni se le pone la insignia.
    nombres_mostrados = cargar_nombres_mostrados()

    participantes = listar_participantes()

    if not participantes:
        print("⚠️  No hay participantes registrados todavía (config/participantes.json).")
        return 0

    pronosticos = {p["slug"]: cargar_pronosticos(p["slug"]) for p in participantes}
    # El nombre que se muestra y sus insignias pueden venir de config/nombres.txt;
    # si un slug no está ahí, se usa el nombre tal cual quedó registrado y sin
    # insignias.
    nombres = {p["slug"]: p["nombre"] for p in participantes}
    insignias_por_slug = {s: [] for s in nombres}
    for s, (nombre_base, insignias) in nombres_mostrados.items():
        if s in nombres:
            nombres[s] = nombre_base
            insignias_por_slug[s] = insignias
    ANALISIS_DIR.mkdir(parents=True, exist_ok=True)

    reporte = {}
    acumulado = {
        s: {
            "puntos_totales": 0,
            "puntos_partidos": 0,
            "bonus_rendimiento": 0,
            "puntos_ganador_perdedor": 0,
            "aciertos_1x2": 0,
            "aciertos_exactos": 0,
            "partidos_pronosticados": 0,
            "jornadas_jugadas": 0,
            "jornadas_ganadas": 0,
            "jornadas_perdidas": 0,
            "por_jornada": {},
        }
        for s in nombres
    }

    for clave in sorted(realidad, key=lambda k: int(k[1:])):
        total_partidos = len(calendario.get(clave, []))
        resultado = evaluar_jornada(
            clave, realidad[clave], total_partidos, pronosticos, settings
        )
        if not resultado:
            continue
        reporte[clave] = {
            "cerrada": resultado["cerrada"],
            "jugadores": {
                s: {k: v for k, v in f.items() if k != "detalle"}
                for s, f in resultado["filas"].items()
            },
        }

        # Fichero de análisis: desglose cruzado jugadores x partidos.
        guardar_json(ANALISIS_DIR / f"{clave}.json", {
            "clave": clave,
            "jornada": int(clave[1:]),
            "cerrada": resultado["cerrada"],
            "resultado_jornada": {
                "ganadores": [{"slug": s, "nombre": nombres.get(s, s)}
                              for s in resultado["resultado_jornada"]["ganadores"]],
                "perdedores": [{"slug": s, "nombre": nombres.get(s, s)}
                               for s in resultado["resultado_jornada"]["perdedores"]],
                "ganador_seguro": resultado["resultado_jornada"]["ganador_seguro"],
                "perdedor_seguro": resultado["resultado_jornada"]["perdedor_seguro"],
            } if resultado["resultado_jornada"] else None,
            "partidos": calendario.get(clave, []),
            "resultados": {
                str(p["id"]): {
                    "goles_local": p["goles_local"],
                    "goles_visitante": p["goles_visitante"],
                    "estado": p["estado"],
                } for p in realidad[clave]
            },
            "jugadores": [
                {
                    "slug": s,
                    "nombre": nombres.get(s, s),
                    "insignias": insignias_por_slug.get(s, []),
                    "aciertos_1x2": f["aciertos_1x2"],
                    "aciertos_exactos": f["aciertos_exactos"],
                    "bonus": f["bonus_rendimiento"],
                    "elegible": f["elegible_jornada"],
                    "ganador": f["es_ganador_jornada"],
                    "perdedor": f["es_perdedor_jornada"],
                    "puntos": f["puntos_totales"],
                    "pronosticados": f["partidos_pronosticados"],
                    "predicciones": {
                        str(d["id"]): {
                            "pronostico": d["pronostico"],
                            "acierto_1x2": d["acierto_1x2"],
                            "acierto_exacto": d["acierto_exacto"],
                            "puntos": d["puntos"],
                        } for d in f["detalle"].values()
                    },
                }
                for s, f in sorted(resultado["filas"].items(),
                                   key=lambda kv: -kv[1]["puntos_totales"])
            ],
        })
        for s, f in resultado["filas"].items():
            a = acumulado[s]
            a["puntos_totales"] += f["puntos_totales"]
            a["puntos_partidos"] += f["puntos_partidos"]
            a["bonus_rendimiento"] += f["bonus_rendimiento"]
            a["puntos_ganador_perdedor"] += f["puntos_ganador_perdedor"]
            a["aciertos_1x2"] += f["aciertos_1x2"]
            a["aciertos_exactos"] += f["aciertos_exactos"]
            a["partidos_pronosticados"] += f["partidos_pronosticados"]
            a["jornadas_jugadas"] += 1
            a["jornadas_ganadas"] += int(f["es_ganador_jornada"])
            a["jornadas_perdidas"] += int(f["es_perdedor_jornada"])
            a["por_jornada"][clave] = {
                "puntos": f["puntos_totales"],
                "aciertos_1x2": f["aciertos_1x2"],
                "aciertos_exactos": f["aciertos_exactos"],
                "bonus": f["bonus_rendimiento"],
                "ganador": f["es_ganador_jornada"],
                "perdedor": f["es_perdedor_jornada"],
                "detalle": resultado["filas"][s]["detalle"],
            }

    # Historial individual
    for s, a in acumulado.items():
        guardar_json(
            carpeta_participante(s) / "estadisticas" / "historial_puntos.json",
            {"participante": s, "nombre": nombres[s], "insignias": insignias_por_slug.get(s, []), **a},
        )

    # Clasificación ordenada con desempates
    criterios = settings.get("desempates", ["jornadas_ganadas", "aciertos_exactos", "aciertos_1x2"])
    orden = sorted(
        acumulado.items(),
        key=lambda kv: (kv[1]["puntos_totales"], *[kv[1].get(c, 0) for c in criterios]),
        reverse=True,
    )

    clasificacion = []
    for i, (s, a) in enumerate(orden, start=1):
        clasificacion.append({
            "puesto": i,
            "slug": s,
            "nombre": nombres[s],
            "insignias": insignias_por_slug.get(s, []),
            "puntos_totales": a["puntos_totales"],
            "puntos_partidos": a["puntos_partidos"],
            "bonus_rendimiento": a["bonus_rendimiento"],
            "puntos_ganador_perdedor": a["puntos_ganador_perdedor"],
            "aciertos_1x2": a["aciertos_1x2"],
            "aciertos_exactos": a["aciertos_exactos"],
            "partidos_pronosticados": a["partidos_pronosticados"],
            "jornadas_jugadas": a["jornadas_jugadas"],
            "jornadas_ganadas": a["jornadas_ganadas"],
            "jornadas_perdidas": a["jornadas_perdidas"],
            "por_jornada": {
                k: {kk: vv for kk, vv in v.items() if kk != "detalle"}
                for k, v in a["por_jornada"].items()
            },
        })

    guardar_json(CLASIFICACION_FILE, {
        "competicion": settings["competicion"]["nombre"],
        "generado": datetime.now().isoformat(timespec="seconds"),
        "jornadas_calculadas": sorted(reporte, key=lambda k: int(k[1:])),
        "desempates": criterios,
        "clasificacion": clasificacion,
    })
    guardar_json(REPORTES_DIR / "reporte_06_jornadas.json", reporte)

    print(f"✅ {len(reporte)} jornada(s) calculada(s), {len(clasificacion)} jugador(es).")
    for c in clasificacion[:10]:
        print(f"   {c['puesto']:>2}. {c['nombre']:<18} {c['puntos_totales']:>5} pts "
              f"({c['aciertos_1x2']} 1X2 / {c['aciertos_exactos']} exactos)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
