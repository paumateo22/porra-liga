# 🧪 Probar cosas concretas

Recetario para cuando quieres comprobar **una cosa en concreto**, no correr
toda la cadena. Cada receta parte de cero y usa el simulador (`99_simulador.py`),
así no toca datos reales.

Antes de cualquier receta, deja el proyecto limpio:

```bash
python reset.py
```

(Esto también descarga el calendario real; si prefieres uno de mentira para
no depender de internet, usa en su lugar los tres primeros comandos de la
siguiente receta.)

---

## Ver la web con datos de mentira, ya

```bash
python simuladores/99_simulador.py 5
python scripts/03_ingesta_pronosticos.py
python simuladores/99_simulador.py --jugar 3
python scripts/06_motor_puntuacion.py
python main.py     # opción 6
```

Abre `localhost:8000`. Cinco jugadores, 5 jornadas, 3 ya jugadas.

---

## Probar el reenvío de una jornada (fusión, no sobrescritura)

Quieres comprobar que reenviar una jornada a medio jugar conserva los
partidos ya disputados y solo actualiza los pendientes.

```bash
python simuladores/99_simulador.py 3
python scripts/03_ingesta_pronosticos.py
python simuladores/99_simulador.py --jugar 1     # se juega la J01 entera

# Reenvío manual de Pau para la J01: intenta cambiar un partido ya jugado
python -c "
import json, sys
sys.path.insert(0, 'scripts')
from utils import ofuscar_marcador
cal = json.load(open('config/calendario.json'))['J01']
p = cal[0]
json.dump({
    'participante': 'Pau', 'jornada': 1, 'generado': '2026-01-01T00:00:00',
    'predicciones': [{**p, 'marcador': ofuscar_marcador(9, 9)}]
}, open('entradas/J01_Pau.json', 'w'), indent=4)
"
python scripts/03_ingesta_pronosticos.py
```

Mira la consola: debe decir `1 bloqueados` y el pronóstico de ese partido
debe seguir siendo el original. Compruébalo:

```bash
python -c "
import json
d = json.load(open('participantes/pau/pronosticos/J01.json'))
print(d['predicciones'][0])
"
```

---

## Probar un partido adelantado o aplazado

```bash
python simuladores/99_simulador.py 5
```

El simulador ya adelanta el primer partido de la última jornada preparada
(comprobable en `config/calendario.json`, jornada más alta). Para forzarlo
tú mismo sobre cualquier jornada:

```bash
python -c "
import json
from datetime import datetime, timedelta
cal = json.load(open('config/calendario.json'))
cal['J02'][0]['fecha'] = (datetime.now() - timedelta(days=1)).isoformat(timespec='seconds')
json.dump(cal, open('config/calendario.json', 'w'), indent=4, ensure_ascii=False)

real = json.load(open('data/resultados/realidad_oficial.json'))
p = real['J02'][0]
p['goles_local'], p['goles_visitante'], p['estado'] = 2, 1, 'finished'
p['fecha'] = (datetime.now() - timedelta(days=1)).isoformat(timespec='seconds')
json.dump(real, open('data/resultados/realidad_oficial.json', 'w'), indent=4, ensure_ascii=False)
"
python scripts/06_motor_puntuacion.py
```

Revisa `data/reportes/reporte_06_jornadas.json` → `J02` → `cerrada` debe ser
`false` aunque ese partido ya puntúe.

Para la prueba automática y completa de este escenario (adelantado, aplazado,
reenvío y cierre final, con comprobaciones):

```bash
python tests/test_casos_limite.py
```

---

## Probar el umbral de participación (55 %)

Quieres ver a alguien quedarse fuera de ganador/perdedor por pronosticar
poco.

```bash
python simuladores/99_simulador.py 1
```

Edita a mano cuántos partidos pronostica cada uno antes de ingerir, o revisa
directamente el resultado con el dataset por defecto: Manu, en el simulador,
solo pronostica la mitad de los partidos a propósito.

