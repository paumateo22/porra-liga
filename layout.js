/* Cabecera, navegación y utilidades compartidas. */

/* Google Analytics (GA4) — mide visitas, páginas vistas y visitantes únicos,
   sin servidor: funciona igual en GitHub Pages que en local.

   Para activarlo:
   1. Ve a https://analytics.google.com, crea una cuenta (o usa una que ya
      tengas) y dentro de ella una "propiedad" para esta web.
   2. Te da un "ID de medición" con forma G-XXXXXXXXXX. Pégalo abajo.
   3. Haz push. En un par de minutos ya puedes ver las visitas en tiempo
      real dentro de Analytics — no hace falta tocar nada más en el código.

   Con el ID vacío (como está por defecto) no se carga nada — así en local,
   mientras desarrollas, no ensucias tus propias estadísticas de visitas. */
const GA_MEASUREMENT_ID = "";

function montarAnalytics() {
  if (!GA_MEASUREMENT_ID) return;

  const script = document.createElement("script");
  script.async = true;
  script.src = `https://www.googletagmanager.com/gtag/js?id=${GA_MEASUREMENT_ID}`;
  document.head.appendChild(script);

  window.dataLayer = window.dataLayer || [];
  function gtag() { window.dataLayer.push(arguments); }
  gtag("js", new Date());
  // Sin datos personales: no hace falta pedir consentimiento de cookies
  // para una porra de amigos, pero por si acaso se pide a Google que
  // anonimice cualquier rastro que pudiera identificar a alguien.
  gtag("config", GA_MEASUREMENT_ID, { anonymize_ip: true });
  window.gtag = gtag;
}

const PAGINAS = [
  { id: "clasificacion", texto: "🏆 Clasificación", href: "index.html", principal: true },
  { id: "calendario", texto: "📅 Calendario", href: "calendario.html", principal: true },
  { id: "pronosticar", texto: "✍️ Pronosticar", href: "pronosticar.html", principal: true },
  { id: "analisis", texto: "🔍 Análisis", href: "analisis.html", principal: true },
  { id: "carrera", texto: "📈 Carrera", href: "carrera.html" },
  { id: "participantes", texto: "👥 Participantes", href: "participantes.html" },
  { id: "reglamento", texto: "📜 Reglamento", href: "reglamento.html" },
];

function montarCabecera({ titulo, subtitulo, pagina }) {
  montarAnalytics();
  const enlaces = PAGINAS
    .filter((p) => p.principal || p.id === pagina)
    .map((p) => `<a href="${p.href}"${p.id === pagina ? ' class="home-btn"' : ""}>${p.texto}</a>`)
    .join("");

  document.body.insertAdjacentHTML("afterbegin", `
    <div id="menu-lateral" class="sidenav">
      <a href="javascript:void(0)" class="closebtn" onclick="cerrarMenu()">&times;</a>
      ${PAGINAS.map((p) => `<a href="${p.href}">${p.texto}</a>`).join("")}
    </div>
    <span class="menu-btn" onclick="abrirMenu()">&#9776;</span>
    <header>
      <div class="cabecera-interior">
        <div id="widgets-izquierda" class="widgets-lado"></div>
        <div class="cabecera-centro">
          <h1>${titulo}</h1>
          ${subtitulo ? `<p class="subtitulo">${subtitulo}</p>` : ""}
          <nav class="top-nav">${enlaces}</nav>
        </div>
        <div id="widgets-derecha" class="widgets-lado"></div>
      </div>
    </header>
  `);

  montarWidgetsCabecera();
}

function abrirMenu() {
  document.getElementById("menu-lateral").style.width = "250px";
}

function cerrarMenu() {
  document.getElementById("menu-lateral").style.width = "0";
}

/* ---------- Datos ---------- */

async function cargar(ruta, porDefecto = null) {
  try {
    const r = await fetch(`${ruta}?v=${Date.now()}`, { cache: "no-store" });
    if (!r.ok) return porDefecto;
    return await r.json();
  } catch (e) {
    return porDefecto;
  }
}

const ordenJornadas = (claves) => claves.sort((a, b) => parseInt(a.slice(1)) - parseInt(b.slice(1)));

function formatearFecha(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  return d.toLocaleString("es-ES", {
    weekday: "short", day: "numeric", month: "short",
    hour: "2-digit", minute: "2-digit",
  });
}

