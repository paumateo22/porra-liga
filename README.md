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

### Ganador y perdedor de jornada: en vivo, no solo al cerrar

El ganador y el perdedor (+1 / −1) se reparten **ya, en cuanto haya un
resultado provisional claro** — no hace falta que la jornada esté cerrada
del todo. Según van cambiando los aciertos de cada uno (partidos que
terminan, o incluso partidos en directo con su marcador actual), el +1 / −1
puede **cambiar de dueño**: quien iba ganando puede dejar de hacerlo si a
otro le sale mejor un partido que se juega después.

Esto no necesita ninguna corrección especial: el motor recalcula la
temporada entera desde cero cada vez que se ejecuta, así que si el marcador
de un partido en directo cambia antes de terminar, el siguiente cálculo ya
sale bien solo con el dato actualizado.

En `analisis.html` se indica, además, si ese resultado ya es **seguro**:
**"⏳ Aún puede cambiar"** si a alguien le quedan partidos con los que
remontar, o **"✔ Ya es matemáticamente seguro"** si ya es imposible que
nadie más alcance al líder ni esquive al farolillo rojo (aunque acertaran
absolutamente todo lo que les queda por pronosticar).

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

### Partidos en directo puntúan con su marcador actual

Un partido "en directo" (estado `inprogress` en SofaScore, cualquier
variante que no sea "sin empezar" ni "terminado") puntúa igual que uno ya
acabado, usando su marcador **en ese momento** — no hace falta esperar al
pitido final. Si el resultado cambia antes de terminar, el siguiente cálculo
lo recoge solo, sin ninguna corrección manual.

Esto afecta a **todo** el sitio por igual: clasificación general, la
carrera, las flechas de movimiento... no es solo una vista previa aparte.

### Partidos adelantados y aplazados

Una jornada de LaLiga no siempre se juega entera el mismo fin de semana. El
sistema lo contempla:

- Un partido **adelantado** (se juega meses antes que su jornada) puntúa en
  cuanto termina. Su jornada suma esos puntos pero permanece **abierta**.
- Un partido **aplazado** (se juega meses después) no impide que el resto de la
  jornada puntúe. El bonus de rendimiento se recalcula sobre lo jugado hasta el
  momento y se ajusta solo cuando llega el partido pendiente.
- El ganador/perdedor de jornada se reparte de todos modos mientras la
  jornada sigue abierta por el aplazado (ver más arriba) — no espera a que
  se juegue.

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
| **🏆 Clasificación** (`index.html`) | Tabla general y rejilla de puntos por jornada, con flecha de movimiento (▲/▼/—) respecto a la jornada de referencia |
| **📅 Calendario** (`calendario.html`) | Partidos y resultados, jornada a jornada o todas seguidas — con botón para ver la clasificación real de LaLiga hasta esa jornada (PJ/PG/PE/PP/DG/GF/GC/Pts) |
| **✍️ Pronosticar** (`pronosticar.html`) | Formulario que genera el JSON descargable |
| **🔍 Análisis** (`analisis.html`) | Quién acertó qué: tabla cruzada jugadores × partidos, y el detalle de cada partido |
| **📈 Carrera** (`carrera.html`) | Gráfico de evolución + marcador tipo "carrera de barras", con reproducción fluida (interpolada, no a saltos) y velocidad ajustable. Eje Y con margen ajustado por defecto (opción para anclarlo a 0) y vista opcional centrada en un jugador, mostrando a los demás como diferencia respecto a él |
| **👥 Participantes** (`participantes.html`) | Quién juega, desde cuándo, media y porcentaje de acierto |
| **👤 Perfil** (`perfil.html?j=slug`) | Dashboard individual: rachas, mejor y peor jornada, gráfico de acumulado comparable con otros jugadores |
| **🗒️ Pronósticos de un jugador** (`pronosticos_jugador.html?j=slug&jornada=Jxx`) | Escudos, resultado real y el pronóstico de esa persona, dos partidos por fila, con opción de ver toda la temporada seguida — el título cambia al nombre del jugador. Se llega con el botón "Ver sus pronósticos" del perfil o desde la tabla "jornada a jornada" |
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
- **fuera de plazo**: el partido ya se jugó, no tenías nada guardado, Y el
  fichero se generó DESPUÉS de que empezara (el campo `"generado"`, que pone
  `pronosticar.html` al descargar, se compara con la hora del partido). Si el
  fichero se generó antes del pitido pero tarda en llegar al buzón — porque
  el admin lo sube más tarde, por ejemplo — se acepta igual: llegar tarde al
  buzón no es lo mismo que pronosticar tarde.

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

### Quién puede ver los pronósticos ya enviados

Es abierto para todo el grupo, sin ninguna clave ni verificación: en
`pronosticar.html`, escribir un nombre recupera directamente los pronósticos
que esa persona ya haya mandado; y en `pronosticos_jugador.html` (la vista
pública por jugador y jornada), el pronóstico se ve siempre, tanto si el
partido ya se jugó como si no. Es una decisión deliberada de diseño para
simplificar el uso entre amigos, no un descuido.

