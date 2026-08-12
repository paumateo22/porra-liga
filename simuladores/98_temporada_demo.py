"""98 — Temporada de demostración con datos REALES de SofaScore.

Descarga una temporada ya terminada de LaLiga, la carga como si fuera la actual,
inventa 10 participantes y les genera pronósticos coherentes (no aleatorios puros:
cada jugador tiene su nivel, y los marcadores plausibles se ponderan según la
fuerza real de cada equipo esa temporada).

Sirve para ver la web llena de datos antes de que empiece la temporada de verdad.

    python simuladores/98_temporada_demo.py              # 25/26 completa
    python simuladores/98_temporada_demo.py 24/25        # otra temporada
    python simuladores/98_temporada_demo.py --hasta 19   # solo media temporada

Al terminar ejecuta el motor por su cuenta: la web queda lista.

⚠️  Sobrescribe config/calendario.json, los resultados y la carpeta participantes/.
"""
import random
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))

import sofascore as ss  # noqa: E402
from utils import (  # noqa: E402
    ANALISIS_DIR,
    CALENDARIO_FILE,
    PARTICIPANTES_DIR,
    PARTICIPANTES_FILE,
    REALIDAD_FILE,
    REPORTES_DIR,
    cargar_settings,
    clave_jornada,
    guardar_json,
    ofuscar_marcador,
    signo,
    slug,
)

# Nombre y nivel de cada jugador. La habilidad es la probabilidad de acertar el
# 1X2 antes de aplicar la dificultad real del partido.
JUGADORES = [
    ("Pau",     0.52, 0.95),   # (nombre, habilidad, constancia)
    ("Aitor",   0.47, 0.90),
    ("Javi",    0.44, 1.00),
    ("Manu",    0.41, 0.55),   # se deja jornadas a medias
    ("Álvaro",  0.43, 0.85),
    ("Marta",   0.50, 0.92),
    ("Nerea",   0.39, 0.80),
    ("Dani",    0.36, 0.98),
    ("Sergio",  0.45, 0.70),
    ("Lucía",   0.42, 0.88),
]

# Marcadores plausibles por resultado, con su peso relativo en LaLiga.
MARCADORES = {
    "1": [((1, 0), 26), ((2, 0), 20), ((2, 1), 18), ((3, 0), 9),
          ((3, 1), 8), ((4, 0), 3), ((3, 2), 4), ((4, 1), 3)],
    "X": [((0, 0), 30), ((1, 1), 42), ((2, 2), 20), ((3, 3), 4)],
    "2": [((0, 1), 26), ((0, 2), 20), ((1, 2), 18), ((0, 3), 9),
          ((1, 3), 8), ((2, 3), 4), ((1, 4), 3), ((0, 4), 3)],
}


def descargar(etiqueta):
    settings = cargar_settings()
    torneo = settings["competicion"]["sofascore_unique_tournament_id"]
    sesion = ss.crear_sesion()

    print(f"🔎 Buscando la temporada {etiqueta} de LaLiga...")
    season_id, temporadas = ss.resolver_season_id(sesion, torneo, etiqueta)
    if not season_id:
        print("❌ No encontrada. Disponibles:")
        for t in temporadas[:12]:
            print(f"   - {t.get('year')}  ->  id {t.get('id')}")
        raise SystemExit(1)

    print(f"📥 Descargando partidos (season_id {season_id})...")
    eventos = ss.descargar_eventos(sesion, torneo, season_id)
    if not eventos:
        raise SystemExit("❌ SofaScore no devolvió partidos.")

    calendario, realidad = {}, {}
    for ev in eventos:
        p = ss.parsear_evento(ev)
        if not p["jornada"]:
            continue
        clave = clave_jornada(p["jornada"])
        calendario.setdefault(clave, []).append({
            "id": p["id"], "local": p["local"],
            "visitante": p["visitante"], "fecha": p["fecha"],
            "id_escudo_local": p["id_escudo_local"],
            "id_escudo_visitante": p["id_escudo_visitante"],
        })
        realidad.setdefault(clave, []).append({
            "id": p["id"], "local": p["local"], "visitante": p["visitante"],
            "fecha": p["fecha"], "goles_local": p["goles_local"],
            "goles_visitante": p["goles_visitante"], "estado": p["estado"],
            "id_escudo_local": p["id_escudo_local"],
            "id_escudo_visitante": p["id_escudo_visitante"],
        })

    orden = lambda d: {c: sorted(d[c], key=lambda x: (x["fecha"] or "", x["local"]))
                       for c in sorted(d, key=lambda k: int(k[1:]))}
    return orden(calendario), orden(realidad)


def calcular_fuerzas(realidad):
    """Puntos reales por equipo: sirve para que los fallos sean plausibles."""
    puntos = {}
    for partidos in realidad.values():
        for p in partidos:
            if p["estado"] != "finished":
                continue
            s = signo(p["goles_local"], p["goles_visitante"])
            puntos.setdefault(p["local"], 0)
            puntos.setdefault(p["visitante"], 0)
            if s == "1":
                puntos[p["local"]] += 3
            elif s == "2":
                puntos[p["visitante"]] += 3
            else:
                puntos[p["local"]] += 1
                puntos[p["visitante"]] += 1
    if not puntos:
        return {}
    maximo = max(puntos.values()) or 1
    return {e: v / maximo for e, v in puntos.items()}