function formatearHora(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d)) return "";
  return d.toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" });
}

/* Fecha compacta para mostrar junto al marcador/hora de cada partido, sin
   el día de la semana ni el año: "15 ago". */
function formatearFechaCorta(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d)) return "";
  return d.toLocaleDateString("es-ES", { day: "numeric", month: "short" });
}

/* Fecha + hora en una sola línea: "5 ago - 19:30". Para que la hora no
   desaparezca sin más en cuanto el partido se juega (cuando el hueco central
   pasa a mostrar el resultado en vez de la hora), se pone aquí arriba junto
   a la fecha, siempre visible, se haya jugado el partido o no. */
function formatearFechaHora(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d)) return "";
  const fecha = d.toLocaleDateString("es-ES", { day: "numeric", month: "short" });
  const hora = d.toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" });
  return `${fecha} - ${hora}`;
}

/* Marcador de un partido según su estado real — un solo criterio para toda
   la web, en vez de cada página decidiendo por su cuenta:
   - sin empezar ("notstarted" o sin dato): un guion.
   - en directo ("inprogress", o cualquier otra cosa que no sea "notstarted"
     ni "finished" — SofaScore usa varios matices de "en juego"): el marcador
     actual con un balón animado al lado.
   - terminado ("finished"): el resultado final, tal cual.
   Devuelve HTML listo para insertar. */
function marcadorPartido(real) {
  const estado = real?.estado;
  if (estado === "finished") {
    return `<span class="marcador">${real.goles_local}-${real.goles_visitante}</span>`;
  }
  if (estado && estado !== "notstarted") {
    const gl = real.goles_local ?? 0, gv = real.goles_visitante ?? 0;
    return `<span class="marcador en-directo">${gl}-${gv} <span class="balon-directo" title="En directo">⚽</span></span>`;
  }
  return `<span class="marcador">-</span>`;
}

/* true si el partido está siendo jugado ahora mismo. */
function esPartidoEnDirecto(real) {
  const estado = real?.estado;
  return !!estado && estado !== "notstarted" && estado !== "finished";
}

/* Como this.scrollIntoView no existe en todos los entornos (algunos navegadores
   embebidos, y el jsdom que usamos para probar, ni siquiera lo definen como
   función vacía), un simple "?.scrollIntoView(...)" revienta en cuanto el
   elemento SÍ se encuentra — el "?." solo protege contra elemento nulo, no
   contra método inexistente. */
function desplazarSiExiste(elemento, opciones) {
  if (elemento && typeof elemento.scrollIntoView === "function") {
    elemento.scrollIntoView(opciones);
  }
}

/* Jornada "actual": la primera que aún tenga partidos sin terminar. Si no hay
   ningún dato de resultados para una jornada (temporada recién reseteada,
   antes de correr el extractor), se trata como "sin empezar" en vez de
   saltarla — si no, un array vacío nunca cumple el .some() de abajo y la
   función acaba devolviendo la última jornada por error. */
function jornadaActual(realidad, claves) {
  for (const c of claves) {
    const partidos = realidad[c];
    if (!partidos || !partidos.length || partidos.some((p) => p.estado !== "finished")) return c;
  }
  return claves[claves.length - 1];
}

/* Insignias (🏆, ⭐...) que el admin le haya puesto a un jugador desde
   config/nombres.txt. El objeto viene de clasificacion.json o de
   data/analisis/*.json, ambos llevan "insignias": [{emoji, descripcion}, ...]
   (lista vacía si no tiene ninguna). Son acumulables: pueden ser varias. */

/* Para <option>, texto de SVG y sitios donde no se puede meter HTML: el
   nombre seguido de los emojis pegados, sin tooltip clicable (los desplegables
   y el texto SVG no admiten spans interactivos dentro). */
function nombrePlano(c) {
  const emojis = (c.insignias || []).map((i) => i.emoji).join("");
  return emojis ? `${c.nombre} ${emojis}` : c.nombre;
}

/* Para celdas de tabla, enlaces y cualquier sitio con HTML de verdad: cada
   insignia es un span con su descripción en el "title" (aparece al pasar el
   cursor) y también accesible tocándola/haciéndole clic (mostrarInsigniaPopover),
   para que funcione igual en móvil que en escritorio. */
