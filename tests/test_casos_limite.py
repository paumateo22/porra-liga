"""Test end-to-end de casos límite.

Simula el paso del tiempo: primero se pronostica, después se juegan los partidos.

  A) Partido ADELANTADO: un partido de la J10 se juega meses antes que el resto
     de su jornada. Debe puntuar solo, sin cerrar la jornada.
  B) Partido APLAZADO: un partido de la J02 se juega meses después que el resto.
     La jornada suma puntos pero no reparte ganador/perdedor hasta que se juegue.
  C) REENVÍO: un jugador manda la J02 dos veces. La segunda vez intenta cambiar
     un partido ya jugado (debe ignorarse) y corregir el aplazado (debe aceptarse),
     sin perder los demás partidos.
  D) CIERRE: al jugarse el aplazado la jornada cierra y se reparte ganador/perdedor.

Ejecutar desde la raíz:  python tests/test_casos_limite.py
"""
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))

from utils import (  # noqa: E402
    CALENDARIO_FILE,
    CLASIFICACION_FILE,
    ENTRADAS_DIR,
    PARTICIPANTES_DIR,
    PARTICIPANTES_FILE,
    REALIDAD_FILE,
    REPORTES_DIR,
    cargar_json,
    guardar_json,
)

EQUIPOS = ["Barcelona", "Real Madrid", "Atlético", "Athletic", "Real Sociedad",
           "Betis", "Villarreal", "Valencia", "Sevilla", "Celta",
           "Rayo", "Osasuna", "Getafe", "Girona", "Mallorca",
           "Alavés", "Espanyol", "Elche", "Levante", "Oviedo"]

AHORA = datetime.now()
fallos = []


def check(condicion, descripcion):
    print(f"  {'✅' if condicion else '❌'} {descripcion}")
    if not condicion:
        fallos.append(descripcion)


def limpiar():
    for carpeta in (PARTICIPANTES_DIR, REPORTES_DIR):
        if carpeta.exists():
            shutil.rmtree(carpeta)
        carpeta.mkdir(parents=True)
    if ENTRADAS_DIR.exists():
        for f in ENTRADAS_DIR.glob("*.json"):
            f.unlink()
        if (ENTRADAS_DIR / "procesadas").exists():
            shutil.rmtree(ENTRADAS_DIR / "procesadas")
    guardar_json(PARTICIPANTES_FILE, {"participantes": []})
    if CLASIFICACION_FILE.exists():
        CLASIFICACION_FILE.unlink()


def construir_calendario():
    """J02 y J10, 10 partidos cada una, todos aún por jugar."""
    calendario, pid = {}, 15000000
    for j, dias in ((2, 3), (10, 90)):
        partidos = []
        for i in range(0, 20, 2):
            pid += 1
            partidos.append({
                "id": pid,
                "local": EQUIPOS[i],
                "visitante": EQUIPOS[i + 1],
                "fecha": (AHORA + timedelta(days=dias, hours=i)).isoformat(timespec="seconds"),
            })
        calendario[f"J{j:02d}"] = partidos

    # A) El primer partido de la J10 se ADELANTA: se juega dentro de 2 días.
    calendario["J10"][0]["fecha"] = (AHORA + timedelta(days=2)).isoformat(timespec="seconds")
    # B) El último de la J02 se APLAZA: se juega dentro de 100 días.
    calendario["J02"][9]["fecha"] = (AHORA + timedelta(days=100)).isoformat(timespec="seconds")

    guardar_json(CALENDARIO_FILE, calendario)
    realidad = {
        c: [{**p, "goles_local": None, "goles_visitante": None, "estado": "notstarted"}
            for p in partidos]
        for c, partidos in calendario.items()
    }
    guardar_json(REALIDAD_FILE, realidad)
    return calendario, realidad


def jugar(realidad, clave, ids, marcadores):
    """Simula que unos partidos se juegan: pasan a 'finished' con su resultado.

    Ojo: NO se toca la fecha. En la vida real la hora de un partido no
    cambia solo porque termine — solo cambia si de verdad se aplaza o se
    adelanta, y eso ya lo simulan por separado los escenarios A y B. El
    bloqueo de "partido ya empezado" lo decide el campo "estado" de
    realidad_oficial.json, no hace falta tocar la fecha para conseguirlo."""
    for p in realidad[clave]:
        if p["id"] in ids:
            gl, gv = marcadores[p["id"]]
            p["goles_local"], p["goles_visitante"] = gl, gv
            p["estado"] = "finished"
    guardar_json(REALIDAD_FILE, realidad)


def en_directo(realidad, clave, id_partido, marcador):
    """Deja un partido EN JUEGO (no terminado) con un marcador provisional."""
    for p in realidad[clave]:
        if p["id"] == id_partido:
            p["goles_local"], p["goles_visitante"] = marcador
            p["estado"] = "inprogress"
    guardar_json(REALIDAD_FILE, realidad)


