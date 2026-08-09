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
    sin_jornada = 0
    for ev in eventos:
        p = ss.parsear_evento(ev)
        if not p["jornada"]:
            sin_jornada += 1
            continue
        clave = clave_jornada(p["jornada"])
        calendario.setdefault(clave, []).append({
            "id": p["id"],
            "local": p["local"],
            "visitante": p["visitante"],
            "id_escudo_local": p["id_escudo_local"],
            "id_escudo_visitante": p["id_escudo_visitante"],
            "fecha": p["fecha"],
        })

    for clave in calendario:
        calendario[clave].sort(key=lambda x: (x["fecha"] or "", x["local"]))

    ordenado = {c: calendario[c] for c in sorted(calendario, key=lambda k: int(k[1:]))}
    guardar_json(CALENDARIO_FILE, ordenado)

    total = sum(len(v) for v in ordenado.values())
    print(f"✅ {len(ordenado)} jornadas, {total} partidos -> {CALENDARIO_FILE.name}")
    if sin_jornada:
        print(f"   ⚠️  {sin_jornada} partidos descartados por no tener jornada asignada.")

    esperadas = settings["competicion"]["total_jornadas"]
    if len(ordenado) != esperadas:
        print(f"   ⚠️  Se esperaban {esperadas} jornadas. Puede que la temporada aún no esté completa.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
