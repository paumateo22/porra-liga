"""Comprueba si hay ALGÚN partido en juego ahora mismo, mirando
data/resultados/realidad_oficial.json (que 05_extractor_sofascore.py debe
haber actualizado justo antes de llamar a este script).

Un partido "en juego" es cualquiera con estado distinto de "notstarted" (no
ha empezado) y de "finished" (ya terminó) — mismo criterio que ya usa
06_motor_puntuacion.py para decidir qué partidos son evaluables en directo.

Imprime "true" o "false" a stdout (nada más), pensado para leerse desde
bash con $(python scripts/hay_partido_en_juego.py).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import cargar_json, REALIDAD_FILE

ESTADO_FINALIZADO = "finished"
ESTADO_SIN_EMPEZAR = "notstarted"


def main():
    realidad = cargar_json(REALIDAD_FILE, {})
    for partidos in realidad.values():
        for p in partidos:
            estado = p.get("estado")
            if estado and estado not in (ESTADO_SIN_EMPEZAR, ESTADO_FINALIZADO):
                print("true")
                return 0
    print("false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
