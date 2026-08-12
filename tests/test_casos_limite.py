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
    desofuscar_marcador,
    guardar_json,
    ofuscar_marcador,
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
    adelanta, y eso ya lo simulan por separado los escenarios A y B. Cambiar
    la fecha aquí también rompía la ofuscación del marcador (que ahora usa
    la fecha como parte de la clave): el bloqueo de "partido ya empezado" ya
    lo decide el campo "estado" de realidad_oficial.json, no hace falta
    tocar la fecha para conseguirlo."""
    for p in realidad[clave]:
        if p["id"] in ids:
            gl, gv = marcadores[p["id"]]
            p["goles_local"], p["goles_visitante"] = gl, gv
            p["estado"] = "finished"
    guardar_json(REALIDAD_FILE, realidad)


def escribir_entrada(nombre, jornada, predicciones):
    guardar_json(ENTRADAS_DIR / f"J{jornada:02d}_{nombre}.json", {
        "participante": nombre,
        "jornada": jornada,
        "generado": datetime.now().isoformat(timespec="seconds"),
        "predicciones": predicciones,
    })


def pred(p, gl, gv, clave):
    return {"id": p["id"], "local": p["local"], "visitante": p["visitante"],
            "fecha": p["fecha"], "marcador": ofuscar_marcador(gl, gv, p["fecha"], clave)}


def correr(script):
    r = subprocess.run([sys.executable, str(RAIZ / "scripts" / script)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout, r.stderr)
        raise SystemExit(f"{script} falló")
    return r.stdout


def guardadas(slug_jugador, clave):
    datos = cargar_json(PARTICIPANTES_DIR / slug_jugador / "pronosticos" / f"{clave}.json")
    return {p["id"]: desofuscar_marcador(p["marcador"], p["fecha"], clave) for p in datos["predicciones"]}


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
    check(pau10["puntos_totales"] == 2, "un exacto vale 2 puntos (1X2 + exacto)")
    check(pau10["bonus_rendimiento"] == 0, "1 acierto no dispara bonus")
    check(all(not v["es_ganador_jornada"] and not v["es_perdedor_jornada"]
              for v in rep["J10"]["jugadores"].values()),
          "no se reparte ganador/perdedor con la jornada abierta")

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
    check(pau02["puntos_totales"] == 21, "9 exactos (18) + bonus 3 = 21, sin +1 de jornada")
    check(all(not v["es_ganador_jornada"] for v in j02rep["jugadores"].values()),
          "sin ganador de jornada mientras el aplazado no se juegue")

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
    check(pau["por_jornada"]["J10"]["puntos"] == 2,
          "la J10 mantiene los 2 puntos del adelantado")
    check(pau["puntos_totales"] == 28, "total = 26 (J02) + 2 (J10)")

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
