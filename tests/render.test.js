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
      // jsdom no implementa requestAnimationFrame; un no-op basta para las
      // comprobaciones estáticas (no ejecutamos varios fotogramas aquí).
      win.requestAnimationFrame = win.requestAnimationFrame || (() => 0);
      // jsdom tampoco implementa canvas 2D de verdad ni la API del
      // portapapeles — con un contexto falso que registra las llamadas basta
      // para comprobar que la lógica de dibujo no revienta y usa los datos
      // correctos, sin necesitar el paquete nativo "canvas".
      win.__llamadasCanvas = { fillText: [], fillRect: [], drawImage: [] };
      win.HTMLCanvasElement.prototype.getContext = function (tipo) {
        if (tipo !== "2d") return null;
        return {
          fillRect: (...a) => win.__llamadasCanvas.fillRect.push(a),
          fillText: (...a) => win.__llamadasCanvas.fillText.push(a),
          drawImage: (...a) => win.__llamadasCanvas.drawImage.push(a),
          measureText: (t) => ({ width: t.length * 8 }),
          createLinearGradient: () => ({ addColorStop: () => {} }),
          set fillStyle(v) {}, set font(v) {}, set textAlign(v) {},
        };
      };
      win.HTMLCanvasElement.prototype.toDataURL = () => "data:image/png;base64,FALSO";
      win.HTMLCanvasElement.prototype.toBlob = function (cb) { cb(new win.Blob(["x"], { type: "image/png" })); };
      win.ClipboardItem = win.ClipboardItem || class { constructor(o) { this.o = o; } };
      // jsdom trae su propio Image que NUNCA dispara onload/onerror de
      // verdad (no carga nada por red) — hay que sustituirlo sin "||",
      // o la promesa que espera la carga de escudos se queda colgada para
      // siempre. Este stub falso dispara onload al instante.
      win.Image = class {
        set src(v) { this._src = v; setTimeout(() => this.onload && this.onload(), 0); }
        get src() { return this._src; }
      };
      win.navigator.clipboard = win.navigator.clipboard || { write: async () => {} };
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
    check(docCal.querySelectorAll(".widget-cabecera").length === 4,
      "los widgets de cabecera siguen apareciendo aunque no haya resultados ni clasificación todavía");

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
    check(doc.querySelector(`#cuerpo-resumen a[href="perfil.html?j=${lider.slug}"]`) !== null,
      "el nombre en la clasificación es un atajo a su perfil");
    if (lider.insignias && lider.insignias.length) {
      const primeraInsignia = lider.insignias[0];
      check(texto(doc, "#cuerpo-resumen tr td:nth-child(2)").includes(primeraInsignia.emoji),
        `la insignia del líder (${primeraInsignia.emoji}) aparece junto a su nombre`);
      check(doc.querySelector("#cuerpo-resumen .insignia-jugador")?.title === primeraInsignia.descripcion,
        "la descripción de la insignia va en el atributo title (tooltip al pasar el cursor)");
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

  console.log("\n═══ index.html · flechas de movimiento en la clasificación ═══");
  {
    // Fixture aislado con movimiento real y verificable a mano: tras J01,
    // Ana 1ª / Bruno 2º / Clara 3ª. En J02, Clara remonta mucho y Ana se
    // hunde, así que el orden final tiene que quedar Clara / Bruno / Ana —
    // exactamente lo que deben reflejar las flechas al comparar con J01
    // (que es la jornada anterior a la última, J02, que está cerrada).
    const rutaClas = path.join(RAIZ, "data/clasificacion.json");
    const rutaAnalisisDir = path.join(RAIZ, "data/analisis");
    const backupClas = fs.existsSync(rutaClas) ? fs.readFileSync(rutaClas) : null;
    const backupAnalisisDir = rutaAnalisisDir + ".bak";
    if (fs.existsSync(rutaAnalisisDir)) fs.renameSync(rutaAnalisisDir, backupAnalisisDir);
    fs.mkdirSync(rutaAnalisisDir);

    const porJornada = (puntos, ganador) => ({ puntos, ganador, aciertos_1x2: 0, aciertos_exactos: 0 });
    const fixture = {
      competicion: "Prueba", generado: new Date().toISOString(), desempates: ["jornadas_ganadas"],
      jornadas_calculadas: ["J01", "J02"],
      clasificacion: [
        { puesto: 1, slug: "clara", nombre: "Clara", insignias: [], puntos_totales: 31, punto_partida: 0,
          aciertos_exactos: 13, aciertos_1x2: 13, bonus_rendimiento: 0, jornadas_ganadas: 1, jornadas_perdidas: 0,
          por_jornada: { J01: porJornada(6, false), J02: porJornada(25, true) } },
        { puesto: 2, slug: "bruno", nombre: "Bruno", insignias: [], puntos_totales: 26, punto_partida: 0,
          aciertos_exactos: 13, aciertos_1x2: 13, bonus_rendimiento: 0, jornadas_ganadas: 0, jornadas_perdidas: 0,
          por_jornada: { J01: porJornada(12, false), J02: porJornada(14, false) } },
        { puesto: 3, slug: "ana", nombre: "Ana", insignias: [], puntos_totales: 20, punto_partida: 0,
          aciertos_exactos: 9, aciertos_1x2: 9, bonus_rendimiento: 0, jornadas_ganadas: 1, jornadas_perdidas: 1,
          por_jornada: { J01: porJornada(18, true), J02: porJornada(2, false) } },
      ],
    };
    fs.writeFileSync(rutaClas, JSON.stringify(fixture, null, 2));
    fs.writeFileSync(path.join(rutaAnalisisDir, "J01.json"), JSON.stringify({ cerrada: true }));
    fs.writeFileSync(path.join(rutaAnalisisDir, "J02.json"), JSON.stringify({ cerrada: true }));

    try {
      const { doc, errores } = await render("index.html");
      check(errores.length === 0, `sin errores de JS ${errores[0] || ""}`);
      const filas = [...doc.querySelectorAll("#cuerpo-resumen tr")].map((f) => f.textContent.replace(/\s+/g, " ").trim());
      check(filas[0]?.includes("Clara") && filas[0]?.includes("▲ +2"),
        `Clara sube 2 puestos (3ª → 1ª): "${filas[0]}"`);
      check(filas[1]?.includes("Bruno") && filas[1]?.includes("—"),
        `Bruno se mantiene igual (2º → 2º): "${filas[1]}"`);
      check(filas[2]?.includes("Ana") && filas[2]?.includes("▼ -2"),
        `Ana baja 2 puestos (1ª → 3ª): "${filas[2]}"`);
    } finally {
      if (backupClas) fs.writeFileSync(rutaClas, backupClas); else fs.unlinkSync(rutaClas);
      fs.rmSync(rutaAnalisisDir, { recursive: true, force: true });
      fs.renameSync(backupAnalisisDir, rutaAnalisisDir);
    }
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

    check(cuenta(doc, "header .widget-cabecera") === 4,
      "los 4 widgets de la cabecera aparecen dentro del <header>, no debajo");
    check(doc.querySelector("header .cabecera-interior .widgets-lado") !== null,
      "los widgets viven a los lados del título, dentro del fondo azul");

    // La jornada "actual" (la primera con algo pendiente) puede no haber
    // arrancado ningún partido todavía — en ese caso, "próxima jornada"
    // tiene que seguir siendo ELLA MISMA, no saltar a la siguiente solo
    // por ser "la actual".
    const actualYaEmpezada = (realidad[claveActual] || []).some((r) => r.estado && r.estado !== "notstarted");
    if (!actualYaEmpezada) {
      const widgetProxJornada = [...doc.querySelectorAll(".widget-cabecera")]
        .find((w) => texto(w, ".widget-titulo") === "Próxima jornada");
      check(texto(widgetProxJornada, ".widget-fecha").includes(`Jornada ${parseInt(claveActual.slice(1))}`),
        `"próxima jornada" sigue siendo ${claveActual} mientras no arranque ningún partido suyo`);
      check(widgetProxJornada?.querySelector(".widget-atajo")?.getAttribute("href") === `pronosticar.html?jornada=${claveActual}`,
        "el atajo de \"próxima jornada\" lleva a pronosticar esa misma jornada");
    }
    check(cuenta(doc, "#contenido .partido") === calendario[claveActual].length,
      "pinta todos los partidos de esa jornada");
    check(cuenta(doc, "#contenido .fecha-partido") === calendario[claveActual].length,
      "muestra la fecha de cada partido, no solo la hora");
    check(doc.querySelector(".enlace-analisis-jornada")?.getAttribute("href") === `analisis.html?jornada=${claveActual}`,
      "cada jornada lleva un atajo directo a su análisis");

    const cabecera = doc.querySelector(".cabecera-jornada");
    const orden = [...cabecera.children].map((c) => c.tagName);
    check(orden.length === 3 && orden[1] === "BUTTON",
      "el botón de clasificación de liga va justo en medio, entre la jornada y el contador de jugados");

    const boton = doc.querySelector(".btn-tabla-liga");
    const panel = doc.querySelector(".tabla-liga-panel");
    check(boton !== null && panel.hidden, "el panel de la tabla de liga empieza oculto");
    boton.dispatchEvent(new dom.window.Event("click"));
    check(!panel.hidden, "el botón muestra la tabla de liga al pulsarlo");

    const filasLiga = doc.querySelectorAll(".tabla-liga tbody tr");
    check(filasLiga.length === 20, `la tabla de liga tiene los 20 equipos (vio ${filasLiga.length})`);

    // Invariante cruzada: la suma de goles a favor de todos los equipos
    // tiene que coincidir con la suma de goles en contra (todo gol marcado
    // por uno lo encaja otro) — confirma que la tabla está bien calculada,
    // no solo que tiene 20 filas.
    const columnas = (fila) => [...fila.children].map((td) => td.textContent.trim());
    const sumaColumna = (idx) => [...filasLiga].reduce((s, f) => s + parseInt(columnas(f)[idx]), 0);
    check(sumaColumna(7) === sumaColumna(8),
      `los goles a favor de todos (${sumaColumna(7)}) cuadran con los goles en contra de todos (${sumaColumna(8)})`);

    boton.dispatchEvent(new dom.window.Event("click"));
    check(panel.hidden, "un segundo clic vuelve a ocultar la tabla de liga");

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

  console.log("\n═══ pronosticar.html · precarga de pronósticos ya enviados ═══");
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
      const primeraPred = guardado.predicciones.find((p) =>
        doc.querySelector(`input[data-id="${p.id}"][data-lado="l"]`));
      if (primeraPred) {
        const lInput = doc.querySelector(`input[data-id="${primeraPred.id}"][data-lado="l"]`);
        const vInput = doc.querySelector(`input[data-id="${primeraPred.id}"][data-lado="v"]`);
        check(lInput && String(lInput.value) === String(primeraPred.goles_local)
            && vInput && String(vInput.value) === String(primeraPred.goles_visitante),
          `escribir el nombre de ${jugadorPrueba.nombre} recupera sus pronósticos ya enviados `
          + `(${primeraPred.goles_local}-${primeraPred.goles_visitante})`);
      }
    }
  }

  console.log("\n═══ pronosticar.html · imagen de la jornada (PNG / portapapeles) ═══");
  {
    // El calendario de prueba (simulador) no trae ids de escudo reales — se
    // añaden unos falsos solo para esta comprobación, y se restauran al
    // terminar, para poder verificar que si HAY escudo se dibuja de verdad.
    const rutaCal = path.join(RAIZ, "config/calendario.json");
    const backupCal = fs.readFileSync(rutaCal, "utf8");
    const calConEscudos = JSON.parse(backupCal);
    for (const clave in calConEscudos) {
      calConEscudos[clave].forEach((p, i) => {
        p.id_escudo_local = 1000 + i;
        p.id_escudo_visitante = 2000 + i;
      });
    }
    fs.writeFileSync(rutaCal, JSON.stringify(calConEscudos, null, 4));

    let doc, dom, errores;
    try {
      ({ doc, dom, errores } = await render("pronosticar.html"));
    } finally {
      fs.writeFileSync(rutaCal, backupCal);
    }
    check(errores.length === 0, `sin errores de JS ${errores[0] || ""}`);

    doc.getElementById("nombre").value = "Prueba";
    const primerInput = doc.querySelector('input[data-lado="l"]:not([disabled])');
    if (primerInput) {
      primerInput.value = "3";
      doc.querySelector(`input[data-id="${primerInput.dataset.id}"][data-lado="v"]`).value = "1";
    }

    const canvas = await dom.window.dibujarImagenJornada();
    check(canvas.width === 640, "la imagen tiene un ancho fijo de 640px");
    check(dom.window.__llamadasCanvas.fillText.some(([t]) => t.includes("Prueba")),
      "la imagen incluye el nombre del jugador");
    check(dom.window.__llamadasCanvas.fillText.some(([t]) => t.includes(`Jornada ${parseInt(claveActual.slice(1))}`)
        || t.includes("Jornada")),
      "la imagen incluye la jornada");
    check(dom.window.__llamadasCanvas.fillText.some(([t]) => t === "3 - 1"),
      "el marcador relleno (3 - 1) aparece en la imagen");
    check(dom.window.__llamadasCanvas.drawImage.length === calendario[claveActual].length * 2,
      `se dibujan 2 escudos por partido (vio ${dom.window.__llamadasCanvas.drawImage.length} `
      + `de ${calendario[claveActual].length * 2} esperados)`);

    let ficheroDescargado = null;
    dom.window.HTMLAnchorElement.prototype.click = function () { ficheroDescargado = this.download; };
    await dom.window.descargarImagen();
    check(/^J\d{2}_Prueba\.png$/.test(ficheroDescargado || ""),
      `"Descargar imagen" genera un nombre de fichero .png correcto (vio "${ficheroDescargado}")`);

    let avisoTrasCopiar = "";
    await dom.window.copiarImagen();
    avisoTrasCopiar = texto(doc, "#aviso");
    check(avisoTrasCopiar.includes("portapapeles"),
      `"Copiar imagen" avisa de que se copió al portapapeles (vio "${avisoTrasCopiar}")`);
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
    const jugadorConInsignias = analisis.jugadores.find((j) => j.insignias && j.insignias.length);
    if (jugadorConInsignias) {
      check(texto(doc, "#tabla-cruzada tbody").includes(jugadorConInsignias.insignias[0].emoji),
        `la insignia (${jugadorConInsignias.insignias[0].emoji}) aparece en la tabla cruzada del análisis`);
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

    // ?jornada= en la URL (el atajo desde calendario.html) tiene que ganar
    // siempre a la jornada que se abriría por defecto.
    const claveNoDefault = clas.jornadas_calculadas.find((c) => c !== claveAnalisis) || claveAnalisis;
    const { doc: docJornada, errores: erroresJornada } = await render("analisis.html", `?jornada=${claveNoDefault}`);
    check(erroresJornada.length === 0, `?jornada= sin errores de JS ${erroresJornada[0] || ""}`);
    check(docJornada.querySelector(".celda-jornada-nav.activa")?.textContent.trim()
      === String(parseInt(claveNoDefault.slice(1))),
      `?jornada=${claveNoDefault} en la URL abre esa jornada, no la última calculada`);
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
    if (lider.insignias && lider.insignias.length) {
      check(texto(doc, "#cuerpo").includes(lider.insignias[0].emoji),
        `la insignia del líder (${lider.insignias[0].emoji}) aparece en la tabla de participantes`);
    }
  }

  console.log("\n═══ perfil.html ═══");
  {
    const { doc, errores } = await render("perfil.html", `?j=${lider.slug}`);
    check(errores.length === 0, `sin errores de JS ${errores[0] || ""}`);
    check(doc.querySelector("#selector-jugador").value === lider.slug,
      "respeta el jugador pedido por la URL");
    check(doc.querySelector("#btn-ver-pronosticos")?.getAttribute("href") === `pronosticos_jugador.html?j=${lider.slug}`,
      "el botón de acceso rápido apunta a los pronósticos del jugador seleccionado");
    check(texto(doc, "header h1").includes(lider.nombre),
      "el título de la cabecera muestra el nombre del jugador seleccionado, no un texto genérico");
    if (lider.insignias && lider.insignias.length) {
      check(doc.querySelector(`#selector-jugador option[value="${lider.slug}"]`)?.textContent.includes(lider.insignias[0].emoji),
        `la insignia del líder (${lider.insignias[0].emoji}) aparece en el selector de perfil`);
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

  console.log("\n═══ pronosticos_jugador.html ═══");
  {
    const claveEvaluada = [...clas.jornadas_calculadas]
      .sort((a, b) => parseInt(a.slice(1)) - parseInt(b.slice(1)))[0];

    const { doc, dom, errores } = await render("pronosticos_jugador.html", `?j=${lider.slug}&jornada=${claveEvaluada}`);
    check(errores.length === 0, `sin errores de JS ${errores[0] || ""}`);
    check(texto(doc, "header h1") === `🗒️ Pronósticos de ${lider.nombre}`,
      "el título muestra el nombre del jugador seleccionado, no un texto genérico");
    check(cuenta(doc, ".partido") === calendario[claveEvaluada].length,
      "pinta todos los partidos de la jornada pedida");
    check(cuenta(doc, ".linea-pronostico") === calendario[claveEvaluada].length,
      "cada partido lleva su línea de pronóstico");
    check(!texto(doc, ".lista-partidos").includes("🔒"),
      "no aparece ningún candado — los pronósticos se ven siempre, jugado el partido o no");

    const claveMax = Object.keys(calendario).sort((a, b) => parseInt(a.slice(1)) - parseInt(b.slice(1))).pop();
    const { doc: docFutura, errores: erroresFutura } = await render("pronosticos_jugador.html", `?j=${lider.slug}&jornada=${claveMax}`);
    check(erroresFutura.length === 0, `sin errores de JS en una jornada sin evaluar ${erroresFutura[0] || ""}`);
    check(!texto(docFutura, ".lista-partidos").includes("🔒"),
      `tampoco hay candados en ${claveMax}, que ni siquiera se ha evaluado`);
    check(/\d-\d/.test(texto(docFutura, ".lista-partidos")),
      `en ${claveMax} se ve al menos un marcador real (los pronósticos guardados, no bloqueados)`);

    const columnas = dom.window.getComputedStyle(doc.querySelector(".lista-partidos")).gridTemplateColumns;
    check(columnas.trim().split(/\s+/).length === 2,
      `los partidos se muestran en una cuadrícula de 2 columnas (vio "${columnas}")`);

    const totalPartidosCalendario = Object.values(calendario).reduce((s, p) => s + p.length, 0);
    doc.querySelector("#btn-todas").dispatchEvent(new dom.window.Event("click"));
    await new Promise((r) => setTimeout(r, 400));
    check(cuenta(doc, ".cabecera-jornada") === nJornadas, "'Ver todas' pinta las jornadas del calendario completo");
    check(cuenta(doc, ".partido") === totalPartidosCalendario,
      `'Ver todas' pinta los ${totalPartidosCalendario} partidos de toda la temporada`);
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
    if (lider.insignias && lider.insignias.length) {
      check(doc.querySelector(`#fila-${lider.slug} .nombre`)?.textContent.includes(lider.insignias[0].emoji),
        `la insignia del líder (${lider.insignias[0].emoji}) aparece en su fila del marcador de carrera`);

      const badge = doc.querySelector(`#fila-${lider.slug} .insignia-jugador`);
      if (badge) {
        badge.dispatchEvent(new dom.window.Event("click", { bubbles: true }));
        check(dom.window.document.querySelector(".insignia-popover")?.textContent === lider.insignias[0].descripcion,
          "al hacer clic en la insignia aparece una burbuja con su descripción");
      }
    }

    const barra = doc.querySelector("#barra");
    barra.value = "0";
    barra.dispatchEvent(new dom.window.Event("input"));
    await new Promise((r) => setTimeout(r, 80));
    const primera = parseInt(clas.jornadas_calculadas[0].slice(1));
    check(texto(doc, "#etiqueta") === `Jornada ${primera}`, "la barra viaja a la primera jornada");
    check(cuenta(doc, "#marcador .fila-jugador") === nJugadores, "el marcador se conserva al mover la barra");
    check(cuenta(doc, "#grafico svg path") === nJugadores, "el gráfico se repinta");

    // Fluidez: al reproducir, el progreso tiene que avanzar en pasitos
    // pequeños fotograma a fotograma (interpolando), no saltar de golpe de
    // una jornada entera a la siguiente.
    dom.window.alternar(); // pulsa "reproducir" con las funciones reales de la página
    const valores = [];
    let t = 1000;
    for (let i = 0; i < 20; i++) {
      t += 16; // ~16ms por fotograma, como un navegador real a 60fps
      dom.window.bucleAnimacion(t);
      valores.push(+barra.value);
    }
    const creceSiempre = valores.every((v, i) => i === 0 || v >= valores[i - 1]);
    const saltoMaximo = Math.max(...valores.slice(1).map((v, i) => v - valores[i]));
    check(creceSiempre, "la animación avanza de forma continua, nunca hacia atrás");
    check(saltoMaximo > 0 && saltoMaximo < 0.1,
      `cada fotograma avanza un paso pequeño (máximo visto: ${saltoMaximo.toFixed(4)}), no salta de jornada en jornada de golpe`);

    // Límite del eje Y: desactivado por defecto (margen de 5 respecto al
    // último, no ancla siempre en 0).
    const chkLimite = doc.getElementById("limite-cero");
    check(chkLimite && !chkLimite.checked, "el límite del eje a 0 está desactivado por defecto");

    chkLimite.checked = true;
    chkLimite.dispatchEvent(new dom.window.Event("change"));
    const minEjeConLimite = doc.querySelectorAll("#grafico svg text")[1]?.textContent;
    check(minEjeConLimite === "0", `al marcar "limitar a 0" el eje ancla en 0 (vio "${minEjeConLimite}")`);
    chkLimite.checked = false;
    chkLimite.dispatchEvent(new dom.window.Event("change"));

    // Vista centrada en un jugador: una opción por jugador además de "Nadie",
    // y al elegir uno aparece su línea de referencia con el eje en diferencias.
    const opcionesCentrar = [...doc.querySelectorAll("#centrar-en option")].map((o) => o.value);
    check(opcionesCentrar.length === nJugadores + 1,
      "el selector de centrado tiene una opción por jugador, más 'Nadie'");

    const selCentrar = doc.getElementById("centrar-en");
    selCentrar.value = lider.slug;
    selCentrar.dispatchEvent(new dom.window.Event("change"));
    check(doc.querySelector("#grafico svg line[stroke-dasharray]") !== null,
      "al centrar en un jugador aparece su línea de referencia discontinua");
    const maxEjeCentrado = doc.querySelectorAll("#grafico svg text")[0]?.textContent;
    check(/^[+-]\d+$/.test(maxEjeCentrado),
      `en modo centrado el eje muestra diferencias con signo (vio "${maxEjeCentrado}")`);
  }

  console.log("\n═══ reglamento.html ═══");
  {
    const { doc, errores } = await render("reglamento.html");
    const s = leer("config/settings.json");
    check(errores.length === 0, `sin errores de JS ${errores[0] || ""}`);
    check(cuenta(doc, "#contenido details") >= 9, "todas las secciones de normas");
    const todo = texto(doc, "#contenido");
    const exacto = s.puntuaciones.puntos_1x2 + s.puntuaciones.puntos_exacto;
    check(todo.includes(`${exacto} puntos`), `calcula que un exacto vale ${exacto} puntos`);
    check(todo.includes(`${Math.round(s.puntuaciones.porcentaje_minimo_participacion * 100)} %`),
      "muestra el umbral de participación desde settings.json");
    check(todo.includes("Preguntas frecuentes"), "incluye las preguntas frecuentes");
    check(!/\bAna\b|\bBruno\b|\bClara\b|\bElena\b|Nico Herrera|\bMateo\b/.test(todo),
      "no hay ejemplos con nombres de personas");
  }

  console.log("\n" + "─".repeat(62));
  if (fallos.length) {
    console.log(`❌ ${fallos.length} comprobación(es) fallida(s):`);
    fallos.forEach((f) => console.log("   · " + f));
    process.exit(1);
  }
  console.log("✅ Todas las vistas renderizan correctamente.");
})();
