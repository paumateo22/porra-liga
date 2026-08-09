"""03 — Buzón de pronósticos.

Lee los ficheros que sueltes en entradas/ (formato J02_Mateo.json), los valida
contra el calendario oficial y los archiva en:

    participantes/<slug>/pronosticos/J02.json

El fichero original se mueve a entradas/procesadas/. Los rechazados se quedan
en entradas/ para que puedas corregirlos.
"""
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import (
    CALENDARIO_FILE,
    ENTRADAS_DIR,
    PARTICIPANTES_FILE,
    PROCESADAS_DIR,
    REALIDAD_FILE,
    cargar_json,
    carpeta_participante,
    clave_jornada,
    guardar_json,
    slug,
)

PATRON_NOMBRE = re.compile(r"^J(\d{1,2})_(.+)$", re.IGNORECASE)


def registrar_participante(nombre):
    """Añade el jugador a config/participantes.json si es nuevo."""
    datos = cargar_json(PARTICIPANTES_FILE, {"participantes": []})
    existentes = {p["slug"] for p in datos["participantes"]}
    s = slug(nombre)
    if s not in existentes:
        datos["participantes"].append({
            "slug": s,
            "nombre": nombre.strip(),
            "alta": datetime.now().isoformat(timespec="seconds"),
        })
        datos["participantes"].sort(key=lambda p: p["slug"])
        guardar_json(PARTICIPANTES_FILE, datos)
        print(f"   👤 Nuevo participante registrado: {nombre.strip()} ({s})")
    return s


def validar(contenido, ruta, calendario):
    """Devuelve (ok, jornada, participante, predicciones_limpias, errores)."""
    errores = []

    participante = str(contenido.get("participante", "")).strip()
    if not participante:
        errores.append("falta el campo 'participante'")

    try:
        jornada = int(contenido.get("jornada"))
    except (TypeError, ValueError):
        errores.append("falta el campo 'jornada' o no es un número")
        return False, None, participante, [], errores

    clave = clave_jornada(jornada)
    if clave not in calendario:
        errores.append(f"la jornada {clave} no existe en el calendario")
        return False, jornada, participante, [], errores

    # Coherencia con el nombre del fichero (si sigue el patrón J02_Nombre)
    m = PATRON_NOMBRE.match(ruta.stem)
    if m and int(m.group(1)) != jornada:
        errores.append(
            f"el nombre del fichero dice J{int(m.group(1)):02d} pero dentro pone jornada {jornada}"
        )

    partidos_oficiales = {p["id"]: p for p in calendario[clave]}
    predicciones = contenido.get("predicciones") or []
    if not isinstance(predicciones, list) or not predicciones:
        errores.append("'predicciones' está vacío o no es una lista")
        return False, jornada, participante, [], errores

    limpias = []
    vistos = set()
    for i, pred in enumerate(predicciones):
        pid = pred.get("id")
        if pid not in partidos_oficiales:
            errores.append(f"predicción #{i + 1}: el partido id {pid} no es de {clave}")
            continue
        if pid in vistos:
            errores.append(f"predicción #{i + 1}: partido id {pid} duplicado")
            continue
        gl, gv = pred.get("goles_local"), pred.get("goles_visitante")
        if gl is None or gv is None:
            continue  # partido sin rellenar: se ignora sin ser error
        try:
            gl, gv = int(gl), int(gv)
        except (TypeError, ValueError):
            errores.append(f"predicción #{i + 1}: goles no numéricos")
            continue
        if gl < 0 or gv < 0 or gl > 30 or gv > 30:
            errores.append(f"predicción #{i + 1}: marcador fuera de rango ({gl}-{gv})")
            continue

        oficial = partidos_oficiales[pid]
        vistos.add(pid)
        limpias.append({
            "id": pid,
            "local": oficial["local"],
            "visitante": oficial["visitante"],
            "fecha": oficial["fecha"],
            "goles_local": gl,
            "goles_visitante": gv,
        })

    if not limpias:
        errores.append("no hay ninguna predicción válida")

    limpias.sort(key=lambda p: (p["fecha"] or "", p["local"]))
    return not errores, jornada, participante, limpias, errores