### Insignias de jugadores (🏆, ⭐...)

Un emoji junto al nombre de un jugador, visible en toda la web (clasificación,
análisis, perfil, carrera, participantes). No hace falta ningún script: se
edita a mano un fichero de texto, `config/nombres.txt`, uno por línea:

```
Pau; Pau 🏆(Liga 2025/26)
Ivan; Ivan ⭐(Mundial 2026)
Miguel Dykan; Miguel Dykan 🏆(Liga 2025/26) ⭐(Mundial 2026)
```

- Antes del `;`: el nombre con el que esa persona pronostica (tal cual lo
  escribe en `pronosticar.html`). No cambia su identidad ni cómo se casan sus
  pronósticos — solo sirve para saber a quién va destinada la línea.
- Después del `;`: el nombre tal como se muestra en la web, seguido de cero o
  más insignias pegadas al final con la forma `emoji(descripción)`. La
  descripción puede llevar espacios y símbolos (`Liga 2025/26`) — es lo que
  aparece al pasar el cursor por encima del emoji, o al tocarlo/hacer clic en
  él (para que funcione igual en el móvil que en el ordenador).
- **Las insignias son acumulables**: pon tantos `emoji(descripción)` seguidos
  como haga falta, siempre al final de la línea.
- Una insignia **necesita sus paréntesis** para reconocerse como tal, aunque
  la descripción quede vacía (`🔥()`); un emoji suelto sin paréntesis se trata
  como texto normal del nombre, no como insignia. Y tienen que ir todas
  seguidas al final: si escribes algo después de la última insignia, ninguna
  se reconoce.
- Líneas vacías o que empiecen por `#` se ignoran (sirven de comentario).

Tras editar el fichero, ejecuta la opción 4 (o cualquiera que incluya el
motor) para que se refleje en la web — el motor lee `nombres.txt` en cada
pasada y actualiza `data/clasificacion.json` y `data/analisis/*.json` solo.

**Solo decora a quien ya esté registrado de verdad.** Poner a alguien en
`nombres.txt` no lo da de alta ni lo hace aparecer en la clasificación: hasta
que esa persona no mande al menos un pronóstico real (y quede registrada en
`config/participantes.json` como cualquier otro jugador), su línea en
`nombres.txt` se ignora sin más. En cuanto mande su primer pronóstico —usando
exactamente el mismo nombre que pusiste antes del `;`— aparecerá con su
insignia puesta desde ese primer pronóstico.

### Partidos duplicados o jornadas cortas (calendario mal contado)

Si una jornada sale con más o menos partidos de la cuenta (por ejemplo, 11 en
vez de 10, con dos equipos repetidos), el motivo típico es que SofaScore
reprogramó un partido: el evento viejo se queda "fantasma" en su respuesta,
con un id distinto pero el mismo par de equipos, junto al nuevo. El script
`00_generador_calendario.py` lo detecta solo (por jornada + mismo par de
equipos, no solo por id) y se queda con el id más alto —el más reciente—,
avisando bien claro en la consola de los dos ids implicados por si hace
falta revisarlo a mano.

Si una jornada se queda corta y no hay ningún aviso de duplicado, el script
también imprime qué partidos se descartaron por no tener jornada asignada
(`roundInfo.round` vacío en la respuesta de SofaScore) — revisa esa lista
para ver si alguno de ellos era el que falta.

`python tests/test_generador_calendario.py` (opción **c** del panel)
reproduce este patrón con datos de prueba para comprobar que la
deduplicación sigue funcionando.

### Nombres de equipo

`scripts/sofascore.py` contiene `MAPA_EQUIPOS`, que traduce el nombre que
devuelve SofaScore al que quieres mostrar (`Real Betis` → `Betis`). Si un equipo
no está en el mapa se muestra tal cual llega. Revísalo tras la primera ejecución
del script `00`, cuando veas los nombres reales de los 20 equipos de la temporada.

### Publicar en GitHub Pages

Settings → Pages → Source: rama `main`, carpeta raíz. No hay build step: lo que
hay en el repo es exactamente lo que se sirve.

### Estadísticas de visitas (Google Analytics)

Cuántas visitas tiene la web, a qué páginas entra la gente y cuántos
visitantes distintos hay — con Google Analytics (GA4), gratis y sin servidor
propio, funciona igual en GitHub Pages.