def escribir_entrada(nombre, jornada, predicciones, generado=None):
    guardar_json(ENTRADAS_DIR / f"J{jornada:02d}_{nombre}.json", {
        "participante": nombre,
        "jornada": jornada,
        "generado": generado or datetime.now().isoformat(timespec="seconds"),
        "predicciones": predicciones,
    })


def pred(p, gl, gv, clave):
    return {"id": p["id"], "local": p["local"], "visitante": p["visitante"],
            "fecha": p["fecha"], "goles_local": gl, "goles_visitante": gv}


def correr(script):
    r = subprocess.run([sys.executable, str(RAIZ / "scripts" / script)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout, r.stderr)
        raise SystemExit(f"{script} falló")
    return r.stdout


def guardadas(slug_jugador, clave):
    datos = cargar_json(PARTICIPANTES_DIR / slug_jugador / "pronosticos" / f"{clave}.json")
    return {p["id"]: (p["goles_local"], p["goles_visitante"]) for p in datos["predicciones"]}


def main():
    limpiar()
    calendario, realidad = construir_calendario()
    j02, j10 = calendario["J02"], calendario["J10"]
    adelantado, aplazado = j10[0], j02[9]

    # ---- Todos pronostican mientras no se ha jugado nada ----
    marcador_real = {p["id"]: (2, 1) for p in j02 + j10}

    escribir_entrada("Pau", 10, [pred(p, 2, 1, "J10") for p in j10])          # lo clava todo
    escribir_entrada("Aitor", 10, [pred(p, 0, 3, "J10") for p in j10])        # falla todo
    escribir_entrada("Pau", 2, [pred(p, 2, 1, "J02") for p in j02])
    escribir_entrada("Aitor", 2, [pred(p, 0, 3, "J02") for p in j02])
    escribir_entrada("Javi", 2, [pred(p, 1, 1, "J02") for p in j02])          # empate: falla todo
    correr("03_ingesta_pronosticos.py")

    check(len(guardadas("pau", "J10")) == 10, "se guardan los 10 partidos de la J10")

    print("\n═══ A: partido ADELANTADO de la J10 ═══")
    jugar(realidad, "J10", {adelantado["id"]}, marcador_real)
    correr("06_motor_puntuacion.py")
    rep = cargar_json(REPORTES_DIR / "reporte_06_jornadas.json")

    check("J10" in rep, "la J10 se evalúa aunque solo tenga 1 de 10 partidos jugados")
    check(rep["J10"]["cerrada"] is False, "la J10 NO se marca como cerrada")
    pau10 = rep["J10"]["jugadores"]["pau"]
    check(pau10["partidos_evaluados"] == 1, "solo se evalúa el partido adelantado")
    check(pau10["aciertos_exactos"] == 1 and pau10["aciertos_1x2"] == 1,
          "el acierto exacto del adelantado cuenta")
    check(pau10["puntos_totales"] == 3, "un exacto (2) + ganador provisional de la jornada abierta (+1) = 3")
    check(pau10["bonus_rendimiento"] == 0, "1 acierto no dispara bonus")
    check(rep["J10"]["jugadores"]["pau"]["es_ganador_jornada"]
          and rep["J10"]["jugadores"]["aitor"]["es_perdedor_jornada"],
          "el ganador/perdedor de jornada se reparte ya en vivo, aunque la jornada siga abierta")

    print("\n═══ B: la J02 se juega salvo el APLAZADO ═══")
    ids_j02 = {p["id"] for p in j02} - {aplazado["id"]}
    jugar(realidad, "J02", ids_j02, marcador_real)
    correr("06_motor_puntuacion.py")
    rep = cargar_json(REPORTES_DIR / "reporte_06_jornadas.json")
    j02rep = rep["J02"]

    check(j02rep["cerrada"] is False, "la J02 sigue abierta por el aplazado")
    pau02 = j02rep["jugadores"]["pau"]
    check(pau02["partidos_evaluados"] == 9, "se evalúan los 9 jugados, no el aplazado")
    check(pau02["aciertos_1x2"] == 9, "los 9 aciertos 1X2 cuentan ya")
    check(pau02["bonus_rendimiento"] == 3, "9 aciertos dan bonus +3 aunque falte 1 partido")
    check(pau02["puntos_totales"] == 22, "9 exactos (18) + bonus 3 + ganador provisional 1 = 22")
    check(j02rep["jugadores"]["pau"]["es_ganador_jornada"],
          "el ganador de jornada SÍ se reparte ya, aunque falte el aplazado por jugarse")

    print("\n═══ C: REENVÍO de la J02 con partidos ya jugados ═══")
    antes = guardadas("pau", "J02")
    jugado_id = j02[0]["id"]

    escribir_entrada("Pau", 2, [
        pred(j02[0], 7, 7, "J02"),        # ya jugado -> debe ignorarse
        pred(aplazado, 3, 0, "J02"),      # aún sin jugar -> debe aceptarse
    ])
    salida = correr("03_ingesta_pronosticos.py")
    despues = guardadas("pau", "J02")

    check(despues[jugado_id] == antes[jugado_id],
          "el partido ya jugado conserva el pronóstico original")
    check(despues[aplazado["id"]] == (3, 0),
          "el partido aplazado acepta el nuevo pronóstico")
    check(len(despues) == 10,
          "el reenvío parcial no borra los otros 8 partidos (fusión, no sobrescritura)")
    check("1 bloqueados" in salida, "la consola informa del partido bloqueado")

    correr("06_motor_puntuacion.py")
    rep = cargar_json(REPORTES_DIR / "reporte_06_jornadas.json")
    check(rep["J02"]["jugadores"]["pau"]["aciertos_1x2"] == 9,
          "los puntos de la J02 no cambian tras el reenvío")

    print("\n═══ D: se juega el APLAZADO y la jornada cierra ═══")
    jugar(realidad, "J02", {aplazado["id"]}, {aplazado["id"]: (3, 0)})
    correr("06_motor_puntuacion.py")
    rep = cargar_json(REPORTES_DIR / "reporte_06_jornadas.json")
    j02rep = rep["J02"]
    pau02 = j02rep["jugadores"]["pau"]

    check(j02rep["cerrada"] is True, "la J02 se cierra al jugarse el aplazado")
    check(pau02["aciertos_1x2"] == 10, "el aplazado suma el acierto nº10 a Pau")
    check(pau02["aciertos_exactos"] == 10, "el pronóstico corregido del aplazado era exacto")
    check(pau02["bonus_rendimiento"] == 5, "el bonus sube de +3 a +5 al completar los 10")
    check(pau02["es_ganador_jornada"] is True, "ahora sí se asigna ganador de jornada")
    check(pau02["puntos_totales"] == 26, "10 exactos (20) + bonus 5 + ganador 1 = 26")
    perdedores = [s for s, v in j02rep["jugadores"].items() if v["es_perdedor_jornada"]]
    check(len(perdedores) == 2, f"empate en el mínimo: dos perdedores {perdedores}")

    print("\n═══ E: la J10 sigue viva con su partido adelantado ═══")
    clas = cargar_json(CLASIFICACION_FILE)
    pau = next(c for c in clas["clasificacion"] if c["slug"] == "pau")
    check(set(clas["jornadas_calculadas"]) == {"J02", "J10"},
          "ambas jornadas aparecen en la clasificación")
    check(pau["por_jornada"]["J10"]["puntos"] == 3,
          "la J10 mantiene los 3 puntos del adelantado (2 de acierto exacto + 1 de ganador provisional)")
    check(pau["puntos_totales"] == 29, "total = 26 (J02) + 3 (J10)")

    print("\n═══ F: alguien se incorpora a mitad de temporada (punto de partida) ═══")
    # "elena" no existía hasta ahora: manda su primera jornada en la J10, la
    # segunda y última jornada del calendario de prueba (nunca jugó la J02).
    # Alfabéticamente "elena" va DESPUÉS de "aitor" — si hubiera contaminación
    # de orden (que veteranos ya hubieran sumado sus puntos de la J10 antes de
    # calcular el punto de partida de elena), su valor saldría mal.
    j10 = cargar_json(CALENDARIO_FILE)["J10"]
    escribir_entrada("Elena", 10, [pred(p, 3, 0, "J10") for p in j10[:5]])
    correr("03_ingesta_pronosticos.py")
    correr("06_motor_puntuacion.py")

    clas2 = cargar_json(CLASIFICACION_FILE)
    elena = next(c for c in clas2["clasificacion"] if c["slug"] == "elena")
    pau2 = next(c for c in clas2["clasificacion"] if c["slug"] == "pau")
    # El último tras la J02 (antes de que nadie sume nada de la J10) — se
    # recalcula aquí mismo a partir de lo que ya sabíamos de cada uno.
    aitor2 = next(c for c in clas2["clasificacion"] if c["slug"] == "aitor")
    javi2 = next(c for c in clas2["clasificacion"] if c["slug"] == "javi")
    ultimo_tras_j02 = min(
        aitor2["por_jornada"].get("J02", {}).get("puntos", 0),
        javi2["por_jornada"].get("J02", {}).get("puntos", 0),
    )
    check(elena["punto_partida"] == ultimo_tras_j02,
        f"el punto de partida de Elena ({elena['punto_partida']}) es el del último tras la J02 ({ultimo_tras_j02})")
    check(elena["aciertos_1x2"] == elena["por_jornada"]["J10"]["aciertos_1x2"],
        "los aciertos de Elena arrancan de cero, sin heredar nada del punto de partida")
    check(elena["jornadas_ganadas"] == 0 and elena["jornadas_perdidas"] == 0,
        "el punto de partida no cuenta como jornada ganada ni perdida")
    check(pau2["puntos_totales"] == 29,
        "el punto de partida de un jugador nuevo no altera los totales de los demás")

    print("\n═══ G: pronóstico legítimo que llega tarde al buzón (generado a tiempo) ═══")
    # Un partido de la J10 (distinto del adelantado) se juega, sin que nadie
    # lo haya pronosticado todavía en el servidor — como si el fichero se
    # hubiera generado a tiempo pero tardara en subirse al buzón.
    otro_j10 = j10[1]
    jugar(realidad, "J10", {otro_j10["id"]}, {otro_j10["id"]: (1, 0)})

    fecha_partido = datetime.fromisoformat(otro_j10["fecha"])
    generado_a_tiempo = (fecha_partido - timedelta(hours=2)).isoformat(timespec="seconds")
    generado_tarde = (fecha_partido + timedelta(hours=1)).isoformat(timespec="seconds")

    escribir_entrada("Nuria", 10, [pred(otro_j10, 1, 0, "J10")], generado=generado_a_tiempo)
    escribir_entrada("Manolo", 10, [pred(otro_j10, 1, 0, "J10")], generado=generado_tarde)
    correr("03_ingesta_pronosticos.py")

    guardado_nuria = guardadas("nuria", "J10")
    check(otro_j10["id"] in guardado_nuria,
        "se acepta un pronóstico cuyo 'generado' es ANTERIOR al partido, aunque sea la primera vez que se ingiere y el partido ya haya terminado")

    ruta_manolo = PARTICIPANTES_DIR / "manolo" / "pronosticos" / "J10.json"
    guardado_manolo = guardadas("manolo", "J10") if ruta_manolo.exists() else {}
    check(otro_j10["id"] not in guardado_manolo,
        "un pronóstico genuinamente tarde ('generado' POSTERIOR al partido) se sigue rechazando")

    print("\n═══ H: un partido EN DIRECTO puntúa con su marcador provisional ═══")
    # Un tercer partido de la J10 (distinto del adelantado y del jugado en el
    # escenario G) se pone "en directo" con un marcador que aún puede cambiar.
    en_vivo = j10[2]
    en_directo(realidad, "J10", en_vivo["id"], (1, 0))
    correr("06_motor_puntuacion.py")
    rep_h = cargar_json(REPORTES_DIR / "reporte_06_jornadas.json")
    pau_h = rep_h["J10"]["jugadores"]["pau"]

    # A estas alturas Pau ya tenía en J10: el adelantado (2-1 exacto, 2 pts)
    # y el partido del escenario G (1X2 acertado, 1 pt). Pronosticó 2-1 en
    # toda la jornada: con el marcador EN VIVO de este tercero (1-0) acierta
    # también el 1X2 (local gana), aunque no el exacto — +1 punto más.
    check(pau_h["aciertos_1x2"] == 3, "el acierto 1X2 del partido en directo ya cuenta (adelantado + G + este)")
    check(pau_h["puntos_partidos"] == 4, "2 (adelantado, exacto) + 1 (de G) + 1 (en directo, solo 1X2) = 4")
    check(rep_h["J10"]["cerrada"] is False,
        "un partido en directo no cuenta como terminado — la jornada sigue sin cerrarse")

    # Termina de verdad con un resultado DISTINTO al que tenía en directo
    # (empate 1-1 en vez de 1-0): el acierto 1X2 de Pau para ESE partido
    # deja de contar, sin que haga falta ninguna corrección manual — el
    # motor siempre recalcula desde cero.
    jugar(realidad, "J10", {en_vivo["id"]}, {en_vivo["id"]: (1, 1)})
    correr("06_motor_puntuacion.py")
    rep_h2 = cargar_json(REPORTES_DIR / "reporte_06_jornadas.json")
    pau_h2 = rep_h2["J10"]["jugadores"]["pau"]
    check(pau_h2["aciertos_1x2"] == 2,
        "al terminar con un resultado distinto al que tenía en directo (1-1 en vez de 1-0), el acierto se retira solo")
    check(pau_h2["puntos_partidos"] == 3,
        "vuelve a 3 (adelantado + G) — el partido en directo ya no acierta al cerrar con otro marcador")

    print("\n" + "─" * 62)
    if fallos:
        print(f"❌ {len(fallos)} comprobación(es) fallida(s):")
        for f in fallos:
            print(f"   · {f}")
        return 1
    print("✅ Todos los casos límite pasan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
