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

function _semillaContexto(fecha, jornada) {
  const contexto = `${CLAVE_OFUSCACION}#${fecha}#${jornada}`;
  let h = 0;
  for (let i = 0; i < contexto.length; i++) {
    h = (h * 131 + contexto.charCodeAt(i)) % 4294967296; // 2**32
  }
  return h;
}

function _flujoClave(fecha, jornada, longitud) {
  let x = _semillaContexto(fecha, jornada);
  const flujo = [];
  for (let i = 0; i < longitud; i++) {
    x = (1664525 * x + 1013904223) % 4294967296;
    // Byte ALTO (x >>> 24), no el bajo: con módulo potencia de 2 los bits
    // bajos de un LCG tienen un periodo cortísimo. ">>> " (sin signo) es
    // necesario porque x puede superar el rango de un entero de 32 bits con
    // signo que usa el operador ">>" normal de JS.
    flujo.push((x >>> 24) & 0xff);
  }
  return flujo;
}

function ofuscarMarcador(gl, gv, fecha, jornada) {
  const texto = `${gl}-${gv}`;
  const flujo = _flujoClave(fecha, jornada, texto.length);
  const xor = [];
  for (let i = 0; i < texto.length; i++) {
    xor.push(texto.charCodeAt(i) ^ flujo[i]);
  }
  let nucleo = "";
  for (const b of xor) nucleo += NIBBLES_OFUSCACION[b >> 4] + NIBBLES_OFUSCACION[b & 15];
  let conRuido = "";
  for (let i = 0; i < nucleo.length; i += 2) {
    conRuido += nucleo.slice(i, i + 2) + RUIDO_OFUSCACION[(i / 2) % RUIDO_OFUSCACION.length];
  }
  return PREFIJO_OFUSCACION + conRuido + SUFIJO_OFUSCACION;
}

function desofuscarMarcador(token, fecha, jornada) {
  const cuerpo = SUFIJO_OFUSCACION
    ? token.slice(PREFIJO_OFUSCACION.length, -SUFIJO_OFUSCACION.length)
    : token.slice(PREFIJO_OFUSCACION.length);
  let nucleo = "";
  for (let i = 0; i < cuerpo.length; i += 3) nucleo += cuerpo.slice(i, i + 2);
  const bytes = [];
  for (let i = 0; i < nucleo.length; i += 2) {
    bytes.push(NIBBLES_OFUSCACION.indexOf(nucleo[i]) * 16 + NIBBLES_OFUSCACION.indexOf(nucleo[i + 1]));
  }
  const flujo = _flujoClave(fecha, jornada, bytes.length);
  let texto = "";
  for (let i = 0; i < bytes.length; i++) {
    texto += String.fromCharCode(bytes[i] ^ flujo[i]);
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