1. Ve a [analytics.google.com](https://analytics.google.com), crea una cuenta
   (o usa una que ya tengas) y dentro una "propiedad" para esta web.
2. Te da un **ID de medición** con forma `G-XXXXXXXXXX`.
3. Pégalo en `layout.js`, en la constante `GA_MEASUREMENT_ID` (está casi al
   principio del fichero, vacía por defecto).
4. Haz push. En un par de minutos ya ves las visitas en tiempo real dentro
   de Analytics.

No hay que tocar nada más — al estar centralizado en `layout.js`, se activa
en las 9 páginas a la vez. Con la constante vacía (como viene por defecto) no
se carga nada, para no ensuciar tus propias estadísticas mientras pruebas en
local.

### Flechas de movimiento en la clasificación

Junto al nombre de cada jugador en `index.html` sale una flecha comparando su
puesto actual con el que tenía tras una jornada de referencia: ▲ verde con
el número de puestos que ha subido, ▼ roja con los que ha bajado, o un guion
si sigue igual. Quien acaba de incorporarse (sin clasificación anterior con
la que compararlo) también sale con un guion.

La jornada de referencia se elige sola: si la última jornada con datos ya
está cerrada del todo, se compara con la anterior a ella (para mostrar el
movimiento de esa última jornada completa); si sigue en curso (algún
partido pendiente), se busca hacia atrás la última que sí cerró. Todo el
cálculo se hace en el navegador a partir de lo que ya trae
`data/clasificacion.json` — no hace falta tocar el motor ni regenerar nada
aparte.

### Clasificación real de LaLiga (no confundir con la de la porra)

En `calendario.html`, el botón "📊 Clasificación de la liga" (en el centro de
la cabecera de cada jornada) muestra la tabla de liga REAL — no la de quién
va ganando la porra, sino la del propio campeonato: PJ, PG, PE, PP, DG, GF,
GC y Pts, calculada sumando todos los resultados ya terminados desde la
primera jornada hasta la que estés viendo. Un partido en directo no cuenta
todavía, igual que en cualquier tabla de liga de verdad — solo suma cuando
termina.

Se calcula entero en el navegador a partir de `config/calendario.json` y
`data/resultados/realidad_oficial.json`, sin tocar el motor. En "Ver todas
las jornadas" cada una tiene su propio botón, así que puedes ver cómo
evolucionó la tabla real jornada a jornada.

### Descargar/copiar la jornada como imagen

En `pronosticar.html`, junto al botón de descargar el JSON, hay dos más:
"Descargar imagen" y "Copiar imagen". Generan un PNG con todos los
pronósticos de la jornada visible (escudos incluidos), tal como estén
puestos en el formulario en ese momento — los partidos sin rellenar salen
con un guion. Se dibuja con `<canvas>` nativo, sin ninguna librería externa.

Los escudos se cargan del CDN de SofaScore. Si ese servidor no permitiera
cargar imágenes de otro dominio dentro de un canvas que luego se exporta
(una restricción de seguridad del navegador, no un fallo nuestro), la
imagen se regenera sola sin escudos en vez de romperse — no hace falta
hacer nada si eso pasa, simplemente sale la versión sin escudos.

### Widgets de la cabecera (próximo partido, en directo...)

En todas las páginas, debajo del título, salen cuatro tarjetas: próximo
partido con cuenta atrás en vivo (segundos incluidos), próxima jornada que
aún no ha empezado, último resultado terminado, y el partido en directo si
lo hay (si no, el próximo). Se generan solas, sin tocar cada página — están
colgadas de `montarCabecera()` en `layout.js`.

Para que el marcador "en directo" se actualice de verdad mientras se juega,
hace falta que `05_extractor_sofascore.py` se ejecute con frecuencia durante
los partidos — normalmente vía el workflow `cron_sofascore.yml` (si lo
desactivaste, reactívalo quitándole el `.disabled` del nombre).

### Entrar a mitad de temporada (punto de partida)

Si alguien manda su primer pronóstico en una jornada que no es la primera de
la temporada, el motor le asigna automáticamente un **punto de partida**: los
mismos puntos totales que llevara en ese momento quien fuera último en la
clasificación (0 si es el primero en pronosticar de todos). Así no arranca
con una clasificación general imposible de remontar.

Es solo un punto de salida, no un premio: **no cuenta** como acierto 1X2,
acierto exacto, jornada ganada ni jornada perdida — esas estadísticas
arrancan de cero con su primer pronóstico real, igual que con cualquiera. Se
calcula solo, sin que tengas que hacer nada — y se indica en su perfil
(`punto_partida` en `data/clasificacion.json`) para que quede claro de dónde
sale ese número si alguien pregunta.

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
            "goles_local": 2,
            "goles_visitante": 1
        }
    ]
}
```

Nombre del fichero: **`J02_Mateo.json`**. La ingesta comprueba que la jornada del
nombre coincida con la de dentro.

**El marcador va en claro**, sin ningún tipo de cifrado ni ofuscación (versiones
anteriores de este proyecto codificaban el número con un esquema propio para
que no se leyera a simple vista al abrir el JSON; se quitó a propósito —
la protección real contra copiarse ya no depende de ocultar el número en el
fichero, sino de que la propia web nunca enseña el pronóstico de un partido
que aún no se ha jugado, sea de quien sea el enlace que se abra, así que
ocultar el número en el fichero ya no aportaba nada, solo complejidad).

Un fichero de una temporada anterior a este cambio, con un campo `"marcador"`
en vez de `"goles_local"`/`"goles_visitante"`, ya no se procesa: hay que
volver a generarlo desde `pronosticar.html`.

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