```bash
python scripts/03_ingesta_pronosticos.py
python simuladores/99_simulador.py --jugar 1
python scripts/06_motor_puntuacion.py
python -c "
import json
j = json.load(open('data/reportes/reporte_06_jornadas.json'))['J01']['jugadores']
print('Manu elegible:', j['manu']['elegible_jornada'])
print('Manu pronosticados:', j['manu']['partidos_pronosticados'])
"
```

Debe salir `elegible_jornada: False` con 5 partidos pronosticados de 10.

---

## Probar un cambio en las reglas de puntuación

Por ejemplo, subir el bonus de rendimiento o bajar el umbral de exactos.

```bash
# 1. Edita config/settings.json a mano (o con este atajo):
python -c "
import json
s = json.load(open('config/settings.json'))
s['puntuaciones']['bonus_rendimiento']['tabla']['8'] = 4   # antes +2
json.dump(s, open('config/settings.json', 'w'), indent=4, ensure_ascii=False)
"

# 2. Prepara datos y recalcula
python simuladores/99_simulador.py 3
python scripts/03_ingesta_pronosticos.py
python simuladores/99_simulador.py --jugar 2
python scripts/06_motor_puntuacion.py

# 3. Comprueba que el reglamento en la web refleja el cambio
python main.py     # opción 6 → reglamento.html
```

El reglamento se genera leyendo `settings.json` en el navegador: si el cambio
no aparece ahí, el problema está en la web, no en el motor.

---

## Probar cómo se ve un perfil de jugador concreto

```bash
python simuladores/98_temporada_demo.py --hasta 10
python main.py     # opción 6
```

Y en el navegador ve a `perfil.html?j=pau` (o `aitor`, `javi`, `manu`,
`alvaro`, `marta`, `nerea`, `dani`, `sergio`, `lucia`). Con `--hasta 10`
tarda menos que la temporada entera y ya hay datos de sobra para ver rachas.

---

## Probar que la ingesta rechaza un fichero mal formado

```bash
python simuladores/99_simulador.py 2
echo '{"participante": "Roto"}' > entradas/J01_Roto.json    # sin jornada ni predicciones
python scripts/03_ingesta_pronosticos.py
```

Debe salir `❌ J01_Roto.json: rechazado` con la lista de motivos, y el
fichero debe seguir en `entradas/` (no se mueve a `procesadas/`).

---

## Probar que un partido con id equivocado se rechaza

```bash
python simuladores/99_simulador.py 1
python -c "
import json, sys
sys.path.insert(0, 'scripts')
from utils import ofuscar_marcador
cal = json.load(open('config/calendario.json'))['J01'][0]
json.dump({
    'participante': 'Fantasma', 'jornada': 1, 'generado': '2026-01-01T00:00:00',
    'predicciones': [{**cal, 'id': 99999999, 'marcador': ofuscar_marcador(1, 0)}]
}, open('entradas/J01_Fantasma.json', 'w'), indent=4)
"
python scripts/03_ingesta_pronosticos.py
```

Debe rechazarse con `el partido id 99999999 no es de J01`.

---

## Probar la web sin arrancar Python (solo para mirar el HTML)

No se puede: todas las páginas leen JSON con `fetch`, y eso exige un
servidor. Ver la sección de `python main.py` → opción 6 en `COMANDOS.md`.

Si quieres mirar solo el maquetado sin datos reales, deja `config/calendario.json`
sin generar: cada página muestra su mensaje de "todavía no hay datos" en vez de
romperse, así que sirve para revisar que ese estado vacío se ve bien.

---

## Verificación rápida antes de subir cambios

```bash
python tests/test_casos_limite.py && node tests/render.test.js
```

Si ambos acaban en verde, el motor calcula bien y las ocho vistas pintan lo
que deben. No sustituye a mirarlo en el navegador, pero atrapa la mayoría de
roturas.
