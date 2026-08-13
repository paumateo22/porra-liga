"""Elimina a un participante por completo — solo para el administrador.

Borra su carpeta de pronósticos/estadísticas y su ficha en
config/participantes.json. Con solo borrar la carpeta a mano NO basta: la
ficha del registro se queda, y esa persona sigue apareciendo en la
clasificación como un "fantasma" con 0 puntos en vez de desaparecer del
todo. Este script hace las dos cosas a la vez.

Tras usarlo, hay que volver a ejecutar el motor para que la clasificación,
el análisis y los informes se recalculen como si esa persona nunca hubiera
participado.

Uso:
    python scripts/eliminar_participante.py
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import PARTICIPANTES_DIR, PARTICIPANTES_FILE, cargar_json, guardar_json


def main():
    registro = cargar_json(PARTICIPANTES_FILE, {"participantes": []})
    participantes = registro["participantes"]

    if not participantes:
        print("No hay ningún participante registrado.")
        return

    print("\n👥 Participantes registrados:\n")
    for i, p in enumerate(participantes, 1):
        print(f"  {i}. {p['nombre']} ({p['slug']})")

    eleccion = input("\n¿A quién quieres eliminar? (número, Enter para cancelar): ").strip()
    if not eleccion:
        print("Cancelado.")
        return

    try:
        objetivo = participantes[int(eleccion) - 1]
    except (ValueError, IndexError):
        print("Número no válido.")
        return

    print(f"\n⚠️  Vas a eliminar a {objetivo['nombre']} ({objetivo['slug']}) POR COMPLETO:")
    print(f"   - Toda la carpeta participantes/{objetivo['slug']}/ (sus pronósticos guardados)")
    print(f"   - Su ficha en config/participantes.json")
    print("   Esto no se puede deshacer. Al recalcular, todo queda como si nunca hubiera participado.")

    confirmacion = input(f"\nEscribe su nombre exacto ({objetivo['nombre']}) para confirmar: ").strip()
    if confirmacion != objetivo["nombre"]:
        print("No coincide. Cancelado, no se ha borrado nada.")
        return

    carpeta = PARTICIPANTES_DIR / objetivo["slug"]
    if carpeta.exists():
        shutil.rmtree(carpeta)
        print(f"🗑️  Borrada participantes/{objetivo['slug']}/")
    else:
        print(f"   (no tenía carpeta participantes/{objetivo['slug']}/, no había nada que borrar ahí)")

    registro["participantes"] = [p for p in participantes if p["slug"] != objetivo["slug"]]
    guardar_json(PARTICIPANTES_FILE, registro)
    print("🗑️  Quitado del registro en config/participantes.json")

    print(f"\n✅ {objetivo['nombre']} eliminado por completo.")
    print("⚠️  Ahora ejecuta el motor para que la clasificación, el análisis y los")
    print("    informes se recalculen sin él/ella:")
    print("    python scripts/06_motor_puntuacion.py")
    print("\n   (Si tenía una insignia en config/nombres.txt, esa línea ya no hace nada,")
    print("    pero puedes borrarla a mano si quieres dejar el fichero limpio.)")


if __name__ == "__main__":
    main()
