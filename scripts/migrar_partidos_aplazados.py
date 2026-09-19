"""Detecta partidos que han cambiado de ID entre dos calendarios (mismo par
de equipos, misma jornada, ID distinto — el síntoma real de un partido
aplazado al que SofaScore le reasigna el ID) y migra los pronósticos
afectados automáticamente, sin preguntar nada. Pensado para vivir en el
workflow que corre a menudo (cron_sofascore.yml).

Por qué es seguro hacerlo sin confirmación humana: la señal usada (mismo
par local/visitante EXACTO, dentro de la MISMA jornada) es muy específica
— dos equipos solo se enfrentan una vez por jornada, así que la
probabilidad de una coincidencia falsa es prácticamente nula. Cada
migración se imprime con detalle en la consola, así que queda reflejada en
el propio registro de la ejecución del workflow.

El pronóstico de cada participante se busca en dos sitios, por este orden:
  1. Su fichero oficial ya guardado (participantes/<slug>/pronosticos/<jornada>.json)
     — el caso normal: se guardó bien con el ID viejo antes del
     aplazamiento, solo hace falta llevarlo al ID nuevo.
  2. Si no está ahí, se busca en entradas/procesadas/ y entradas/rechazados/
     — por si un envío con el ID viejo llegó a archivarse pero nunca llegó
     a guardarse en el fichero oficial (por ejemplo, si ese envío se
     rechazó por completo por arrastrar también este partido con un ID que
     ya no era válido en ese momento).

Uso:
    Automático, para el workflow (sin preguntar nada):
        python scripts/migrar_partidos_aplazados.py --auto RUTA_ANTES RUTA_DESPUES

    Manual, para un caso puntual (pide confirmación):
        python scripts/migrar_partidos_aplazados.py ID_VIEJO ID_NUEVO
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import (
    cargar_json, guardar_json, PARTICIPANTES_DIR, CALENDARIO_FILE,
    ENTRADAS_DIR, PROCESADAS_DIR, listar_participantes, slug,
)

RECHAZADOS_DIR = ENTRADAS_DIR / "rechazados"


def buscar_partido_en_calendario(calendario, id_partido):
    for clave, partidos in calendario.items():
        for p in partidos:
            if p["id"] == id_partido:
                return clave, p
    return None, None


def buscar_en_archivos(id_viejo, clave):
    """Busca en entradas/procesadas/ y entradas/rechazados/ ficheros de esa
    jornada que contengan una predicción para id_viejo. Devuelve
    {slug: (goles_local, goles_visitante)}."""
    encontrados = {}
    numero = int(clave[1:])
    for carpeta in (PROCESADAS_DIR, RECHAZADOS_DIR):
        if not carpeta.exists():
            continue
        for ruta in sorted(carpeta.glob(f"J{numero:02d}_*.json")):
            try:
                datos = json.loads(ruta.read_text(encoding="utf-8"))
            except Exception:
                continue
            participante = datos.get("participante")
            if not participante:
                continue
            for p in datos.get("predicciones", []):
                if p.get("id") == id_viejo and p.get("goles_local") is not None:
                    encontrados[slug(participante)] = (p["goles_local"], p["goles_visitante"])
    return encontrados


def migrar_partido(id_viejo, id_nuevo, calendario=None):
    """Migra (o rescata) el pronóstico de id_viejo a id_nuevo para todos los
    participantes que tengan algo que migrar. Devuelve
    (clave, partido_nuevo, [(slug, marcador, origen), ...])."""
    if calendario is None:
        calendario = cargar_json(CALENDARIO_FILE, {})

    clave, partido_nuevo = buscar_partido_en_calendario(calendario, id_nuevo)
    if not partido_nuevo:
        return None, None, []

    rescatados = buscar_en_archivos(id_viejo, clave)
    cambios = []

    for p in listar_participantes():
        s = p["slug"]
        ruta = PARTICIPANTES_DIR / s / "pronosticos" / f"{clave}.json"
        datos = cargar_json(ruta, {
            "participante": p["nombre"], "jornada": int(clave[1:]),
            "generado": None, "predicciones": [],
        })
        predicciones = datos.get("predicciones", [])

        if any(x["id"] == id_nuevo for x in predicciones):
            continue  # ya migrado antes, o ya pronosticado directo con el ID nuevo

        entrada_vieja = next((x for x in predicciones if x["id"] == id_viejo), None)
        if entrada_vieja:
            gl, gv = entrada_vieja["goles_local"], entrada_vieja["goles_visitante"]
            origen = "fichero oficial"
        elif s in rescatados:
            gl, gv = rescatados[s]
            origen = "rescatado de un envío archivado"
        else:
            continue  # este participante no tenía nada que migrar para este partido

        nueva_entrada = {
            "id": id_nuevo, "local": partido_nuevo["local"], "visitante": partido_nuevo["visitante"],
            "fecha": partido_nuevo["fecha"], "goles_local": gl, "goles_visitante": gv,
        }
        datos["predicciones"] = [x for x in predicciones if x["id"] != id_viejo] + [nueva_entrada]
        guardar_json(ruta, datos)
        cambios.append((s, f"{gl}-{gv}", origen))

    return clave, partido_nuevo, cambios


def detectar_candidatos(antes, despues):
    """[(id_viejo, id_nuevo, local, visitante, clave), ...] — partidos que
    han cambiado de ID dentro de la misma jornada."""
    candidatos = []
    for clave, partidos_despues in despues.items():
        partidos_antes = antes.get(clave, [])
        ids_antes = {p["id"]: p for p in partidos_antes}
        ids_despues = {p["id"]: p for p in partidos_despues}

        desaparecidos = [p for pid, p in ids_antes.items() if pid not in ids_despues]
        nuevos = [p for pid, p in ids_despues.items() if pid not in ids_antes]

        for viejo in desaparecidos:
            for nuevo in nuevos:
                if viejo["local"] == nuevo["local"] and viejo["visitante"] == nuevo["visitante"]:
                    candidatos.append((viejo["id"], nuevo["id"], viejo["local"], viejo["visitante"], clave))
                    break

    return candidatos


def modo_automatico(ruta_antes, ruta_despues):
    antes = cargar_json(ruta_antes, None)
    despues = cargar_json(ruta_despues, None)

    if antes is None:
        print("No había un calendario previo con el que comparar (primera vez) — nada que detectar.")
        return 0
    if despues is None:
        print("No se encuentra el calendario regenerado — algo ha ido mal antes de llegar aquí.")
        return 1

    candidatos = detectar_candidatos(antes, despues)
    if not candidatos:
        print("Sin cambios de ID detectados en ningún partido.")
        return 0

    print(f"Detectado(s) {len(candidatos)} partido(s) con ID cambiado (probable aplazamiento):\n")
    for id_viejo, id_nuevo, local, visitante, clave in candidatos:
        print(f"  {clave}: {local} - {visitante}  (ID {id_viejo} -> {id_nuevo})")
        _, partido_nuevo, cambios = migrar_partido(id_viejo, id_nuevo, despues)
        if not cambios:
            print("    Nadie tenía nada que migrar para este partido.")
            continue
        for s, marcador, origen in cambios:
            print(f"    {s}: {marcador} ({origen}), abierto hasta {partido_nuevo['fecha']}")
    return 0


def modo_manual(id_viejo, id_nuevo):
    calendario = cargar_json(CALENDARIO_FILE, {})
    clave, partido_nuevo = buscar_partido_en_calendario(calendario, id_nuevo)
    if not partido_nuevo:
        print(f"El ID nuevo ({id_nuevo}) no aparece en config/calendario.json — "
              "asegúrate de haber regenerado el calendario primero (script 00).")
        return 1

    print(f"Partido: {partido_nuevo['local']} - {partido_nuevo['visitante']} "
          f"en {clave} ({partido_nuevo['fecha']})")
    if input("\n¿Aplicar la migración? [s/N] ").strip().lower() != "s":
        print("Cancelado, no se ha tocado nada.")
        return 0

    _, _, cambios = migrar_partido(id_viejo, id_nuevo, calendario)
    if not cambios:
        print("Nadie tenía nada que migrar para este partido.")
        return 0
    for s, marcador, origen in cambios:
        print(f"  {s}: {marcador} ({origen})")
    print(f"\nListo — {len(cambios)} pronóstico(s) migrado(s), "
          f"abiertos a cambio hasta {partido_nuevo['fecha']}.")
    return 0


def main():
    if len(sys.argv) == 4 and sys.argv[1] == "--auto":
        return modo_automatico(sys.argv[2], sys.argv[3])
    if len(sys.argv) == 3:
        try:
            return modo_manual(int(sys.argv[1]), int(sys.argv[2]))
        except ValueError:
            pass
    print("Uso:")
    print("  Automático: python scripts/migrar_partidos_aplazados.py --auto RUTA_ANTES RUTA_DESPUES")
    print("  Manual:     python scripts/migrar_partidos_aplazados.py ID_VIEJO ID_NUEVO")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