def cargar_bloqueados(clave, calendario, realidad):
    """Ids de partidos que ya no admiten cambios: empezados o con hora pasada."""
    ahora = datetime.now()
    estados = {p["id"]: p.get("estado") for p in realidad.get(clave, [])}
    bloqueados = set()
    for p in calendario.get(clave, []):
        estado = estados.get(p["id"])
        if estado and estado != "notstarted":
            bloqueados.add(p["id"])
            continue
        try:
            if p.get("fecha") and datetime.fromisoformat(p["fecha"]) <= ahora:
                bloqueados.add(p["id"])
        except ValueError:
            pass
    return bloqueados


def procesar_fichero(ruta, calendario, realidad, sin_cierre=False):
    try:
        contenido = cargar_json(ruta)
    except Exception as e:  # noqa: BLE001
        print(f"❌ {ruta.name}: no es un JSON válido ({e})")
        return False

    ok, jornada, participante, limpias, errores = validar(contenido, ruta, calendario)
    if not ok:
        print(f"❌ {ruta.name}: rechazado")
        for e in errores:
            print(f"      · {e}")
        return False

    clave = clave_jornada(jornada)
    s = registrar_participante(participante)
    destino = carpeta_participante(s) / "pronosticos" / f"{clave}.json"

    # Fusión: lo ya enviado manda en los partidos que ya han empezado.
    previo = cargar_json(destino, {})
    guardadas = {p["id"]: p for p in previo.get("predicciones", [])}
    bloqueados = set() if sin_cierre else cargar_bloqueados(clave, calendario, realidad)

    nuevas, actualizadas, rechazadas, conservadas = 0, 0, 0, 0
    for pred in limpias:
        pid = pred["id"]
        if pid in bloqueados:
            if pid in guardadas:
                conservadas += 1
                continue  # el partido ya se jugó: no se toca
            rechazadas += 1
            continue  # llega tarde y no había nada guardado
        if pid in guardadas:
            if (guardadas[pid]["goles_local"], guardadas[pid]["goles_visitante"]) != \
                    (pred["goles_local"], pred["goles_visitante"]):
                actualizadas += 1
        else:
            nuevas += 1
        guardadas[pid] = pred

    finales = sorted(guardadas.values(), key=lambda p: (p["fecha"] or "", p["local"]))
    if not finales:
        print(f"❌ {ruta.name}: no queda ninguna predicción válida tras aplicar el cierre.")
        return False

    guardar_json(destino, {
        "participante": s,
        "nombre": participante.strip(),
        "jornada": jornada,
        "generado": contenido.get("generado"),
        "ingerido": datetime.now().isoformat(timespec="seconds"),
        "predicciones": finales,
    })

    total_jornada = len(calendario[clave])
    print(f"✅ {participante.strip()} · {clave} → {len(finales)}/{total_jornada} partidos "
          f"({nuevas} nuevos, {actualizadas} corregidos, {conservadas} bloqueados, "
          f"{rechazadas} fuera de plazo)")

    PROCESADAS_DIR.mkdir(parents=True, exist_ok=True)
    sello = datetime.now().strftime("%Y%m%d-%H%M%S")
    shutil.move(str(ruta), str(PROCESADAS_DIR / f"{ruta.stem}_{sello}.json"))
    return True


def main():
    sin_cierre = "--sin-cierre" in sys.argv
    calendario = cargar_json(CALENDARIO_FILE, None)
    realidad = {} if sin_cierre else cargar_json(REALIDAD_FILE, {})
    ENTRADAS_DIR.mkdir(parents=True, exist_ok=True)

    if sin_cierre:
        print("⚠️  Modo --sin-cierre: se ignora el bloqueo por hora de partido.\n")

    ficheros = sorted(
        f for f in ENTRADAS_DIR.glob("*.json") if f.parent == ENTRADAS_DIR
    )
    if not ficheros:
        print("📭 No hay ficheros nuevos en entradas/")
        return 0

    print(f"📬 {len(ficheros)} fichero(s) en el buzón\n")
    ok = sum(procesar_fichero(f, calendario, realidad, sin_cierre) for f in ficheros)
    print(f"\n📊 {ok} ingerido(s), {len(ficheros) - ok} rechazado(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
