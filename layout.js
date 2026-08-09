/* Cabecera, navegación y utilidades compartidas. */

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
      <h1>${titulo}</h1>
      ${subtitulo ? `<p class="subtitulo">${subtitulo}</p>` : ""}
      <nav class="top-nav">${enlaces}</nav>
    </header>
  `);
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

/* Mismo esquema que ofuscar_marcador/desofuscar_marcador en scripts/utils.py —
   tienen que coincidir símbolo a símbolo. NO es cifrado real: la clave y el
   esquema viven en este mismo fichero, público en el navegador de cualquiera,
   así que alguien con conocimientos técnicos podría revertirlo abriendo la
   consola. Lo que sí evita es que el marcador se lea a simple vista al abrir
   el JSON o al reenviarlo por WhatsApp — que es todo lo que se pedía.

   El byte ofuscado (XOR con la clave) no se codifica en Base64 normal, porque
   "QkJD" se reconoce como Base64 a simple vista. En su lugar cada byte se
   parte en dos mitades de 4 bits y cada mitad se sustituye por un símbolo de
   esta tabla — dígitos arábigos y caracteres chinos, no letras latinas — y
   luego se intercalan símbolos de "ruido" que no significan nada y se
   descartan al descodificar, más un prefijo/sufijo decorativos fijos. */
const CLAVE_OFUSCACION = "porra-liga-2026-no-copies";
const NIBBLES_OFUSCACION = ["٠", "١", "٢", "٣", "٤", "٥", "٦", "٧", "٨", "٩", "山", "水", "火", "木", "金", "土"];
const RUIDO_OFUSCACION = ["٧", "八", "٣", "九", "٥", "二", "٩", "龍"];
const PREFIJO_OFUSCACION = "٤٩٠";
const SUFIJO_OFUSCACION = "水火";

function ofuscarMarcador(gl, gv) {
  const texto = `${gl}-${gv}`;
  const xor = [];
  for (let i = 0; i < texto.length; i++) {
    xor.push(texto.charCodeAt(i) ^ CLAVE_OFUSCACION.charCodeAt(i % CLAVE_OFUSCACION.length));
  }
  let nucleo = "";
  for (const b of xor) nucleo += NIBBLES_OFUSCACION[b >> 4] + NIBBLES_OFUSCACION[b & 15];
  let conRuido = "";
  for (let i = 0; i < nucleo.length; i += 2) {
    conRuido += nucleo.slice(i, i + 2) + RUIDO_OFUSCACION[(i / 2) % RUIDO_OFUSCACION.length];
  }
  return PREFIJO_OFUSCACION + conRuido + SUFIJO_OFUSCACION;
}

function desofuscarMarcador(token) {
  const cuerpo = SUFIJO_OFUSCACION
    ? token.slice(PREFIJO_OFUSCACION.length, -SUFIJO_OFUSCACION.length)
    : token.slice(PREFIJO_OFUSCACION.length);
  let nucleo = "";
  for (let i = 0; i < cuerpo.length; i += 3) nucleo += cuerpo.slice(i, i + 2);
  const bytes = [];
  for (let i = 0; i < nucleo.length; i += 2) {
    bytes.push(NIBBLES_OFUSCACION.indexOf(nucleo[i]) * 16 + NIBBLES_OFUSCACION.indexOf(nucleo[i + 1]));
  }
  let texto = "";
  for (let i = 0; i < bytes.length; i++) {
    texto += String.fromCharCode(bytes[i] ^ CLAVE_OFUSCACION.charCodeAt(i % CLAVE_OFUSCACION.length));
  }
  const [gl, gv] = texto.split("-").map(Number);
  return { gl, gv };
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
