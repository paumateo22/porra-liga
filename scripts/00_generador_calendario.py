"""00 — Genera config/calendario.json (38 jornadas de LaLiga con id de SofaScore).

Resuelve el season_id automáticamente la primera vez y lo escribe en
config/settings.json para no volver a buscarlo.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sofascore as ss
from utils import (
    CALENDARIO_FILE,
    SETTINGS_FILE,
    cargar_settings,
    clave_jornada,
    guardar_json,
)

ETIQUETA_TEMPORADA = "26/27"


def main():
    settings = cargar_settings()
    comp = settings["competicion"]
    torneo_id = comp["sofascore_unique_tournament_id"]
    season_id = comp.get("sofascore_season_id")

    sesion = ss.crear_sesion()

    if not season_id:
        print(f"🔎 Resolviendo season_id de {ETIQUETA_TEMPORADA}...")
        season_id, temporadas = ss.resolver_season_id(sesion, torneo_id, ETIQUETA_TEMPORADA)
        if not season_id:
            print("❌ No se encontró la temporada. Disponibles:")
            for t in temporadas[:10]:
                print(f"   - {t.get('year')}  ->  id {t.get('id')}")
            print("   Escribe el id a mano en config/settings.json y vuelve a ejecutar.")
            return 1
        comp["sofascore_season_id"] = season_id
        guardar_json(SETTINGS_FILE, settings)
        print(f"✅ season_id = {season_id} (guardado en settings.json)")

    print(f"📥 Descargando calendario (torneo {torneo_id}, temporada {season_id})...")
    eventos = ss.descargar_eventos(sesion, torneo_id, season_id)
    if not eventos:
        print("❌ SofaScore no devolvió partidos.")
        return 1

    calendario = {}
    sin_jornada = []
    for ev in eventos:
        p = ss.parsear_evento(ev)
        if not p["jornada"]:
            sin_jornada.append(p)
            continue
        clave = clave_jornada(p["jornada"])
        calendario.setdefault(clave, []).append(p)

    # descargar_eventos() ya deduplica por id (dos peticiones que devuelvan el
    # mismo evento no producen dos entradas) — pero un mismo partido puede
    # aparecer con DOS ids distintos si SofaScore lo reprogramó: el evento
    # viejo se queda "fantasma" en la respuesta junto al nuevo, ambos con el
    # mismo par de equipos y a veces la misma jornada. Eso es lo que produce
    # un "11 partidos, con un X-Y duplicado" en vez de 10. Aquí se detecta
    # por (jornada, local, visitante) y, si hay colisión, se conserva el id
    # más alto (el creado más tarde — normalmente el partido reprogramado de
    # verdad) y se avisa bien claro de los dos ids implicados, para poder
    # revisarlo a mano si el criterio se equivoca.
    for clave, partidos in calendario.items():
        vistos = {}
        for p in partidos:
            fixture = (p["local"], p["visitante"])
            if fixture in vistos:
                anterior = vistos[fixture]
                descartado, conservado = sorted([anterior, p], key=lambda x: x["id"])
                print(f"   ⚠️  {clave}: {descartado['local']} - {descartado['visitante']} aparece dos veces "
                      f"(ids {descartado['id']} y {conservado['id']}) — se conserva el id {conservado['id']} "
                      f"(el más reciente) y se descarta el {descartado['id']}.")
                vistos[fixture] = conservado
            else:
                vistos[fixture] = p
        calendario[clave] = list(vistos.values())

    ordenado_final = {}
    for clave in calendario:
        ordenado_final[clave] = sorted(
            [{
                "id": p["id"], "local": p["local"], "visitante": p["visitante"],
                "id_escudo_local": p["id_escudo_local"], "id_escudo_visitante": p["id_escudo_visitante"],
                "fecha": p["fecha"],
            } for p in calendario[clave]],
            key=lambda x: (x["fecha"] or "", x["local"]),
        )

    ordenado = {c: ordenado_final[c] for c in sorted(ordenado_final, key=lambda k: int(k[1:]))}
    guardar_json(CALENDARIO_FILE, ordenado)

    total = sum(len(v) for v in ordenado.values())
    print(f"✅ {len(ordenado)} jornadas, {total} partidos -> {CALENDARIO_FILE.name}")

    # Cuántos partidos tiene cada jornada — para detectar de un vistazo una
    # jornada corta (como la J6 con 9 en vez de 10) sin tener que abrir el
    # JSON a mano. Solo se imprime si alguna se sale del número esperado.
    por_jornada = settings["competicion"].get("partidos_por_jornada", 10)
    irregulares = {c: len(v) for c, v in ordenado.items() if len(v) != por_jornada}
    if irregulares:
        print(f"   ⚠️  Jornadas con un número de partidos distinto de {por_jornada}:")
        for c, n in irregulares.items():
            print(f"      - {c}: {n} partidos")

    if sin_jornada:
        print(f"   ⚠️  {len(sin_jornada)} partido(s) descartados por no tener jornada asignada:")
        for p in sin_jornada:
            print(f"      - id {p['id']}: {p['local']} - {p['visitante']} ({p['fecha'] or 'sin fecha'})")

    esperadas = settings["competicion"]["total_jornadas"]
    if len(ordenado) != esperadas:
        print(f"   ⚠️  Se esperaban {esperadas} jornadas. Puede que la temporada aún no esté completa.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
