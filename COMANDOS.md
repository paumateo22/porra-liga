# 🎮 Comandos

Todos los comandos se ejecutan desde la carpeta raíz del proyecto
(`porra-liga/`), con el entorno de Python activado.

```bash
pip install -r requirements.txt
```

---

## ⚠️ Antes de nada: cómo ver la web

**No abras `index.html` con doble clic.** Los navegadores bloquean las
peticiones a ficheros (`fetch`) cuando la página se carga como `file://...`, así
que la web se queda en blanco sin avisar de nada.

Usa el panel de control:

```bash
python main.py     # opción 6
```

Abre `http://localhost:8000` en el navegador. Dejar la consola abierta
mientras navegas; `Ctrl+C` para pararlo. El servidor manda cabeceras que
desactivan el caché del navegador, así que cualquier cambio en un fichero
(HTML, CSS, JS) se ve en el siguiente recargar sin necesidad de forzar un
Ctrl+Shift+R.

---

## 📖 El panel de control

```bash
python main.py
```

Es la puerta de entrada a todo lo demás. Muestra un menú numerado; cada opción
llama a uno de los comandos de abajo.

| # | Qué hace | Script |
|---|---|---|
| 1 | Descarga el calendario de la temporada desde SofaScore | `00_generador_calendario.py` |
| 2 | Procesa los JSON del buzón `entradas/` | `03_ingesta_pronosticos.py` |
| 3 | Descarga los resultados reales desde SofaScore | `05_extractor_sofascore.py` |
| 4 | Recalcula toda la clasificación | `06_motor_puntuacion.py` |
| 5 | Encadena 2 + 3 + 4 | — |
| 6 | Abre la web en `localhost:8000` | — |
| 7 | Carga una temporada real terminada con 10 jugadores falsos | `98_temporada_demo.py` |
| 8 | Comprueba que el motor calcula bien los casos difíciles | `test_casos_limite.py` |
| 9 | Prepara datos de mentira para desarrollar sin red | `99_simulador.py` |
| r | Resetea todo + descarga el calendario (inicio de temporada) | `reset.py` |

---

## 🔧 Comandos uno a uno

### `00_generador_calendario.py` — Calendario de la temporada

```bash
python scripts/00_generador_calendario.py
```

Descarga las 38 jornadas de la temporada actual desde SofaScore: equipos, hora
y el `id` de cada partido. Escribe `config/calendario.json`. La primera vez
también resuelve el `season_id` y lo guarda en `config/settings.json` para no
tener que volver a buscarlo.

**Cuándo usarlo:** una vez, al arrancar la temporada. No hace falta repetirlo
salvo que LaLiga reordene jornadas completas.

---

### `03_ingesta_pronosticos.py` — Procesar el buzón

```bash
python scripts/03_ingesta_pronosticos.py
python scripts/03_ingesta_pronosticos.py --sin-cierre   # ver más abajo
```

Lee todos los `.json` sueltos directamente en `entradas/` (no en
subcarpetas), los valida contra el calendario oficial y los archiva en
`participantes/<jugador>/pronosticos/J02.json`. Los ficheros procesados se
mueven a `entradas/procesadas/`.

Si un partido de la jornada ya empezó, el marcador que traiga el fichero para
ese partido se ignora y se conserva lo que hubiera guardado antes. Es
automático: no hace falta hacer nada especial para reenviar una jornada a
medias.

**`--sin-cierre`**: desactiva ese bloqueo por hora de partido. Solo para
cargas retroactivas de una temporada ya terminada (lo usa internamente
`98_temporada_demo.py`). No lo uses con la temporada en curso: es la manera de
que alguien pronostique un partido después de haber terminado.

---

### `05_extractor_sofascore.py` — Resultados reales

```bash
python scripts/05_extractor_sofascore.py
```

Descarga el estado y marcador de todos los partidos de la temporada y
sobrescribe `data/resultados/realidad_oficial.json`. Es la fuente de verdad
del proyecto: de ahí sale todo lo que se compara con los pronósticos.

**Cuándo usarlo:** después de cada jornada, o en bucle mientras se juega (para
eso está el workflow `cron_sofascore.yml`).

---

### `06_motor_puntuacion.py` — Calcular la clasificación

```bash
python scripts/06_motor_puntuacion.py
```

Cruza calendario + resultados + pronósticos de todos los jugadores y
recalcula la temporada **entera** desde cero. Escribe:

- `data/clasificacion.json` — lo que lee la web
- `data/analisis/J01.json` … — desglose partido a partido de cada jornada
- `data/reportes/reporte_06_jornadas.json` — resumen técnico
- `participantes/<jugador>/estadisticas/historial_puntos.json`

Es idempotente: da igual cuántas veces lo ejecutes o en qué orden llegaron los
datos, el resultado siempre es el mismo a partir de las tres fuentes.

**Cuándo usarlo:** después de cualquier cambio en pronósticos, resultados o
en `config/settings.json`.

---

### `98_temporada_demo.py` — Temporada real de demostración

```bash
python simuladores/98_temporada_demo.py              # 25/26 completa
python simuladores/98_temporada_demo.py 24/25        # otra temporada
python simuladores/98_temporada_demo.py --hasta 19   # solo media temporada
```

Descarga una temporada de LaLiga **ya terminada** con sus resultados reales de
SofaScore, y genera 10 jugadores inventados con pronósticos plausibles (cada
uno con su nivel, ponderados por la fuerza real de los equipos). Ejecuta el
motor al final. Deja la web lista para ver con datos de verdad.

