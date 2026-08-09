"""Gestión de distintivos de jugadores (🏆, ⭐, ...) — solo para el administrador.

Un distintivo es un emoji que acompaña al nombre del jugador en TODA la web
(clasificación, análisis, perfil, carrera, participantes). Se guarda en
config/participantes.json y el motor de puntuación lo copia a
data/clasificacion.json y a data/analisis/*.json en cada ejecución.

También permite dar de alta a alguien por adelantado, aunque todavía no haya
mandado ningún pronóstico — útil para dejarle puesto el distintivo desde
antes de que empiece a jugar.

Uso:
    python scripts/gestionar_distintivos.py

Después de cualquier cambio hay que volver a ejecutar el motor para que se
vea en la web:
    python scripts/06_motor_puntuacion.py
"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import PARTICIPANTES_FILE, cargar_json, guardar_json, slug


def mostrar_lista(participantes):
    print("\n🏅 Participantes y distintivos actuales:\n")
    if not participantes:
        print("   (todavía no hay ningún participante registrado)")
        return
    for i, p in enumerate(participantes, 1):
        marca = p.get("distintivo") or "—"
        print(f"   {i}. {p['nombre']:<20} {marca}")


def elegir(participantes):
    for i, p in enumerate(participantes, 1):
        print(f"  {i}. {p['nombre']}")
    try:
        idx = int(input("¿Cuál? (número): ").strip()) - 1
    except ValueError:
        return None
    if 0 <= idx < len(participantes):
        return idx
    print("Número fuera de rango.")
    return None


def main():
    datos = cargar_json(PARTICIPANTES_FILE, {"participantes": []})
    participantes = datos["participantes"]

    mostrar_lista(participantes)

    print("\n1. Asignar/cambiar distintivo a alguien que ya está en la lista")
    print("2. Dar de alta a alguien nuevo con distintivo (aunque no haya pronosticado nada)")
    print("3. Quitar el distintivo a alguien")
    print("0. Salir sin cambios")
    opcion = input("\nElige una opción: ").strip()

    cambiado = False

    if opcion in ("1", "3"):
        if not participantes:
            print("No hay nadie registrado todavía. Usa la opción 2.")
            return
        idx = elegir(participantes)
        if idx is None:
            return
        if opcion == "1":
            emoji = input("Distintivo (pega un emoji, ej. 🏆 o ⭐): ").strip()
            participantes[idx]["distintivo"] = emoji
            print(f"✅ {participantes[idx]['nombre']} ahora lleva {emoji or '(sin distintivo)'}")
        else:
            participantes[idx]["distintivo"] = ""
            print(f"✅ Distintivo quitado a {participantes[idx]['nombre']}")
        cambiado = True

    elif opcion == "2":
        nombre = input("Nombre del nuevo participante (tal cual debe aparecer): ").strip()
        if not nombre:
            print("Nombre vacío, cancelado.")
            return
        s = slug(nombre)
        if any(p["slug"] == s for p in participantes):
            print(f"❌ Ya existe un participante con ese nombre (o muy parecido): {s}")
            return
        emoji = input("Distintivo (opcional, Enter para no poner ninguno): ").strip()
        participantes.append({
            "slug": s,
            "nombre": nombre,
            "alta": datetime.now().isoformat(timespec="seconds"),
            "distintivo": emoji,
        })
        print(f"✅ {nombre} dado de alta" + (f" con {emoji}" if emoji else ", sin distintivo") + ".")
        print("   Cuando mande su primer pronóstico, usa exactamente este mismo nombre.")
        cambiado = True

    else:
        print("Sin cambios.")
        return

    if cambiado:
        participantes.sort(key=lambda p: p["slug"])
        guardar_json(PARTICIPANTES_FILE, {"participantes": participantes})
        print("\n⚠️  Para que se vea en la web, ejecuta ahora:")
        print("    python scripts/06_motor_puntuacion.py")


if __name__ == "__main__":
    main()