def signo_plausible(local, visitante, fuerzas, evitar):
    """Elige un 1X2 distinto del real, ponderado por la fuerza de los equipos."""
    fl = fuerzas.get(local, 0.5) + 0.15   # ventaja de campo
    fv = fuerzas.get(visitante, 0.5)
    pesos = {"1": fl * 2.2, "X": 1.0, "2": fv * 2.0}
    pesos.pop(evitar, None)
    opciones = list(pesos)
    return random.choices(opciones, weights=[pesos[o] for o in opciones])[0]


def marcador_para(resultado):
    tabla = [m for m in MARCADORES[resultado] if m[1] > 0]
    return random.choices([m[0] for m in tabla], weights=[m[1] for m in tabla])[0]


def generar_pronostico(partido, real, habilidad, fuerzas):
    """Devuelve (goles_local, goles_visitante) coherentes con el nivel del jugador."""
    real_signo = signo(real["goles_local"], real["goles_visitante"])
    if real_signo is None:
        return None

    # Los partidos entre equipos parejos son más difíciles de acertar.
    fl = fuerzas.get(partido["local"], 0.5) + 0.15
    fv = fuerzas.get(partido["visitante"], 0.5)
    claridad = min(abs(fl - fv) * 1.6, 0.35)
    prob = min(habilidad + claridad * 0.5, 0.70)

    if random.random() < prob:
        elegido = real_signo
        # Muy de vez en cuando alguien "ve" el marcador entero. El resto de
        # exactos salen por coincidencia al elegir un marcador plausible.
        if random.random() < 0.05:
            return real["goles_local"], real["goles_visitante"]
    else:
        elegido = signo_plausible(partido["local"], partido["visitante"], fuerzas, real_signo)

    return marcador_para(elegido)


def generar_participantes(calendario, realidad, hasta_jornada):
    fuerzas = calcular_fuerzas(realidad)
    registro = []
    total_preds = 0

    for nombre, habilidad, constancia in JUGADORES:
        s = slug(nombre)
        carpeta = PARTICIPANTES_DIR / s / "pronosticos"
        carpeta.mkdir(parents=True, exist_ok=True)

        # Alguno entra con la temporada empezada.
        primera = 1
        if nombre in ("Lucía", "Sergio"):
            primera = random.randint(3, 6)

        for clave in calendario:
            j = int(clave[1:])
            if j < primera or j > hasta_jornada:
                continue

            reales = {p["id"]: p for p in realidad[clave]}
            partidos = calendario[clave]

            # Jornada olvidada del todo (poco frecuente salvo en los inconstantes).
            if random.random() > constancia + 0.35:
                continue
            # A veces se deja partidos sin rellenar.
            if random.random() > constancia:
                partidos = random.sample(partidos, random.randint(4, len(partidos) - 1))

            predicciones = []
            for p in partidos:
                real = reales.get(p["id"])
                if not real:
                    continue
                resultado = generar_pronostico(p, real, habilidad, fuerzas)
                if resultado is None:
                    continue
                gl, gv = resultado
                predicciones.append({
                    "id": p["id"], "local": p["local"], "visitante": p["visitante"],
                    "fecha": p["fecha"], "marcador": ofuscar_marcador(gl, gv, p["fecha"], clave),
                })

            if not predicciones:
                continue

            predicciones.sort(key=lambda x: (x["fecha"] or "", x["local"]))
            guardar_json(carpeta / f"{clave}.json", {
                "participante": s,
                "nombre": nombre,
                "jornada": j,
                "generado": predicciones[0]["fecha"],
                "ingerido": datetime.now().isoformat(timespec="seconds"),
                "predicciones": predicciones,
            })
            total_preds += len(predicciones)

        registro.append({
            "slug": s,
            "nombre": nombre,
            "alta": calendario[clave_jornada(primera)][0]["fecha"],
        })

    registro.sort(key=lambda r: r["slug"])
    guardar_json(PARTICIPANTES_FILE, {"participantes": registro})
    return total_preds


def main():
    args = [a for a in sys.argv[1:]]
    hasta = 38
    if "--hasta" in args:
        i = args.index("--hasta")
        hasta = int(args[i + 1])
        args = args[:i] + args[i + 2:]
    etiqueta = args[0] if args else "25/26"

    random.seed(2026)

    calendario, realidad = descargar(etiqueta)
    guardar_json(CALENDARIO_FILE, calendario)
    guardar_json(REALIDAD_FILE, realidad)

    jugados = sum(1 for ps in realidad.values() for p in ps if p["estado"] == "finished")
    total = sum(len(v) for v in realidad.values())
    print(f"✅ {len(calendario)} jornadas · {total} partidos · {jugados} finalizados")

    # Borrón y cuenta nueva en los datos derivados.
    for carpeta in (PARTICIPANTES_DIR, REPORTES_DIR, ANALISIS_DIR):
        if carpeta.exists():
            shutil.rmtree(carpeta)
        carpeta.mkdir(parents=True)

    print(f"🎲 Generando pronósticos de {len(JUGADORES)} jugadores hasta la J{hasta:02d}...")
    n = generar_participantes(calendario, realidad, hasta)
    print(f"✅ {n} pronósticos escritos en participantes/")

    print("\n🧮 Ejecutando el motor de puntuación...\n")
    subprocess.run([sys.executable, str(RAIZ / "scripts" / "06_motor_puntuacion.py")], check=True)
    print("\n🌐 Listo. Abre index.html para ver la web con datos reales.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
