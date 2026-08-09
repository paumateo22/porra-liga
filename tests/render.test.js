/* Renderiza cada página con jsdom sobre los ficheros JSON reales del repo y
   comprueba que pintan lo que deben. Las expectativas se derivan de los propios
   datos, así que funciona igual con 3 jornadas simuladas que con una temporada
   real de 38.

   Uso:  node tests/render.test.js       (desde la raíz del proyecto)   */

const fs = require("fs");
const path = require("path");
const { JSDOM, VirtualConsole } = require("jsdom");

const RAIZ = path.resolve(__dirname, "..");
const fallos = [];

const leer = (rel) => JSON.parse(fs.readFileSync(path.join(RAIZ, rel), "utf8"));

function check(ok, desc) {
  console.log(`  ${ok ? "✅" : "❌"} ${desc}`);
  if (!ok) fallos.push(desc);
}

/* fetch falso que lee del disco, imitando a GitHub Pages */
function fetchLocal(url) {
  const ruta = path.join(RAIZ, String(url).split("?")[0]);
  if (!fs.existsSync(ruta)) {
    return Promise.resolve({ ok: false, status: 404, json: () => Promise.reject(new Error("404")) });
  }
  const texto = fs.readFileSync(ruta, "utf8");
  return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(JSON.parse(texto)) });
}

async function render(fichero, busqueda = "") {
  let html = fs.readFileSync(path.join(RAIZ, fichero), "utf8");

  // jsdom no descarga <script src>: se incrusta antes de parsear, así el orden
  // de ejecución es el mismo que en el navegador.
  html = html.replace(/<script src="([^"]+)"><\/script>/g, (_, src) =>
    `<script>${fs.readFileSync(path.join(RAIZ, src), "utf8")}</script>`);

  const errores = [];
  const vc = new VirtualConsole();
  vc.on("jsdomError", (e) => errores.push(e.message));

  const dom = new JSDOM(html, {
    runScripts: "dangerously",
    url: `https://ejemplo.test/${fichero}${busqueda}`,
    virtualConsole: vc,
    beforeParse(win) {
      win.fetch = fetchLocal;
      if (!win.localStorage) {
        const almacen = {};
        win.localStorage = {
          getItem: (k) => (k in almacen ? almacen[k] : null),
          setItem: (k, v) => { almacen[k] = String(v); },
        };
      }
      win.confirm = () => true;
      win.URL.createObjectURL = () => "blob:falso";
      win.URL.revokeObjectURL = () => {};
      win.addEventListener("unhandledrejection", (e) => errores.push(String(e.reason)));
    },
  });

  await new Promise((r) => setTimeout(r, 300));
  return { dom, doc: dom.window.document, errores };
}

const texto = (doc, sel) => (doc.querySelector(sel)?.textContent || "").trim();
const cuenta = (doc, sel) => doc.querySelectorAll(sel).length;

