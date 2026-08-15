"""Laboratorio de escenarios de prueba — SOLO para desarrollo local.

Genera datos falsos que representan situaciones concretas difíciles de ver
con el simulador normal (99_simulador.py), para poder inspeccionarlas en la
web local sin esperar a que la temporada real llegue a ese punto.

    python simuladores/laboratorio.py

⚠️  Esto NO es parte del pipeline de producción. Borra participantes/,
entradas/, resultados y clasificación cada vez que generas un escenario —
NUNCA lo ejecutes sobre un checkout con pronósticos reales de tus amigos.
"""
import random
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(RAIZ))

from utils import (  # noqa: E402
    ANALISIS_DIR,
    CALENDARIO_FILE,
    CLASIFICACION_FILE,
    ENTRADAS_DIR,
    PARTICIPANTES_DIR,
    PARTICIPANTES_FILE,
    PROCESADAS_DIR,
    REALIDAD_FILE,
    REPORTES_DIR,
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

# Nombres claramente ficticios, para no chocar nunca con jugadores reales
# que tengas en config/nombres.txt o config/participantes.json.
JUGADORES = [
    ("Ana", 0.55, 0.95),    # (nombre, habilidad, constancia)
    ("Bruno", 0.48, 0.85),
    ("Clara", 0.50, 1.00),
    ("David", 0.44, 0.60),  # se deja jornadas a medias
    ("Elena", 0.52, 0.90),
]

N_JORNADAS = 38
AHORA = datetime.now()


# ───────────────────────── utilidades comunes ─────────────────────────

def limpiar_todo():
    for carpeta in (PARTICIPANTES_DIR, REPORTES_DIR, ANALISIS_DIR, PROCESADAS_DIR):
        if carpeta.exists():
            import shutil
            shutil.rmtree(carpeta)
        carpeta.mkdir(parents=True, exist_ok=True)
    for f in ENTRADAS_DIR.glob("*.json"):
        f.unlink()
    for f in (CALENDARIO_FILE, REALIDAD_FILE, CLASIFICACION_FILE):
        if f.exists():
            f.unlink()
    guardar_json(PARTICIPANTES_FILE, {"participantes": []})


def construir_calendario_base(n_jornadas, inicio):
    """Jornadas separadas 7 días entre sí a partir de 'inicio'."""
    calendario, pid = {}, 20000000
    for j in range(1, n_jornadas + 1):
        equipos = EQUIPOS[:]
        random.shuffle(equipos)
        partidos = []
        for i in range(0, len(equipos), 2):
            pid += 1
            fecha = inicio + timedelta(weeks=j - 1, hours=i)
            partidos.append({
                "id": pid, "local": equipos[i], "visitante": equipos[i + 1],
                "fecha": fecha.isoformat(timespec="seconds"),
            })
        calendario[clave_jornada(j)] = partidos
    return calendario


def derivar_realidad(calendario, ahora=AHORA):
    """Un partido está 'finished' si su fecha ya pasó, con marcador plausible.
    Recalcular esto tras mover fechas es lo que hace que un partido aplazado
    o adelantado quede automáticamente en el estado correcto."""
    realidad = {}
    for clave, partidos in calendario.items():
        filas = []
        for p in partidos:
            jugado = datetime.fromisoformat(p["fecha"]) < ahora
            filas.append({
                **p,
                "goles_local": random.randint(0, 4) if jugado else None,
                "goles_visitante": random.randint(0, 3) if jugado else None,
                "estado": "finished" if jugado else "notstarted",
            })
        realidad[clave] = filas
    return realidad


def generar_predicciones(calendario, realidad):
    """Predicciones de los 5 jugadores ficticios para TODO el calendario,
    coherentes con la habilidad de cada uno. Se escriben en entradas/ como
    si vinieran de pronosticar.html (en claro, tal como se guardan de verdad)."""
    for nombre, habilidad, constancia in JUGADORES:
        for clave, partidos in calendario.items():
            if random.random() > constancia + 0.3:
                continue  # jornada entera olvidada, típico de los inconstantes
            elegidos = partidos if random.random() < constancia else \
                random.sample(partidos, max(1, int(len(partidos) * 0.6)))

            predicciones = []
            for p in elegidos:
                if random.random() < habilidad:
                    gl, gv = random.randint(0, 3), random.randint(0, 2)
                else:
                    gl, gv = random.randint(0, 4), random.randint(0, 3)
                predicciones.append({**p, "goles_local": gl, "goles_visitante": gv})

            if predicciones:
                guardar_json(ENTRADAS_DIR / f"{clave}_{nombre}.json", {
                    "participante": nombre, "jornada": int(clave[1:]),
                    "generado": datetime.now().isoformat(timespec="seconds"),
                    "predicciones": predicciones,
                })


def ejecutar_pipeline():
    print("\n📬 Ingiriendo pronósticos y calculando puntuación...\n")
    # --sin-cierre: los escenarios generan pronósticos "ahora mismo" para
    # jornadas que ya han pasado (para poder ver una temporada a medias sin
    # esperar semanas). Sin este flag, la ingesta los rechazaría todos como
    # "fuera de plazo" — correcto en producción, pero no es lo que queremos
    # aquí: aquí se simula que esos pronósticos se mandaron a tiempo.
    r = subprocess.run([sys.executable, str(RAIZ / "scripts" / "03_ingesta_pronosticos.py"), "--sin-cierre"])
    if r.returncode != 0:
        print("⚠️  03_ingesta_pronosticos.py devolvió un error, revisa el mensaje de arriba.")
    r = subprocess.run([sys.executable, str(RAIZ / "scripts" / "06_motor_puntuacion.py")])
    if r.returncode != 0:
        print("⚠️  06_motor_puntuacion.py devolvió un error, revisa el mensaje de arriba.")


def ofrecer_abrir_web():
    respuesta = input("\n¿Abrir la web local ahora? (s/n): ").strip().lower()
    if respuesta == "s":
        from main import servidor_local
        servidor_local()


# ───────────────────────── escenarios ─────────────────────────

def escenario_temporada_a_medias():
    """38 jornadas, temporada empezada hace ~15 semanas: la mitad ya jugada,
    la otra mitad por delante. El caso normal de "estamos a mitad de liga"."""
    inicio = AHORA - timedelta(weeks=15)
    calendario = construir_calendario_base(N_JORNADAS, inicio)
    realidad = derivar_realidad(calendario)
    guardar_json(CALENDARIO_FILE, calendario)
    guardar_json(REALIDAD_FILE, realidad)
    generar_predicciones(calendario, realidad)
    jugadas = sum(1 for ps in realidad.values() for p in ps if p["estado"] == "finished")
    print(f"✅ Temporada a medias: {jugadas}/{N_JORNADAS * 10} partidos jugados.")


def escenario_jornada_a_medias():
    """Como la anterior, pero la jornada "actual" (la que toca ahora mismo)
    tiene exactamente 6 de sus 10 partidos ya jugados y 4 todavía no —
    ni jugada del todo ni sin empezar, justo a medias."""
    inicio = AHORA - timedelta(weeks=15)
    calendario = construir_calendario_base(N_JORNADAS, inicio)

    idx_actual = min(N_JORNADAS, max(1, (AHORA - inicio).days // 7 + 1))
    clave_actual = clave_jornada(idx_actual)
    partidos = calendario[clave_actual]
    random.shuffle(partidos)
    for p in partidos[:6]:
        p["fecha"] = (AHORA - timedelta(days=1)).isoformat(timespec="seconds")
    for p in partidos[6:]:
        p["fecha"] = (AHORA + timedelta(days=2)).isoformat(timespec="seconds")

    realidad = derivar_realidad(calendario)
    guardar_json(CALENDARIO_FILE, calendario)
    guardar_json(REALIDAD_FILE, realidad)
    generar_predicciones(calendario, realidad)
    print(f"✅ Jornada a medias: {clave_actual} tiene 6/10 partidos jugados y 4/10 pendientes.")


def escenario_jornada_partida_en_tiempo():
    """Una jornada (la 10) con partidos repartidos por todo el calendario:
    2 adelantados semanas antes, 6 en su fecha normal, 2 aplazados semanas
    después. La jornada se queda "abierta" mucho más tiempo del normal."""
    inicio = AHORA - timedelta(weeks=15)
    calendario = construir_calendario_base(N_JORNADAS, inicio)

    clave = clave_jornada(10)
    partidos = calendario[clave]
    random.shuffle(partidos)
    for p in partidos[:2]:
        p["fecha"] = (AHORA - timedelta(weeks=6)).isoformat(timespec="seconds")
    for p in partidos[8:]:
        p["fecha"] = (AHORA + timedelta(weeks=8)).isoformat(timespec="seconds")

    realidad = derivar_realidad(calendario)
    guardar_json(CALENDARIO_FILE, calendario)
    guardar_json(REALIDAD_FILE, realidad)
    generar_predicciones(calendario, realidad)
    print(f"✅ {clave} repartida en el tiempo: 2 adelantados hace 6 semanas, "
          f"6 en su fecha normal, 2 aplazados 8 semanas.")


def escenario_aplazados_repartidos():
    """Temporada a medias normal, pero con 5 partidos sueltos —repartidos por
    distintas jornadas, algunas ya jugadas y otras futuras— movidos fuera de
    su semana: para probar que varias jornadas pueden quedar "abiertas" a la
    vez por motivos distintos."""
    inicio = AHORA - timedelta(weeks=15)
    calendario = construir_calendario_base(N_JORNADAS, inicio)

    # 3 partidos de jornadas YA jugadas se aplazan mucho más adelante.
    for j in (4, 7, 12):
        p = random.choice(calendario[clave_jornada(j)])
        p["fecha"] = (AHORA + timedelta(weeks=random.randint(3, 10))).isoformat(timespec="seconds")

    # 2 partidos de jornadas TODAVÍA no jugadas se adelantan a ya mismo.
    for j in (20, 25):
        p = random.choice(calendario[clave_jornada(j)])
        p["fecha"] = (AHORA - timedelta(days=random.randint(1, 20))).isoformat(timespec="seconds")

    realidad = derivar_realidad(calendario)
    guardar_json(CALENDARIO_FILE, calendario)
    guardar_json(REALIDAD_FILE, realidad)
    generar_predicciones(calendario, realidad)
    print("✅ Temporada a medias con 5 partidos sueltos movidos de su jornada "
          "(J04, J07, J12 aplazados · J20, J25 adelantados).")


ESCENARIOS = [
    ("1", "Temporada a medias (mitad jugada, mitad por delante)", escenario_temporada_a_medias),
    ("2", "Jornada actual a medias (6 de 10 jugados, 4 pendientes)", escenario_jornada_a_medias),
    ("3", "Una jornada repartida en el tiempo (adelantados + aplazados dentro de ella)", escenario_jornada_partida_en_tiempo),
    ("4", "Temporada con varios partidos sueltos aplazados/adelantados", escenario_aplazados_repartidos),
]


def main():
    print("\n🧪  LABORATORIO DE ESCENARIOS DE PRUEBA (solo local)")
    print("⚠️  Esto borra participantes/, entradas/, resultados y clasificación")
    print("    actuales y los sustituye por datos de mentira con 5 jugadores")
    print("    ficticios (Ana, Bruno, Clara, David, Elena).\n")

    for tecla, etiqueta, _ in ESCENARIOS:
        print(f"  {tecla}. {etiqueta}")
    print("  0. Salir sin hacer nada")

    opcion = input("\n¿Qué escenario quieres ver? ").strip()
    elegido = next((e for e in ESCENARIOS if e[0] == opcion), None)
    if not elegido:
        print("Sin cambios.")
        return

    confirmacion = input(
        "⚠️  Se va a borrar todo lo que haya ahora mismo en participantes/, "
        "entradas/ y los resultados. ¿Seguro? (s/n): "
    ).strip().lower()
    if confirmacion != "s":
        print("Cancelado.")
        return

    random.seed()  # cada vez un escenario distinto, no siempre el mismo
    limpiar_todo()
    elegido[2]()
    ejecutar_pipeline()
    ofrecer_abrir_web()


if __name__ == "__main__":
    main()
