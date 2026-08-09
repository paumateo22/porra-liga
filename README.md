# 🏆 Porra LaLiga 2026-27

Porra de fútbol para un grupo de amigos. Una sola liga, web estática alojada en
GitHub Pages, sin servidor ni base de datos: el frontend lee ficheros JSON del
propio repositorio y toda la lógica vive en scripts de Python que se ejecutan en
local o mediante GitHub Actions.

Heredero directo del proyecto `porra_mundial`, con el mismo modus operandi: el
jugador genera un JSON desde la web, ese JSON entra al repo, y una cadena de
scripts lo convierte en puntos y clasificación.

---

## 📜 Normas

### Cómo se puntúa cada partido

| Concepto | Puntos | Detalle |
|---|---|---|
| Acierto **1X2** | **+1** | Aciertas quién gana (o el empate), sin importar el marcador |
| Acierto **exacto** | **+1 adicional** | El marcador clavado. Se suma al punto de 1X2, así que **un exacto vale 2 puntos en total** |

### Bonus de rendimiento

Se concede al final de cada jornada según cuántos aciertos **1X2** hayas
conseguido en esa jornada:

| Aciertos 1X2 | Bonus |
|---|---|
| 8 | **+2** |
| 9 | **+3** |
| 10 | **+5** |

Por debajo de 8 aciertos no hay bonus. El umbral y la tabla son configurables.

### Ganador y perdedor de la jornada

- Quien tenga **más aciertos 1X2** de la jornada: **+1 punto**.
- Quien tenga **menos aciertos 1X2** de la jornada: **−1 punto**.
- En caso de empate, **todos** los empatados en el máximo ganan y todos los
  empatados en el mínimo pierden.
- Si el máximo y el mínimo coinciden (todos empatados), no hay ni ganador ni
  perdedor.

> El criterio es **siempre el número de aciertos 1X2**, nunca los puntos totales.
> Así el bonus de rendimiento no distorsiona quién ha acertado más partidos.

### Requisito de participación

Para **optar** a ganador o perdedor de jornada hay que haber pronosticado **más
del 55 %** de los partidos de esa jornada (es decir, **6 o más de 10**).

Quien no llegue a ese umbral sigue sumando los puntos de sus aciertos, pero
queda fuera del reparto de +1 / −1. Esto evita que alguien que solo pronostica
dos partidos se lleve el premio de la jornada, y también que quien apenas juega
arrastre el castigo de perdedor.

### Cuándo se cierra una jornada

El ganador y el perdedor **solo se asignan cuando los 10 partidos de la jornada
han terminado**. Mientras la jornada está en curso los puntos de aciertos sí se
van actualizando en vivo, pero el +1 / −1 no se reparte para que no baile.

### Desempate en la clasificación general

A igualdad de puntos totales, por este orden:

1. **Jornadas ganadas**
2. **Aciertos exactos** acumulados
3. **Aciertos 1X2** acumulados

### Cierre de pronósticos

**El cierre es por partido, no por jornada.** Cada partido queda bloqueado en
cuanto llega su hora, independientemente del resto de su jornada.

Esto tiene tres consecuencias:

- **Puedes mandar la misma jornada tantas veces como quieras.** Cada reenvío se
  **fusiona** con lo que ya tenías guardado, no lo sustituye.
- **Los partidos ya jugados no se pueden tocar.** Si reenvías una jornada
  intentando cambiar un partido que ya se disputó, esa parte se ignora y se
  conserva lo que enviaste en su momento.
- **Los partidos que aún no se han jugado sí se actualizan**, aunque otros de
  esa misma jornada ya estén disputados.

El bloqueo se aplica **dos veces**: la web deshabilita los campos de los partidos
iniciados, y la ingesta vuelve a comprobarlo en el servidor. Editar el JSON a
mano no sirve de nada: la ingesta manda.

Cada predicción guarda la **hora del partido** junto al marcador, que es lo que
permite decidir qué está abierto y qué está cerrado.

### Partidos adelantados y aplazados

Una jornada de LaLiga no siempre se juega entera el mismo fin de semana. El
sistema lo contempla:

- Un partido **adelantado** (se juega meses antes que su jornada) puntúa en
  cuanto termina. Su jornada suma esos puntos pero permanece **abierta**.
- Un partido **aplazado** (se juega meses después) no impide que el resto de la
  jornada puntúe. El bonus de rendimiento se recalcula sobre lo jugado hasta el
  momento y se ajusta solo cuando llega el partido pendiente.
- El **ganador y el perdedor de jornada** esperan siempre a que se hayan jugado
  los 10 partidos. Una jornada con un aplazado en marzo no reparte +1 / −1 hasta
  marzo.

### Todo es configurable

Cada número de esta sección vive en `config/settings.json`. Cambiarlo y volver a
ejecutar el motor recalcula la temporada entera desde cero: no hay estado
acumulado que se pueda corromper.

---

## ⚙️ Funcionamiento

### La idea en una frase

No hay backend. Hay **ficheros JSON en un repositorio** y **scripts que los
transforman**. La web es una capa de lectura sobre esos ficheros.

### Las tres fuentes de datos

| Fichero | Qué es | Quién lo escribe |
|---|---|---|
| `config/calendario.json` | Las 38 jornadas: id de SofaScore, equipos y hora de cada partido | Script `00`, una vez por temporada |
| `data/resultados/realidad_oficial.json` | **La fuente de verdad**: resultados reales y estado de cada partido | Script `05`, en bucle durante la temporada |
| `participantes/<slug>/pronosticos/J01.json` … `J38.json` | Lo que pronosticó cada jugador | Script `03`, al ingerir el buzón |

De ahí sale todo lo demás. `data/clasificacion.json` y los historiales
individuales son **derivados**: se pueden borrar y regenerar en cualquier momento.

### La cadena de scripts

```
00  Calendario     SofaScore          ->  config/calendario.json
03  Ingesta        entradas/          ->  participantes/<slug>/pronosticos/
05  Resultados     SofaScore          ->  data/resultados/realidad_oficial.json
06  Motor          todo lo anterior   ->  data/clasificacion.json + historiales
```

El motor es **idempotente**: recalcula siempre la temporada completa desde los
tres ficheros fuente. No importa cuántas veces lo ejecutes ni en qué orden
llegaron los datos.

### Identificación de partidos por ID de SofaScore

Cada partido lleva su `id` numérico de SofaScore en el calendario, en los
resultados y en los pronósticos. El emparejamiento entre lo que pronosticaste y
lo que pasó se hace por ese id, nunca por el nombre de los equipos.

Es la diferencia principal respecto al proyecto del mundial, que usaba la clave
de texto `Local_vs_Visitante`. Con 38 jornadas, aplazamientos y variaciones en
los nombres de equipo, el id es lo único que aguanta la temporada entera.

### Identificación de jugadores

El nombre que escribes en el formulario se convierte en un `slug`
(`Miguel Dykan` → `miguel_dykan`) que es tu carpeta en `participantes/`. Si
escribes el nombre de forma distinta en dos jornadas, se crean dos jugadores
distintos. **Usa siempre el mismo nombre.**

Los jugadores se dan de alta solos: la primera vez que llega un pronóstico con
un nombre nuevo, la ingesta lo registra en `config/participantes.json` y le crea
la carpeta.

### Las vistas

| Página | Qué muestra |
|---|---|
| **🏆 Clasificación** (`index.html`) | Tabla general y rejilla de puntos por jornada |
| **📅 Calendario** (`calendario.html`) | Partidos y resultados, jornada a jornada o todas seguidas |
| **✍️ Pronosticar** (`pronosticar.html`) | Formulario que genera el JSON descargable |
| **🔍 Análisis** (`analisis.html`) | Quién acertó qué: tabla cruzada jugadores × partidos, y el detalle de cada partido |
| **📈 Carrera** (`carrera.html`) | Gráfico de evolución + marcador tipo "carrera de barras": las filas se reordenan animadas al mover la barra temporal, con reproducción automática y velocidad ajustable |
| **👥 Participantes** (`participantes.html`) | Quién juega, desde cuándo, media y porcentaje de acierto |
| **👤 Perfil** (`perfil.html?j=slug`) | Dashboard individual: rachas, mejor y peor jornada, gráfico de acumulado |
| **📜 Reglamento** (`reglamento.html`) | Las normas, generadas en vivo desde `settings.json` |

