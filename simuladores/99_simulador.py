"""99 — Simulador de desarrollo, en dos fases.

Respeta el orden real de los acontecimientos: primero se pronostica, después se
juegan los partidos. Así se prueba también el cierre por partido.

  Fase 1  python simuladores/99_simulador.py 5
          Calendario falso + resultados sin jugar + pronósticos en entradas/

          python main.py  ->  opción 2 (ingesta)

  Fase 2  python simuladores/99_simulador.py --jugar 3
          Marca las 3 primeras jornadas como jugadas

          python main.py  ->  opción 4 (motor)
"""
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from utils import (  # noqa: E402
    CALENDARIO_FILE,
    ENTRADAS_DIR,
    REALIDAD_FILE,
    cargar_json,
    clave_jornada,
    guardar_json,
)

EQUIPOS = [
    "Barcelona", "Real Madrid", "Atlético", "Athletic", "Real Sociedad",
    "Betis", "Villarreal", "Valencia", "Sevilla", "Celta",
    "Rayo", "Osasuna", "Getafe", "Girona", "Mallorca",
    "Alavés", "Espanyol", "Elche", "Levante", "Oviedo",
]

JUGADORES = ["Pau", "Aitor", "Javi", "Manu", "Álvaro"]
OCULTOS = Path(__file__).resolve().parent / "_resultados_simulados.json"


def preparar(n_jornadas):
    ahora = datetime.now()
    calendario, pid = {}, 14000000

    for j in range(1, n_jornadas + 1):
        equipos = EQUIPOS[:]
        random.shuffle(equipos)
        partidos = []
        for i in range(0, len(equipos), 2):
            pid += 1
            partidos.append({
                "id": pid,
                "local": equipos[i],
                "visitante": equipos[i + 1],
                # Todo en el futuro: nada está cerrado todavía.
                "fecha": (ahora + timedelta(days=7 * j, hours=i)).isoformat(timespec="seconds"),
            })
        calendario[clave_jornada(j)] = partidos

    # Un partido de la última jornada se ADELANTA a mañana.
    if n_jornadas >= 2:
        calendario[clave_jornada(n_jornadas)][0]["fecha"] = \
            (ahora + timedelta(days=1)).isoformat(timespec="seconds")

    guardar_json(CALENDARIO_FILE, calendario)
    guardar_json(REALIDAD_FILE, {
        c: [{**p, "goles_local": None, "goles_visitante": None, "estado": "notstarted"}
            for p in partidos]
        for c, partidos in calendario.items()
    })

    # Resultados que se revelarán en la fase 2.
    ocultos = {
        c: {str(p["id"]): [random.randint(0, 4), random.randint(0, 3)] for p in partidos}
        for c, partidos in calendario.items()
    }
    guardar_json(OCULTOS, ocultos)

    ENTRADAS_DIR.mkdir(parents=True, exist_ok=True)
    for j in range(1, n_jornadas + 1):
        clave = clave_jornada(j)
        for jugador in JUGADORES:
            partidos = calendario[clave]
            # Manu solo pronostica la mitad: debe quedar fuera de ganador/perdedor.
            if jugador == "Manu":
                partidos = partidos[:len(partidos) // 2]

            predicciones = []
            for p in partidos:
                real = ocultos[clave][str(p["id"])]
                # Pau acierta el 75%: debe disparar el bonus de rendimiento.
                if jugador == "Pau" and random.random() < 0.75:
                    gl, gv = real
                else:
                    gl, gv = random.randint(0, 4), random.randint(0, 3)
                predicciones.append({**p, "goles_local": gl, "goles_visitante": gv})

            guardar_json(ENTRADAS_DIR / f"{clave}_{jugador}.json", {
                "participante": jugador,
                "jornada": j,
                "generado": datetime.now().isoformat(timespec="seconds"),
                "predicciones": predicciones,
            })

    print(f"🎲 Fase 1 lista: {n_jornadas} jornadas, {len(JUGADORES)} jugadores, "
          f"nada jugado todavía.")
    print("   Siguiente: python main.py -> opción 2 (ingesta)")
    print(f"   Después:   python simuladores/99_simulador.py --jugar {min(3, n_jornadas)}")


def jugar(hasta_jornada):
    ocultos = cargar_json(OCULTOS, None)
    if not ocultos:
        print("❌ No hay simulación preparada. Ejecuta antes la fase 1.")
        return 1

    ahora = datetime.now()
    calendario = cargar_json(CALENDARIO_FILE)
    realidad = cargar_json(REALIDAD_FILE)
    ultima = clave_jornada(max(int(c[1:]) for c in calendario))
    jugados = 0

    for clave in calendario:
        adelantado = calendario[clave][0]["id"] if clave == ultima else None
        for i, p in enumerate(realidad[clave]):
            # Se juega si su jornada ya tocó, o si es el partido adelantado.
            if int(clave[1:]) > hasta_jornada and p["id"] != adelantado:
                continue
            gl, gv = ocultos[clave][str(p["id"])]
            p["goles_local"], p["goles_visitante"] = gl, gv
            p["estado"] = "finished"
            p["fecha"] = (ahora - timedelta(days=1, hours=i)).isoformat(timespec="seconds")
            calendario[clave][i]["fecha"] = p["fecha"]
            jugados += 1

    guardar_json(REALIDAD_FILE, realidad)
    guardar_json(CALENDARIO_FILE, calendario)
    print(f"⚽ Fase 2: {jugados} partidos marcados como jugados "
          f"(jornadas 1-{hasta_jornada} + el adelantado de la {ultima}).")
    print("   Siguiente: python main.py -> opción 4 (motor)")
    return 0


def main():
    args = sys.argv[1:]
    if args and args[0] == "--jugar":
        return jugar(int(args[1]) if len(args) > 1 else 3)

    random.seed(22)
    preparar(int(args[0]) if args else 38)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
