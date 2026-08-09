"""Reseteo de temporada: limpia todos los datos generados y descarga el
calendario oficial de LaLiga desde SofaScore, en un solo comando.

Escrito en Python a propósito: 'rm -rf' es de bash y no existe en PowerShell,
así que este script funciona igual en Windows, Mac o Linux.

    python reset.py
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))
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
)


def limpiar():
    print("🧹 Borrando datos generados...")

    for carpeta in (PARTICIPANTES_DIR, REPORTES_DIR, ANALISIS_DIR, PROCESADAS_DIR):
        if carpeta.exists():
            shutil.rmtree(carpeta)
        carpeta.mkdir(parents=True, exist_ok=True)
        (carpeta / ".gitkeep").touch()

    for f in ENTRADAS_DIR.glob("*.json"):
        f.unlink()

    for f in (CALENDARIO_FILE, REALIDAD_FILE, CLASIFICACION_FILE):
        if f.exists():
            f.unlink()

    json.dump({"participantes": []}, open(PARTICIPANTES_FILE, "w"), indent=4)

    print("✅ Todo limpio: sin jugadores, sin pronósticos, sin resultados.")


def descargar_calendario():
    print("\n📅 Descargando el calendario de la temporada desde SofaScore...\n")
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "00_generador_calendario.py")])
    if r.returncode != 0:
        print("\n⚠️  El calendario no se pudo descargar. Puedes reintentarlo con:")
        print("    python scripts/00_generador_calendario.py")


def main():
    limpiar()
    descargar_calendario()
    print("\n🚀 Listo para empezar la temporada.")
    print("   Siguiente: python main.py -> opción 6, para verla en el navegador.")


if __name__ == "__main__":
    main()