function nombreConInsignias(c) {
  const insignias = c.insignias || [];
  if (!insignias.length) return c.nombre;
  const badges = insignias.map((ins) => {
    const desc = String(ins.descripcion || "").replace(/"/g, "&quot;");
    return `<span class="insignia-jugador" title="${desc}" data-desc="${desc}" onclick="mostrarInsigniaPopover(event)">${ins.emoji}</span>`;
  }).join(" ");
  return `${c.nombre} ${badges}`;
}

/* Nombre (con sus insignias) siempre como atajo a su perfil — para usar en
   cualquier sitio donde aparezca un jugador: tablas, carteles, marcadores...
   Las insignias siguen siendo clicables por su cuenta (su propio manejador ya
   corta la propagación y cancela la navegación del enlace, así que tocar una
   insignia muestra su burbuja en vez de irse al perfil). */
function enlaceNombre(c, claseExtra = "") {
  return `<a href="perfil.html?j=${c.slug}" class="enlace-jugador ${claseExtra}">${nombreConInsignias(c)}</a>`;
}

/* Al tocar/hacer clic en una insignia: muestra su descripción en una burbuja
   flotante durante unos segundos. No navega el enlace que la contenga ni
   dispara el onclick del elemento padre (por ejemplo, la fila de la carrera). */
function mostrarInsigniaPopover(evento) {
  evento.preventDefault();
  evento.stopPropagation();
  document.querySelectorAll(".insignia-popover").forEach((el) => el.remove());
  const texto = evento.currentTarget.dataset.desc;
  if (!texto) return;
  const pop = document.createElement("div");
  pop.className = "insignia-popover";
  pop.textContent = texto;
  const rect = evento.currentTarget.getBoundingClientRect();
  pop.style.position = "fixed";
  pop.style.left = Math.max(4, rect.left) + "px";
  pop.style.top = (rect.bottom + 6) + "px";
  document.body.appendChild(pop);
  setTimeout(() => pop.remove(), 3000);
  document.addEventListener("click", () => pop.remove(), { once: true });
}

/* Barra de jornadas: casillas numeradas + flechas que desplazan la tira.
   Se monta una vez sobre un contenedor vacío y devuelve un control con
   marcarActiva(clave) para sincronizar el resaltado desde fuera. */
function montarBarraJornadas(idContenedor, claves, claveInicial, onSeleccion) {
  const cont = document.getElementById(idContenedor);
  cont.className = "barra-jornadas";
  cont.innerHTML = `
    <button type="button" class="flecha-jornada" data-dir="-1" aria-label="Jornadas anteriores">‹</button>
    <div class="pista-jornadas"></div>
    <button type="button" class="flecha-jornada" data-dir="1" aria-label="Jornadas siguientes">›</button>`;

  const pista = cont.querySelector(".pista-jornadas");
  pista.innerHTML = claves
    .map((c) => `<button type="button" class="celda-jornada-nav" data-clave="${c}">${parseInt(c.slice(1))}</button>`)
    .join("");

  pista.querySelectorAll("button").forEach((btn) => {
    btn.onclick = () => onSeleccion(btn.dataset.clave);
  });
  cont.querySelectorAll(".flecha-jornada").forEach((btn) => {
    btn.onclick = () => pista.scrollBy({ left: parseInt(btn.dataset.dir) * 180, behavior: "smooth" });
  });

  function marcarActiva(clave) {
    pista.querySelectorAll("button").forEach((b) => b.classList.toggle("activa", b.dataset.clave === clave));
    // "nearest" (no "center"): si la casilla ya cabe en lo que se ve, no toca el
    // scroll. Centrar siempre recortaba el arranque de la tira y daba la
    // sensación de que faltaba la jornada 1 aunque solo estuviera detrás del borde.
    pista.querySelector(".activa")?.scrollIntoView?.({ inline: "nearest", block: "nearest", behavior: "smooth" });
  }

  marcarActiva(claveInicial);
  return { marcarActiva };
}

/* Escudo de equipo vía la CDN pública de imágenes de SofaScore.
   Si falla la carga (CDN caída, bloqueo de hotlinking, id incorrecto...) no
   desaparece sin más: se sustituye por una insignia con las iniciales del
   equipo, para que el hueco nunca quede vacío ni descuadre el layout. */
function escudoHtml(idEscudo, alt, tamano = 22) {
  if (!idEscudo) return "";
  const nombreSeguro = String(alt || "").replace(/"/g, "&quot;");
  return `<img class="escudo" width="${tamano}" height="${tamano}"
    src="https://img.sofascore.com/api/v1/team/${idEscudo}/image"
    alt="" title="${nombreSeguro}" data-nombre="${nombreSeguro}"
    loading="lazy" referrerpolicy="no-referrer"
    onerror="marcarEscudoRoto(this)">`;
}

function marcarEscudoRoto(img) {
  const nombre = img.dataset.nombre || "";
  const tam = img.width || 22;
  const span = document.createElement("span");
  span.className = "escudo-fallback";
  span.title = nombre;
  span.textContent = nombre.trim().slice(0, 3).toUpperCase();
  span.style.width = tam + "px";
  span.style.height = tam + "px";
  span.style.fontSize = Math.round(tam * 0.36) + "px";
  img.replaceWith(span);
}

/* ───────────────────── Widgets de la cabecera ─────────────────────
   Próximo partido, próxima jornada, último resultado y partido en directo,
   visibles en todas las páginas (colgados de montarCabecera). Se cargan sus
   propios datos, independientemente de lo que cada página necesite para lo
   suyo — así no hay que tocar cada página una por una. */

let _intervaloCuentasAtras = null;

async function montarWidgetsCabecera() {
  const contIzq = document.getElementById("widgets-izquierda");
  const contDer = document.getElementById("widgets-derecha");
  if (!contIzq || !contDer) return;

  const calendario = await cargar("config/calendario.json", {});
  const realidad = await cargar("data/resultados/realidad_oficial.json", {});
  const claves = ordenJornadas(Object.keys(calendario));
  if (!claves.length) return; // sin calendario todavía (temporada recién reseteada)

  // Todos los partidos de la temporada en una sola lista plana, con su
  // resultado real fusionado (si lo hay) y la jornada a la que pertenecen.
  const todos = [];
  for (const clave of claves) {
    const reales = Object.fromEntries((realidad[clave] || []).map((r) => [r.id, r]));
    for (const p of calendario[clave] || []) {
      todos.push({ ...p, ...(reales[p.id] || {}), jornada: clave });
    }
  }

  const porFecha = (a, b) => new Date(a.fecha) - new Date(b.fecha);
  const sinEmpezar = todos.filter((p) => (p.estado || "notstarted") === "notstarted").sort(porFecha);
  const proximo = sinEmpezar[0] || null;
  const enDirecto = todos.find((p) => esPartidoEnDirecto(p)) || null;
  const ultimoTerminado = todos
    .filter((p) => p.estado === "finished")
    .sort((a, b) => new Date(b.fecha) - new Date(a.fecha))[0] || null;

  // La próxima jornada que ni siquiera ha empezado. Si la jornada "actual"
  // (la que jornadaActual() ve como la que toca) todavía no tiene ningún
  // partido arrancado, ES ella misma la próxima — no hay que saltar a la
  // siguiente solo porque sea "la actual". Solo se busca una posterior
  // cuando la actual ya está en marcha de verdad.
  const claveActual = jornadaActual(realidad, claves);
  const idxActual = claves.indexOf(claveActual);
  const actualYaEmpezada = (realidad[claveActual] || []).some((r) => (r.estado || "notstarted") !== "notstarted");
  const claveProximaJornada = actualYaEmpezada
    ? claves.slice(idxActual + 1).find((c) =>
        (realidad[c] || []).every((r) => (r.estado || "notstarted") === "notstarted")
      ) || null
    : claveActual;
  const primerPartidoProximaJornada = claveProximaJornada
    ? (calendario[claveProximaJornada] || []).slice().sort(porFecha)[0]
    : null;

  contIzq.innerHTML = `
    ${_widgetPartido("Próximo partido", proximo, true)}
    ${_widgetJornada("Próxima jornada", claveProximaJornada, primerPartidoProximaJornada)}`;
  contDer.innerHTML = `
    ${_widgetPartido("Último resultado", ultimoTerminado, false)}
    ${enDirecto
      ? _widgetPartido("🔴 En directo", enDirecto, false)
      : _widgetPartido("Próximo partido", proximo, true)}`;

  _iniciarCuentasAtras();
}

function _widgetPartido(titulo, p, conCuentaAtras) {
  if (!p) {
    return `<div class="widget-cabecera"><div class="widget-titulo">${titulo}</div>
      <div class="nota">No hay ningún partido que mostrar.</div></div>`;
  }
  const jornadaNum = parseInt(p.jornada.slice(1));
  const pendiente = (p.estado || "notstarted") === "notstarted";
  return `
    <div class="widget-cabecera">
      <div class="widget-titulo">${titulo}</div>
      <div class="widget-fecha">Jornada ${jornadaNum} · ${formatearFechaHora(p.fecha)}</div>
      <div class="widget-partido">
        <span class="equipo-widget">${escudoHtml(p.id_escudo_local, p.local, 26)}<span>${p.local}</span></span>
        ${marcadorPartido(p)}
        <span class="equipo-widget"><span>${p.visitante}</span>${escudoHtml(p.id_escudo_visitante, p.visitante, 26)}</span>
      </div>
      ${conCuentaAtras && pendiente ? `<div class="cuenta-atras" data-fecha="${p.fecha}">calculando…</div>` : ""}
    </div>`;
}

function _widgetJornada(titulo, clave, primerPartido) {
  if (!clave || !primerPartido) {
    return `<div class="widget-cabecera"><div class="widget-titulo">${titulo}</div>
      <div class="nota">No hay ninguna jornada pendiente.</div></div>`;
  }
  return `
    <div class="widget-cabecera">
      <div class="widget-titulo">${titulo}</div>
      <div class="widget-fecha">Jornada ${parseInt(clave.slice(1))} · comienza ${formatearFechaHora(primerPartido.fecha)}</div>
      <div class="cuenta-atras" data-fecha="${primerPartido.fecha}">calculando…</div>
      <a href="pronosticar.html?jornada=${clave}" class="widget-atajo">✏️ Pronosticar esta jornada</a>
    </div>`;
}

/* Cuenta atrás en vivo, actualizada cada segundo, para cualquier elemento
   con la clase "cuenta-atras" y un atributo data-fecha con la hora destino
   en ISO. Se reinicia cada vez que se repintan los widgets, para no
   acumular temporizadores duplicados de una vuelta a otra. */
function _iniciarCuentasAtras() {
  if (_intervaloCuentasAtras) clearInterval(_intervaloCuentasAtras);

  const actualizar = () => {
    const ahora = Date.now();
    document.querySelectorAll(".cuenta-atras[data-fecha]").forEach((el) => {
      const restante = new Date(el.dataset.fecha).getTime() - ahora;
      if (restante <= 0) { el.textContent = "🔴 ¡Ya está en juego!"; return; }

      const s = Math.floor(restante / 1000);
      const dias = Math.floor(s / 86400);
      const horas = Math.floor((s % 86400) / 3600);
      const minutos = Math.floor((s % 3600) / 60);
      const segundos = s % 60;
      const dos = (n) => String(n).padStart(2, "0");

      el.textContent = dias > 0
        ? `⏳ ${dias}d ${dos(horas)}h ${dos(minutos)}m ${dos(segundos)}s`
        : `⏳ ${dos(horas)}:${dos(minutos)}:${dos(segundos)}`;
    });
  };

  actualizar();
  _intervaloCuentasAtras = setInterval(actualizar, 1000);
}


/* ───────────────────── Generación de imágenes (canvas) ─────────────────────
   Usadas por analisis.html e index.html para exportar/copiar capturas. No se
   usa ninguna librería: solo Canvas 2D nativo. */

/* Los escudos vienen del CDN de SofaScore. Si su servidor no permite el uso
   en canvas entre dominios (CORS), el navegador "mancha" el lienzo y
   exportarlo (descargar/copiar) lanza un error de seguridad — por eso se
   intenta cargar con crossOrigin, y quien llame a esto debe estar listo
   para repetir el dibujo sin escudos si la exportación falla igualmente. */
async function cargarImagenEscudo(idEscudo) {
  if (!idEscudo) return null;
  return new Promise((resolve) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => resolve(img);
    img.onerror = () => resolve(null);
    img.src = `https://img.sofascore.com/api/v1/team/${idEscudo}/image`;
  });
}

function recortarTexto(ctx, texto, anchoMax) {
  if (ctx.measureText(texto).width <= anchoMax) return texto;
  let recortado = texto;
  while (recortado.length > 1 && ctx.measureText(recortado + "…").width > anchoMax) {
    recortado = recortado.slice(0, -1);
  }
  return recortado + "…";
}

/* canvas.toBlob() envuelto en una promesa, para poder usar await. */
function canvasABlob(canvas) {
  return new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
}