Las cuatro primeras están en la barra superior; el resto, en el menú lateral.

---

## 🔄 Flujos de uso

### Flujo del jugador

1. Entra en la web → pestaña **✍️ Pronosticar**.
2. Escribe su nombre (se recuerda en el navegador para las siguientes veces).
3. Elige la jornada. Por defecto se abre en la primera que aún no ha terminado.
4. Rellena los marcadores. Los partidos ya empezados aparecen bloqueados.
5. Pulsa **⬇️ Descargar mis pronósticos** y obtiene un fichero **`J02_Mateo.json`**.
6. Se lo manda al administrador (o lo sube él mismo a `entradas/`).

Si ya había mandado esa jornada, al escribir su nombre la web recupera los
marcadores que envió, para que pueda corregir solo lo que quiera cambiar.

### Flujo del administrador

1. Recibe los ficheros `J02_*.json` y los deja en la carpeta `entradas/`.
2. Ejecuta `python main.py` → opción **5 (Actualización total)**.
3. Revisa la consola: qué se ingirió, qué se rechazó y por qué.
4. `git add . && git commit && git push`.
5. GitHub Pages sirve la web actualizada en un par de minutos.

Con los workflows activados los pasos 2-4 son automáticos: basta con subir los
JSON a `entradas/` y hacer push.

### Flujo automático (GitHub Actions)

```
Push de un JSON a entradas/     ->  ingesta.yml          ingiere + recalcula + commit
Cada 20 min (en temporada)      ->  cron_sofascore.yml   baja resultados
   └─ si hubo cambios           ->  actualizador.yml     cascada completa + commit
Manual, cuando haga falta       ->  actualizador.yml
```

Los tres workflows corren sobre un **runner self-hosted** (tu PC o la Raspberry),
igual que en el proyecto del mundial. El scraper de SofaScore necesita una IP
doméstica: desde los runners públicos de GitHub, Cloudflare bloquea las peticiones.

### Flujo de desarrollo

Para trabajar sin depender de SofaScore ni esperar a que se jueguen partidos:

El simulador trabaja en **dos fases**, para respetar el orden real de los
acontecimientos (primero se pronostica, después se juega):

```bash
python simuladores/99_simulador.py 5        # fase 1: calendario + pronósticos
python main.py                              # opción 2 (ingesta)
python simuladores/99_simulador.py --jugar 3  # fase 2: se juegan 3 jornadas
python main.py                              # opción 4 (motor)
```

Incluye casos límite a propósito: un jugador que solo pronostica el 50 % (debe
quedar excluido de ganador/perdedor), otro que acierta el 75 % (debe disparar el
bonus) y un partido adelantado en la última jornada.

### Temporada de demostración con datos reales

Para ver la web llena antes de que empiece la temporada de verdad, se puede cargar
una temporada ya terminada de LaLiga con sus resultados reales, e inventar diez
participantes con pronósticos plausibles:

```bash
python simuladores/98_temporada_demo.py            # temporada 25/26 entera
python simuladores/98_temporada_demo.py 24/25      # otra temporada
python simuladores/98_temporada_demo.py --hasta 19 # solo media temporada
```

Descarga el calendario y los resultados de SofaScore, genera los pronósticos,
ejecuta el motor y deja la web lista. **Sobrescribe** `config/calendario.json`,
los resultados y la carpeta `participantes/`.

Los pronósticos no son ruido aleatorio: cada jugador tiene su nivel y su
constancia, los marcadores se eligen de una tabla ponderada de resultados típicos
de LaLiga, y los fallos se decantan según la fuerza real que tuvo cada equipo esa
temporada. Los partidos entre equipos parejos se aciertan menos. Dos jugadores
entran con la liga empezada y otro se deja jornadas a medias. El resultado son
tasas de acierto de entre el 45 % y el 62 % en 1X2 y entre el 12 % y el 17 % de
marcadores exactos, que es más o menos lo que da una porra de verdad.

