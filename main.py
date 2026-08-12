import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts"

MENU = [
    ("1", "📅 Regenerar calendario desde SofaScore (00)", [SCRIPTS / "00_generador_calendario.py"]),
    ("2", "📬 Ingerir pronósticos del buzón entradas/ (03)", [SCRIPTS / "03_ingesta_pronosticos.py"]),
    ("3", "📥 Actualizar resultados reales SofaScore (05)", [SCRIPTS / "05_extractor_sofascore.py"]),
    ("4", "🧮 Ejecutar motor de puntuación (06)", [SCRIPTS / "06_motor_puntuacion.py"]),
    ("5", "⚡ ACTUALIZACIÓN TOTAL (03 + 05 + 06)",
     [SCRIPTS / "03_ingesta_pronosticos.py",
      SCRIPTS / "05_extractor_sofascore.py",
      SCRIPTS / "06_motor_puntuacion.py"]),
    ("7", "🌍 Temporada demo con datos REALES de SofaScore (98)",
     [ROOT / "simuladores" / "98_temporada_demo.py"]),
    ("8", "🧪 Test de casos límite (adelantados, aplazados, reenvíos)",
     [ROOT / "tests" / "test_casos_limite.py"]),
    ("9", "🎲 Simulador — fase 1: preparar datos falsos",
     [ROOT / "simuladores" / "99_simulador.py"]),
    ("p", "🧪 Laboratorio de escenarios de prueba (temporada/jornada a medias...)",
     [ROOT / "simuladores" / "laboratorio.py"]),
    ("r", "🧹 RESETEAR TODO + descargar calendario (inicio de temporada)",
     [ROOT / "reset.py"]),
]


def servidor_local():
    import http.server
    import socketserver
    import webbrowser

    class HandlerSinCache(http.server.SimpleHTTPRequestHandler):
        """Igual que el handler estándar, pero desactivando el caché del
        navegador. Sin esto, el navegador puede seguir sirviendo una versión
        vieja de theme.css/layout.js aunque el fichero en disco ya haya
        cambiado, y hace falta un Ctrl+Shift+R para verlo — mejor que nunca
        haga falta."""

        def end_headers(self):
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            super().end_headers()

    puerto = 8000
    os.chdir(ROOT)
    try:
        with socketserver.TCPServer(("", puerto), HandlerSinCache) as httpd:
            url = f"http://localhost:{puerto}/index.html"
            print(f"\n🌐 Servidor arrancado en {url}")
            print("   (Ctrl+C para pararlo)\n")
            webbrowser.open(url)
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n⏹️  Servidor detenido.")
    except OSError as e:
        print(f"\n❌ No se pudo abrir el puerto {puerto} ({e}). "
              f"¿Ya tienes un servidor corriendo?")


def ejecutar(ruta):
    if not ruta.exists():
        print(f"\n❌ No existe {ruta.relative_to(ROOT)}")
        return False
    print(f"\n{'=' * 55}\n🚀 {ruta.name}\n{'=' * 55}")
    try:
        subprocess.run([sys.executable, str(ruta)], check=True)
        return True
    except subprocess.CalledProcessError:
        print(f"\n❌ {ruta.name} ha fallado. Se detiene la cadena.")
        return False
    except KeyboardInterrupt:
        print("\n⚠️  Cancelado.")
        return False


def main():
    while True:
        print("\n" + "⚽" * 28)
        print("      🏆 PANEL DE CONTROL — PORRA LALIGA 🏆")
        print("⚽" * 28 + "\n")
        for tecla, etiqueta, _ in MENU:
            print(f"  {tecla}. {etiqueta}")
        print("  6. 🌐 Abrir la web en local (servidor en localhost:8000)")
        print("\n  0. ❌ Salir")
        print("-" * 56)

        opcion = input("Elige una opción: ").strip().lower()
        if opcion == "0":
            return
        if opcion == "6":
            servidor_local()
            continue
        elegido = next((m for m in MENU if m[0] == opcion), None)
        if not elegido:
            print("⚠️  Opción no válida.")
            continue
        for script in elegido[2]:
            if not ejecutar(script):
                break


if __name__ == "__main__":
    main()