⚠️ **Sobrescribe** `config/calendario.json`, `data/resultados/`, `data/clasificacion.json`
y borra `participantes/` entero. No lo ejecutes con la temporada real en marcha.

---

### `reset.py` — Resetear todo, en un solo comando

```bash
python reset.py
```

Borra `participantes/`, `entradas/`, resultados y clasificación, deja
`config/participantes.json` vacío, y a continuación descarga el calendario
oficial de la temporada desde SofaScore. Es el equivalente a "empezar de cero".

Escrito en Python a propósito: **`rm -rf` es de bash y no existe en
PowerShell** (el terminal por defecto en Windows). Si lo escribes en
PowerShell verás `Remove-Item : No se encuentra ningún parámetro...`. Este
script funciona igual en Windows, macOS o Linux porque no depende de comandos
de una shell concreta.

**Cuándo usarlo:** al arrancar una temporada nueva, o para volver a un estado
limpio después de probar cosas.

---

### `config/nombres.txt` — Insignias junto al nombre (🏆, ⭐...)

No es un script, es un fichero de texto que editas a mano con cualquier
editor. Una línea por persona:

```
Pau; Pau 🏆(Liga 2025/26)
Ivan; Ivan ⭐(Mundial 2026)
```

- Antes del `;`: el nombre con el que esa persona pronostica.
- Después del `;`: el nombre a mostrar, con cero o más insignias pegadas al
  final en la forma `emoji(descripción)` — acumulables, la descripción puede
  llevar espacios. Sale al pasar el cursor por el emoji o al tocarlo/hacer
  clic (funciona igual en móvil).

Después de editar el fichero, ejecuta la opción **4** (o la 5) para que el
motor lo lea y actualice `data/clasificacion.json` y `data/analisis/*.json`.

**Dar de alta a alguien por adelantado**: añade su línea en `nombres.txt`
aunque todavía no haya mandado ningún pronóstico, y ejecuta el motor — se
registra solo con 0 puntos, insignia incluida. Cuando esa persona mande su
primer pronóstico tiene que usar exactamente el mismo nombre de antes del
`;`, para que encaje con la ficha ya creada.

Detalles del formato en `README.md` → "Insignias de jugadores".

**Cuándo usarlo:** para premiar a alguien con una insignia visual (campeón de
una edición anterior, ganador de otra porra, etc.), en cualquier momento de
la temporada.

---

### `99_simulador.py` — Datos falsos para desarrollar

Funciona en dos fases porque el candado de cierre por partido necesita que
primero se pronostique y después se juegue, en ese orden:

```bash
python simuladores/99_simulador.py 5          # fase 1: calendario + pronósticos
python scripts/03_ingesta_pronosticos.py      # los ingiere

python simuladores/99_simulador.py --jugar 3  # fase 2: se juegan 3 jornadas
python scripts/06_motor_puntuacion.py         # se calculan los puntos
```

`5` es el número de jornadas a preparar. Incluye casos límite a propósito: un
jugador que solo pronostica la mitad, otro que acierta el 75 %, y un partido
adelantado en la última jornada.

**Cuándo usarlo:** para probar cambios rápido, sin depender de SofaScore ni
esperar a que se jueguen partidos reales.

---

### Los tests

```bash
python tests/test_casos_limite.py       # 26 comprobaciones del motor
node tests/render.test.js               # 46 comprobaciones de las vistas
```

El primero prueba el motor de puntuación con partidos adelantados, aplazados,
reenvíos de jornada y cierres — sin tocar la web. Es solo Python.

El segundo carga cada página HTML con los datos reales que haya en el repo en
ese momento y comprueba que pintan correctamente. Necesita `npm install jsdom`
una vez.

---

## 🔁 Combinaciones habituales

### Resetear todo y preparar el inicio de temporada

```bash
python reset.py
python main.py     # opción 6, y navega por todas las pestañas
```

`reset.py` deja el proyecto limpio (calendario descargado, cero pronósticos,
cero resultados) en un solo comando, sea cual sea tu terminal. A partir de
aquí: `git add . && git commit -m "Inicio de temporada" && git push`.

### La secuencia normal de cada jornada

Es lo que hace la opción **5** del panel, o los workflows automáticos:

```bash
python scripts/03_ingesta_pronosticos.py    # procesa lo que haya en entradas/
python scripts/05_extractor_sofascore.py    # baja los resultados de la jornada
python scripts/06_motor_puntuacion.py       # recalcula la clasificación
git add . && git commit -m "Jornada X" && git push
```

### Ver la web con datos de mentira, rápido

```bash
python simuladores/99_simulador.py 5
python scripts/03_ingesta_pronosticos.py
python simuladores/99_simulador.py --jugar 3
python scripts/06_motor_puntuacion.py
python main.py     # opción 6
```

### Ver la web llena, con una temporada real

```bash
python simuladores/98_temporada_demo.py
python main.py     # opción 6
```

### Comprobar que nada se ha roto tras un cambio

```bash
python tests/test_casos_limite.py
node tests/render.test.js
```

Si ambos salen en verde, el motor calcula bien y las ocho vistas pintan lo que
deben con los datos actuales del repo.

### Volver a dejar el repo limpio después de probar

```bash
python reset.py
```

Antes de subir cambios a GitHub, para no publicar datos de prueba. Es el
mismo comando de "inicio de temporada" — sirve igual para limpiar después
de haber estado trasteando con el simulador.