async function probarEscenarioReset() {
  const rutaRealidad = path.join(RAIZ, "data/resultados/realidad_oficial.json");
  const rutaClasificacion = path.join(RAIZ, "data/clasificacion.json");
  const rutaAnalisis = path.join(RAIZ, "data/analisis");
  const backupRealidad = rutaRealidad + ".bak";
  const backupClasificacion = rutaClasificacion + ".bak";
  const backupAnalisis = rutaAnalisis + ".bak";

  const totalJornadasCalendario = Object.keys(leer("config/calendario.json")).length;

  const habiaRealidad = fs.existsSync(rutaRealidad);
  const habiaClasificacion = fs.existsSync(rutaClasificacion);
  if (habiaRealidad) fs.renameSync(rutaRealidad, backupRealidad);
  if (habiaClasificacion) fs.renameSync(rutaClasificacion, backupClasificacion);
  fs.renameSync(rutaAnalisis, backupAnalisis);
  fs.mkdirSync(rutaAnalisis);

  try {
    console.log("\n═══ Escenario: recién reseteado (reset.py, sin resultados ni clasificación) ═══");

    const { doc: docCal, errores: errCal } = await render("calendario.html");
    check(errCal.length === 0, `calendario.html sin errores de JS ${errCal[0] || ""}`);
    check(docCal.querySelector(".celda-jornada-nav.activa")?.textContent.trim() === "1",
      "calendario.html abre en la jornada 1 recién reseteado, no en la última");

    const { doc: docPro, errores: errPro } = await render("pronosticar.html");
    check(errPro.length === 0, `pronosticar.html sin errores de JS ${errPro[0] || ""}`);
    check(docPro.querySelector(".celda-jornada-nav.activa")?.textContent.trim() === "1",
      "pronosticar.html abre en la jornada 1 recién reseteado, no en la última");

    const { doc: docAn, errores: errAn } = await render("analisis.html");
    check(errAn.length === 0, `analisis.html sin errores de JS ${errAn[0] || ""}`);
    check(cuenta(docAn, "#barra-jornadas .celda-jornada-nav") === totalJornadasCalendario,
      `analisis.html muestra la barra con las ${totalJornadasCalendario} jornadas del calendario aunque no haya nada calculado`);
    check(texto(docAn, "#banner-resultado").includes("Todavía no hay análisis"),
      "analisis.html indica que no hay análisis en vez de mostrar contenido viejo");
    check(cuenta(docAn, "#tabla-cruzada tr") === 0,
      "analisis.html no pinta ninguna fila de tabla cuando la jornada no tiene datos");
    check(cuenta(docAn, "#grafico-barras svg") === 0,
      "analisis.html no dibuja la gráfica de barras cuando la jornada no tiene datos");
  } finally {
    fs.rmSync(rutaAnalisis, { recursive: true, force: true });
    fs.renameSync(backupAnalisis, rutaAnalisis);
    if (habiaRealidad) fs.renameSync(backupRealidad, rutaRealidad);
    if (habiaClasificacion) fs.renameSync(backupClasificacion, rutaClasificacion);
  }
}