### Tests

```bash
python tests/test_casos_limite.py      # motor: 26 comprobaciones
node tests/render.test.js              # vistas: 46 comprobaciones (requiere jsdom)
```

El primero comprueba de punta a punta los escenarios difíciles del motor: partido
adelantado, partido aplazado, reenvío de una jornada con partidos ya jugados, y
cierre de jornada cuando por fin se disputa el aplazado.

El segundo carga cada página HTML con jsdom sobre los JSON reales del repositorio
y verifica que pintan lo que deben: número de filas, gráficos dibujados, cifras
coherentes entre vistas y ausencia de errores de JavaScript. Instalar jsdom con
`npm install jsdom`.

---

## 🛠️ Administración

### Puesta en marcha

```bash
pip install -r requirements.txt
python main.py     # opción 1: genera el calendario y resuelve el season_id
```

La primera ejecución del script `00` busca el `season_id` de LaLiga 26/27 en
SofaScore y lo escribe en `config/settings.json`. Si no lo encuentra, imprime
las temporadas disponibles con sus ids para que lo pongas a mano.

### El panel de control

```
python main.py

  1. 📅 Regenerar calendario desde SofaScore (00)
  2. 📬 Ingerir pronósticos del buzón entradas/ (03)
  3. 📥 Actualizar resultados reales SofaScore (05)
  4. 🧮 Ejecutar motor de puntuación (06)
  5. ⚡ ACTUALIZACIÓN TOTAL (03 + 05 + 06)
  7. 🌍 Temporada demo con datos reales de SofaScore
  8. 🧪 Test de casos límite
  9. 🎲 Simulador — fase 1
  d. 🏅 Gestionar distintivos de jugadores
```

### El buzón `entradas/`

Los ficheros válidos se archivan en `participantes/` y el original se mueve a
`entradas/procesadas/` con marca de tiempo. **Los rechazados se quedan en
`entradas/`** con el motivo impreso en consola, para que puedas corregirlos.

Motivos de rechazo habituales:

- El fichero no es un JSON válido.
- Falta el campo `participante` o `jornada`.
- La jornada no existe en el calendario.
- Un `id` de partido no pertenece a esa jornada.
- El nombre del fichero dice `J02` pero dentro pone otra jornada.

Reenviar la misma jornada **fusiona** con lo ya guardado. La consola lo desglosa:

```
✅ Pau · J02 → 10/10 partidos (0 nuevos, 1 corregidos, 1 bloqueados, 0 fuera de plazo)
```

- **nuevos**: partidos que no habías pronosticado antes
- **corregidos**: cambiaste el marcador y el partido aún no se había jugado
- **bloqueados**: el partido ya se jugó, se conserva tu pronóstico original
- **fuera de plazo**: el partido ya se jugó y no tenías nada guardado; se descarta

### Ajustar las normas

Todo en `config/settings.json`:

```json
"puntuaciones": {
    "puntos_1x2": 1,
    "puntos_exacto": 1,
    "bonus_rendimiento": { "umbral_minimo": 8, "tabla": { "8": 2, "9": 3, "10": 5 } },
    "ganador_jornada": 1,
    "perdedor_jornada": -1,
    "porcentaje_minimo_participacion": 0.55
}
```

En `habilitadores` puedes apagar reglas enteras poniendo `0` (por ejemplo,
`"bonus_rendimiento": 0` desactiva el bonus para toda la temporada).

Tras cualquier cambio, ejecuta la opción 4 y la clasificación se recalcula entera.

### Distintivos de jugadores (🏆, ⭐...)

```bash
python scripts/gestionar_distintivos.py
```

Un emoji junto al nombre de un jugador, visible en toda la web (clasificación,
análisis, perfil, carrera, participantes). Se guarda como campo `distintivo`
en `config/participantes.json` y el motor lo propaga automáticamente a
`data/clasificacion.json` y `data/analisis/*.json` en cada ejecución — tras
asignar uno, hay que volver a correr el motor (opción 4) para que se vea.

El script permite dar de alta a alguien **por adelantado, con distintivo
incluido, aunque todavía no haya mandado ningún pronóstico** — aparecerá en la
clasificación con 0 puntos hasta que empiece a jugar. Cuando esa persona mande
su primer pronóstico, tiene que usar exactamente el mismo nombre para que
encaje con el registro ya creado, si no se le crea una ficha nueva sin el
distintivo.

### Nombres de equipo

`scripts/sofascore.py` contiene `MAPA_EQUIPOS`, que traduce el nombre que
devuelve SofaScore al que quieres mostrar (`Real Betis` → `Betis`). Si un equipo
no está en el mapa se muestra tal cual llega. Revísalo tras la primera ejecución
del script `00`, cuando veas los nombres reales de los 20 equipos de la temporada.

### Publicar en GitHub Pages

Settings → Pages → Source: rama `main`, carpeta raíz. No hay build step: lo que
hay en el repo es exactamente lo que se sirve.

### Corregir un resultado a mano

`data/resultados/realidad_oficial.json` es un fichero de texto. Puedes editarlo
directamente y ejecutar la opción 4. Ojo: la siguiente ejecución del script `05`
lo sobrescribirá con lo que diga SofaScore.

---

## 📂 Contenido

```
porra-liga/
│
├── index.html              Clasificación general (home)
├── calendario.html         Calendario y resultados por jornada
├── pronosticar.html        Formulario que genera el JSON descargable
├── analisis.html           Desglose cruzado de una jornada
├── carrera.html            Evolución animada de la clasificación
├── participantes.html      Quién juega y cómo le va
├── perfil.html             Dashboard individual (?j=slug)
├── reglamento.html         Normas generadas desde settings.json
├── theme.css               Estilos (heredados del proyecto del mundial)
├── layout.js               Cabecera, navegación y utilidades compartidas
│
├── main.py                 Panel de control CLI
├── requirements.txt        curl_cffi, tzdata
│
├── config/
│   ├── settings.json       Reglas de puntuación y datos de la competición
│   ├── calendario.json     38 jornadas: id, equipos y hora        [generado]
│   └── participantes.json  Registro de jugadores                  [generado]
│
├── data/
│   ├── resultados/
│   │   └── realidad_oficial.json     Fuente de verdad             [generado]
│   ├── clasificacion.json            Lo que lee el frontend       [generado]
│   ├── analisis/J01.json … J38.json  Desglose cruzado por jornada [generado]
│   └── reportes/
│       └── reporte_06_jornadas.json  Resumen por jornada          [generado]
│
├── entradas/               Buzón de JSON de pronósticos
│   └── procesadas/         Archivo de los ya ingeridos
│
├── participantes/
│   └── <slug>/
│       ├── pronosticos/J01.json … J38.json
│       └── estadisticas/historial_puntos.json
│
├── scripts/
│   ├── utils.py                      Rutas, slugs, carga/guardado de JSON
│   ├── sofascore.py                  Cliente de la API oculta de SofaScore
│   ├── 00_generador_calendario.py    Calendario de la temporada
│   ├── 03_ingesta_pronosticos.py     Buzón: valida y archiva
│   ├── 05_extractor_sofascore.py     Resultados reales
│   └── 06_motor_puntuacion.py        Motor de puntuación
│
├── simuladores/
│   ├── 98_temporada_demo.py  Temporada real de SofaScore + 10 jugadores
│   └── 99_simulador.py       Datos falsos para desarrollo (2 fases)
│
├── tests/
│   ├── test_casos_limite.py  Adelantados, aplazados, reenvíos y cierre
│   └── render.test.js        Renderiza cada vista y verifica que pinta
│
└── .github/workflows/
    ├── ingesta.yml         Push a entradas/ → ingiere y recalcula
    ├── cron_sofascore.yml  Cada 20 min en temporada → baja resultados
    └── actualizador.yml    Cascada completa (manual o encadenada)
```