(async () => {
  await probarEscenarioReset();

  // ---- Datos de referencia, leídos del repo ----
  const clas = leer("data/clasificacion.json");
  const calendario = leer("config/calendario.json");
  const realidad = leer("data/resultados/realidad_oficial.json");

  const nJugadores = clas.clasificacion.length;
  const clavesCal = Object.keys(calendario);
  const nJornadas = clavesCal.length;
  const claveAnalisis = clas.jornadas_calculadas[clas.jornadas_calculadas.length - 1];
  const analisis = leer(`data/analisis/${claveAnalisis}.json`);
  const jugadosTotal = Object.values(realidad)
    .flat().filter((p) => p.estado === "finished").length;

  // Jornada en la que abre calendario/pronosticar: la primera con algo sin jugar
  const claveActual = clavesCal.find((c) => (realidad[c] || []).some((p) => p.estado !== "finished"))
    || clavesCal[nJornadas - 1];

  const lider = clas.clasificacion[0];
  console.log(`\nDataset: ${nJornadas} jornadas · ${nJugadores} jugadores · ${jugadosTotal} partidos jugados`);

  console.log("\n═══ index.html · Clasificación ═══");
  {
    const { doc, errores } = await render("index.html");
    check(errores.length === 0, `sin errores de JS ${errores[0] || ""}`);
    check(cuenta(doc, "header .top-nav a") >= 4, "la cabecera monta la navegación");
    check(cuenta(doc, "#cuerpo-resumen tr") === nJugadores,
      `una fila por jugador en el resumen (${nJugadores})`);
    check(texto(doc, "#cuerpo-resumen tr td:nth-child(2)").includes(lider.nombre),
      `${lider.nombre} encabeza la tabla`);
    if (lider.distintivo) {
      check(texto(doc, "#cuerpo-resumen tr td:nth-child(2)").includes(lider.distintivo),
        `el distintivo del líder (${lider.distintivo}) aparece junto a su nombre`);
    }
    check(texto(doc, "#cuerpo-resumen tr td.col-total").startsWith(String(lider.puntos_totales)),
      "los puntos totales del líder coinciden");
    check(texto(doc, "#cuerpo-resumen tr td.col-aciertos").includes(`${lider.aciertos_exactos} / ${lider.aciertos_1x2}`),
      "muestra exactos / 1X2 del líder");
    check(texto(doc, "#pie-clasificacion").includes("Desempate"), "muestra el desempate");

    check(cuenta(doc, "#cabecera-jornadas th") === clas.jornadas_calculadas.length + 2,
      "tabla de jornadas: una columna por jornada, más jugador y total");
    check(cuenta(doc, "#cuerpo-jornadas tr") === nJugadores, "tabla de jornadas: una fila por jugador");
    check(doc.querySelector("table.tabla-ancha") !== null,
      "la tabla de jornadas usa ancho fijo (sin scroll horizontal)");
    const primeraCeldaJornada = doc.querySelector("#cuerpo-jornadas td.celda-jornada");
    if (primeraCeldaJornada) {
      const valor = parseInt(primeraCeldaJornada.textContent);
      check(valor >= 0 && valor <= 10,
        `la celda de jornada muestra aciertos 1X2 (0-10), no puntos totales (vio ${valor})`);
    }
    const hayGanador = clas.clasificacion.some((c) =>
      Object.values(c.por_jornada).some((j) => j.ganador));
    if (hayGanador) {
      check(cuenta(doc, "#cuerpo-jornadas .celda-jornada.ganador") > 0,
        "resalta al menos una jornada ganada");
    }
    const hayBonus = clas.clasificacion.some((c) =>
      Object.values(c.por_jornada).some((j) => j.bonus > 0));
    if (hayBonus) {
      check(cuenta(doc, "#cuerpo-jornadas .con-bonus") > 0, "resalta en azul las jornadas con bonus");
    }

    check(cuenta(doc, "#cabecera-heatmap th") === clas.jornadas_calculadas.length + 1,
      "heatmap: una columna por jornada, más jugador");
    check(cuenta(doc, "#cuerpo-heatmap tr") === nJugadores, "heatmap: una fila por jugador");
    check(cuenta(doc, "#cuerpo-heatmap .celda-heatmap[style]") > 0,
      "el heatmap aplica color de fondo a las celdas");
  }

  console.log("\n═══ calendario.html ═══");
  {
    const { doc, dom, errores } = await render("calendario.html");
    check(errores.length === 0, `sin errores de JS ${errores[0] || ""}`);
    check(cuenta(doc, "#barra-jornadas .celda-jornada-nav") === nJornadas,
      `${nJornadas} jornadas en la barra`);
    check(doc.querySelector(".celda-jornada-nav.activa")?.textContent.trim()
      === String(parseInt(claveActual.slice(1))),
      `abre en la jornada en curso (${claveActual})`);
    check(cuenta(doc, "#contenido .partido") === calendario[claveActual].length,
      "pinta todos los partidos de esa jornada");
    check(cuenta(doc, "#contenido .fecha-partido") === calendario[claveActual].length,
      "muestra la fecha de cada partido, no solo la hora");

    doc.querySelector("#btn-todas").dispatchEvent(new dom.window.Event("click"));
    await new Promise((r) => setTimeout(r, 80));
    check(cuenta(doc, "#contenido .cabecera-jornada") === nJornadas,
      "'Ver todas' pinta todas las jornadas");
    check(cuenta(doc, "#contenido .partido.jugado") === jugadosTotal,
      `marca los ${jugadosTotal} partidos ya jugados`);
  }

  console.log("\n═══ pronosticar.html ═══");
  {
    const { doc, errores } = await render("pronosticar.html");
    check(errores.length === 0, `sin errores de JS ${errores[0] || ""}`);
    const nPartidos = calendario[claveActual].length;
    check(cuenta(doc, "#partidos input[type=number]") === nPartidos * 2,
      `dos campos por partido (${nPartidos * 2})`);
    check(doc.querySelector("#btn-descargar") !== null, "el botón de descarga existe");

    check(cuenta(doc, "#barra-jornadas .celda-jornada-nav") === nJornadas,
      "la barra de jornadas tiene una casilla por jornada");
    check(doc.querySelector(`#barra-jornadas .celda-jornada-nav.activa`)?.textContent.trim()
      === String(parseInt(claveActual.slice(1))),
      "la casilla activa es la jornada en curso");
    check(cuenta(doc, "#barra-jornadas .flecha-jornada") === 2,
      "la barra de jornadas tiene flechas izquierda y derecha");
    check(doc.querySelector(".fila-nombre-compacta #nombre") !== null,
      "el campo de nombre vive en una fila compacta, no centrado a toda anchura");
    check(doc.querySelector("input.campo-nombre-compacto") !== null,
      "el campo de nombre usa un ancho acotado (clase campo-nombre-compacto), no ocupa toda la pantalla");
    check(cuenta(doc, "#barra-jornadas") === 1 && doc.querySelector("#barra-jornadas").previousElementSibling
      .classList.contains("fila-nombre-compacta"),
      "la barra de jornadas ocupa su propia fila a todo lo ancho, justo debajo del nombre");

    const yaJugados = (realidad[claveActual] || [])
      .filter((p) => p.estado === "finished").length;
    check(cuenta(doc, "#partidos input[disabled]") === yaJugados * 2,
      `bloquea los partidos ya jugados de la jornada (${yaJugados})`);
    check(cuenta(doc, "#partidos .fecha-partido") === nPartidos,
      "muestra la fecha de cada partido en el formulario de pronósticos");
  }

  console.log("\n═══ pronosticar.html · precarga de pronósticos ya enviados (marcador ofuscado) ═══");
  {
    const jugadorPrueba = clas.clasificacion[0];
    const rutaGuardado = path.join(RAIZ, `participantes/${jugadorPrueba.slug}/pronosticos/${claveActual}.json`);

    if (fs.existsSync(rutaGuardado)) {
      const { dom, doc, errores } = await render("pronosticar.html");
      check(errores.length === 0, `sin errores de JS al cargar ${errores[0] || ""}`);

      const nombreInput = doc.querySelector("#nombre");
      nombreInput.value = jugadorPrueba.nombre;
      nombreInput.dispatchEvent(new dom.window.Event("blur"));
      await new Promise((r) => setTimeout(r, 250));

      const guardado = leer(`participantes/${jugadorPrueba.slug}/pronosticos/${claveActual}.json`);
      check(!texto(doc, "body").includes(guardado.predicciones[0].marcador),
        "el token ofuscado no aparece nunca como texto plano en la página");

      const primeraPred = guardado.predicciones.find((p) =>
        doc.querySelector(`input[data-id="${p.id}"][data-lado="l"]`));
      if (primeraPred) {
        const { gl, gv } = dom.window.desofuscarMarcador(primeraPred.marcador);
        const lInput = doc.querySelector(`input[data-id="${primeraPred.id}"][data-lado="l"]`);
        const vInput = doc.querySelector(`input[data-id="${primeraPred.id}"][data-lado="v"]`);
        check(lInput && String(lInput.value) === String(gl) && vInput && String(vInput.value) === String(gv),
          `la precarga descodifica el marcador ofuscado y rellena los campos correctamente (${gl}-${gv})`);
      }
    }
  }

  console.log("\n═══ analisis.html ═══");
  {
    const { doc, errores } = await render("analisis.html");
    check(errores.length === 0, `sin errores de JS ${errores[0] || ""}`);
    check(doc.querySelector(".celda-jornada-nav.activa")?.textContent.trim()
      === String(parseInt(claveAnalisis.slice(1))),
      `abre en la última jornada calculada (${claveAnalisis})`);
    check(cuenta(doc, "#barra-jornadas .celda-jornada-nav") === nJornadas,
      "la barra de jornadas tiene una casilla por cada jornada del calendario, no solo las calculadas");
    check(!texto(doc, "body").includes("Quién acertó qué"),
      "no queda el título antiguo 'Quién acertó qué'");

    check(cuenta(doc, "#tabla-cruzada thead th") === analisis.partidos.length + 2,
      "columnas = jugador + partidos + total (sin desglose 1X2/exactos/bonus)");
    check(cuenta(doc, "#tabla-cruzada tbody tr") === analisis.jugadores.length,
      "una fila por jugador con pronóstico");
    check(cuenta(doc, "#tabla-cruzada thead .cabecera-partido") === analisis.partidos.length,
      "cada partido va en una sola cabecera compacta");
    check(!texto(doc, "#tabla-cruzada thead").match(/[A-Z]{3}/),
      "la cabecera ya no muestra siglas de equipo, solo escudos y resultado");
    check(cuenta(doc, "#tabla-cruzada tbody .pts") > 0,
      "cada celda de pronóstico muestra el desglose de puntos debajo");
    const jugadorConDistintivo = analisis.jugadores.find((j) => j.distintivo);
    if (jugadorConDistintivo) {
      check(texto(doc, "#tabla-cruzada tbody").includes(jugadorConDistintivo.distintivo),
        `el distintivo (${jugadorConDistintivo.distintivo}) aparece en la tabla cruzada del análisis`);
    }

    check(cuenta(doc, "#por-partido .match-card") === 0,
      "no queda el desglose partido a partido");

    check(doc.querySelector("#grafico-barras svg") !== null, "dibuja la gráfica de barras");
    check(cuenta(doc, "#grafico-barras svg rect") === analisis.jugadores.length,
      "una barra por jugador");
    check(doc.querySelector("#grafico-barras svg rect title") !== null,
      "las barras tienen tooltip con el desglose");

    const puntos = analisis.jugadores.map((j) => j.puntos);
    check(puntos.every((v, i) => i === 0 || v <= puntos[i - 1]),
      "los jugadores del análisis ya vienen ordenados de más a menos puntos");
  }

  console.log("\n═══ participantes.html ═══");
  {
    const { doc, errores } = await render("participantes.html");
    check(errores.length === 0, `sin errores de JS ${errores[0] || ""}`);
    check(cuenta(doc, "#cuerpo tr") === nJugadores, "una fila por participante");
    check(cuenta(doc, "#tarjetas .match-card") === Math.min(4, nJugadores),
      "tarjetas destacadas del top 4");
    check(doc.querySelector('#cuerpo a[href^="perfil.html?j="]') !== null,
      "enlaza al perfil de cada jugador");
    if (lider.distintivo) {
      check(texto(doc, "#cuerpo").includes(lider.distintivo),
        `el distintivo del líder (${lider.distintivo}) aparece en la tabla de participantes`);
    }
  }

  console.log("\n═══ perfil.html ═══");
  {
    const { doc, errores } = await render("perfil.html", `?j=${lider.slug}`);
    check(errores.length === 0, `sin errores de JS ${errores[0] || ""}`);
    check(doc.querySelector("#selector-jugador").value === lider.slug,
      "respeta el jugador pedido por la URL");
    if (lider.distintivo) {
      check(doc.querySelector(`#selector-jugador option[value="${lider.slug}"]`)?.textContent.includes(lider.distintivo),
        `el distintivo del líder (${lider.distintivo}) aparece en el selector de perfil`);
    }
    check(cuenta(doc, "#tarjetas .match-card") === 8, "8 tarjetas de estadísticas");
    check(doc.querySelector("#grafico svg") !== null, "dibuja el gráfico de evolución");
    check(cuenta(doc, "#grafico svg circle") === lider.jornadas_jugadas,
      `un punto por jornada jugada (${lider.jornadas_jugadas})`);

    const filas = doc.querySelectorAll("#cuerpo-jornadas tr");
    check(filas.length === lider.jornadas_jugadas, "tabla jornada a jornada completa");
    const ultimo = +filas[filas.length - 1].lastElementChild.textContent;
    check(ultimo === lider.puntos_totales,
      `el acumulado final (${ultimo}) coincide con la clasificación (${lider.puntos_totales})`);
  }

  console.log("\n═══ carrera.html ═══");
  {
    const { doc, dom, errores } = await render("carrera.html");
    check(errores.length === 0, `sin errores de JS ${errores[0] || ""}`);
    check(doc.querySelector("#grafico svg") !== null, "dibuja el gráfico");
    check(cuenta(doc, "#grafico svg path") === nJugadores, "una línea por jugador");
    check(cuenta(doc, "#marcador .fila-jugador") === nJugadores, "una fila en el marcador por jugador");
    check(+doc.querySelector("#barra").max === clas.jornadas_calculadas.length - 1,
      "la barra cubre todas las jornadas calculadas");
    const filaLider = doc.querySelector(`#total-${lider.slug}`);
    check(filaLider && +filaLider.textContent === lider.puntos_totales,
      "en la última jornada el líder muestra su total real en el marcador");
    check(doc.querySelector(`#puesto-${lider.slug}`).textContent === "1",
      "el líder aparece en el puesto 1 del marcador");
    if (lider.distintivo) {
      check(doc.querySelector(`#fila-${lider.slug} .nombre`)?.textContent.includes(lider.distintivo),
        `el distintivo del líder (${lider.distintivo}) aparece en su fila del marcador de carrera`);
    }

    const barra = doc.querySelector("#barra");
    barra.value = "0";
    barra.dispatchEvent(new dom.window.Event("input"));
    await new Promise((r) => setTimeout(r, 80));
    const primera = parseInt(clas.jornadas_calculadas[0].slice(1));
    check(texto(doc, "#etiqueta") === `Jornada ${primera}`, "la barra viaja a la primera jornada");
    check(cuenta(doc, "#marcador .fila-jugador") === nJugadores, "el marcador se conserva al mover la barra");
    check(cuenta(doc, "#grafico svg path") === nJugadores, "el gráfico se repinta");
  }

  console.log("\n═══ reglamento.html ═══");
  {
    const { doc, errores } = await render("reglamento.html");
    const s = leer("config/settings.json");
    check(errores.length === 0, `sin errores de JS ${errores[0] || ""}`);
    check(cuenta(doc, "#contenido details") >= 10, "todas las secciones de normas");
    const todo = texto(doc, "#contenido");
    const exacto = s.puntuaciones.puntos_1x2 + s.puntuaciones.puntos_exacto;
    check(todo.includes(`${exacto} puntos`), `calcula que un exacto vale ${exacto} puntos`);
    check(todo.includes(`${Math.round(s.puntuaciones.porcentaje_minimo_participacion * 100)} %`),
      "muestra el umbral de participación desde settings.json");
    check(todo.includes("Ejemplo"), "incluye el ejemplo numérico de una jornada");
    check(todo.includes("Preguntas frecuentes"), "incluye las preguntas frecuentes");
    check(cuenta(doc, "#contenido .latest-grid .match-card") === 3,
      "el ejemplo compara tres casos");
  }

  console.log("\n" + "─".repeat(62));
  if (fallos.length) {
    console.log(`❌ ${fallos.length} comprobación(es) fallida(s):`);
    fallos.forEach((f) => console.log("   · " + f));
    process.exit(1);
  }
  console.log("✅ Todas las vistas renderizan correctamente.");
})();