### Formato del fichero de pronósticos

```json
{
    "participante": "Mateo",
    "jornada": 2,
    "generado": "2026-08-08T11:30:00",
    "predicciones": [
        {
            "id": 14025431,
            "local": "Betis",
            "visitante": "Girona",
            "fecha": "2026-08-23T21:00:00",
            "marcador": "٤٩٠٤٢٧٤٢八٤٣٣水火"
        }
    ]
}
```

Nombre del fichero: **`J02_Mateo.json`**. La ingesta comprueba que la jornada del
nombre coincida con la de dentro.

**El marcador va ofuscado**, no en claro (nada de `"goles_local": 2,
"goles_visitante": 1`). El objetivo es que nadie pueda copiarse mirando el
JSON directamente en GitHub o si el fichero se reenvía por el grupo de
WhatsApp. `pronosticar.html` lo codifica al generar la descarga;
`03_ingesta_pronosticos.py` y `06_motor_puntuacion.py` lo descodifican para
validar y puntuar.

El esquema: XOR con clave fija, y en vez de Base64 normal (que se reconoce a
simple vista) cada byte se parte en dos mitades y cada una se sustituye por un
símbolo de una tabla de dígitos arábigos y caracteres chinos, con símbolos de
"ruido" intercalados que no significan nada y un prefijo/sufijo decorativos
fijos — todo pensado para que no se parezca a ningún formato reconocible
(`ofuscarMarcador`/`desofuscarMarcador` en `layout.js`,
`ofuscar_marcador`/`desofuscar_marcador` en `scripts/utils.py`, tienen que
coincidir símbolo a símbolo entre los dos). **No es cifrado real**: la clave y
el esquema viven en código público, así que alguien con conocimientos
técnicos que abra la consola del navegador podría revertirlo. Sirve para el
vistazo casual, no para un ataque dirigido.

### Formato de `clasificacion.json`

```json
{
    "competicion": "LaLiga 2026-27",
    "generado": "2026-08-08T09:34:10",
    "jornadas_calculadas": ["J01", "J02"],
    "desempates": ["jornadas_ganadas", "aciertos_exactos", "aciertos_1x2"],
    "clasificacion": [
        {
            "puesto": 1,
            "slug": "pau",
            "nombre": "Pau",
            "puntos_totales": 50,
            "puntos_partidos": 43,
            "bonus_rendimiento": 5,
            "puntos_ganador_perdedor": 2,
            "aciertos_1x2": 23,
            "aciertos_exactos": 20,
            "partidos_pronosticados": 30,
            "jornadas_jugadas": 3,
            "jornadas_ganadas": 2,
            "jornadas_perdidas": 0,
            "por_jornada": { "J01": { "puntos": 16, "ganador": true } }
        }
    ]
}
```

---

## 🚧 Qué está por llegar

**Vistas**

- **Comparativa directa** entre dos jugadores: cara a cara jornada por jornada.
- **Heatmap de aciertos** por equipo: contra quién aciertas más y contra quién menos.

**Motor**

- **Entrada a mitad de temporada**: métodos para asignar puntos a las jornadas
  que un jugador no jugó (peor puntuación, media de peores jornadas, media
  general, o cero).
- **Modo salida** para quien abandone a mitad de temporada.
- **Sorpresas y decepciones**: rendimiento relativo a la expectativa, portado del
  proyecto del mundial.
- **Estadísticas por equipo**: contra quién aciertas más y contra quién menos.

**Infraestructura**

- **Migración del runner a Raspberry Pi**, para no depender de que el PC esté
  encendido.
- **Recepción automática de pronósticos** sin paso manual: hoy el JSON viaja por
  mensajería. La alternativa sin backend sería un formulario que abra
  directamente una Pull Request al repositorio.

**Más adelante (fuera del alcance de esta versión)**

- Multi-liga con backend real (FastAPI + SQLite), autenticación con Google y
  varias porras conviviendo. Es el objetivo final del proyecto, aparcado hasta
  que esta versión esté rodada durante una temporada completa.
