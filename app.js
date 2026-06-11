// ===== Configuración =====
// URL del webhook de Make que devuelve el análisis de IA.
const WEBHOOK_URL = "https://hook.us2.make.com/fyb15ipw34mod42ue9crti42f1xpdx02";

// ===== Referencias del DOM =====
const btn       = document.getElementById("generate");
const btnIcon   = document.getElementById("btn-icon");
const btnLabel  = document.getElementById("btn-label");
const statusBox = document.getElementById("status");
const statusTxt = document.getElementById("status-text");
const errorBox  = document.getElementById("error");
const reportBox = document.getElementById("report");
const mdBox     = document.getElementById("md");
const reportDate= document.getElementById("report-date");
const copyBtn   = document.getElementById("copy");

let lastReportText = "";

// ===== Generar análisis =====
async function generate() {
  setLoading(true);
  hide(errorBox);
  hide(reportBox);

  // Mensajes rotativos mientras esperamos (Make + Claude puede tardar unos segundos)
  const phrases = [
    "Descargando las noticias de hoy…",
    "Leyendo los titulares de The Decoder…",
    "Claude está analizando las tendencias…",
    "Redactando el reporte ejecutivo…",
  ];
  let pi = 0;
  statusTxt.textContent = phrases[0];
  const ticker = setInterval(() => {
    pi = (pi + 1) % phrases.length;
    statusTxt.textContent = phrases[pi];
  }, 2500);

  try {
    const res = await fetch(WEBHOOK_URL, { method: "GET" });
    clearInterval(ticker);

    if (!res.ok) {
      throw new Error(`El servidor respondió con código ${res.status}`);
    }

    const text = await res.text();
    if (!text || !text.trim()) {
      throw new Error("La respuesta llegó vacía. Inténtalo de nuevo en un momento.");
    }

    lastReportText = text;
    mdBox.innerHTML = marked.parse(text);
    reportDate.textContent = "📅 " + new Date().toLocaleString("es-ES", {
      weekday: "long", day: "numeric", month: "long",
      hour: "2-digit", minute: "2-digit",
    });
    show(reportBox);
    reportBox.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (err) {
    clearInterval(ticker);
    let msg = err.message || "Ocurrió un error inesperado.";
    if (err.name === "TypeError") {
      // típico fallo de red / CORS
      msg = "No se pudo conectar con el servidor. Revisa tu conexión a internet e inténtalo de nuevo.";
    }
    errorBox.textContent = "⚠️ " + msg;
    show(errorBox);
  } finally {
    setLoading(false);
  }
}

// ===== Copiar reporte =====
async function copyReport() {
  if (!lastReportText) return;
  try {
    await navigator.clipboard.writeText(lastReportText);
    const old = copyBtn.textContent;
    copyBtn.textContent = "✅ Copiado";
    setTimeout(() => (copyBtn.textContent = old), 1800);
  } catch {
    copyBtn.textContent = "No se pudo copiar";
  }
}

// ===== Helpers de UI =====
function setLoading(on) {
  btn.disabled = on;
  if (on) {
    btnIcon.textContent = "⏳";
    btnLabel.textContent = "Generando…";
    show(statusBox, "flex");
  } else {
    btnIcon.textContent = "⚡";
    btnLabel.textContent = "Generar análisis de hoy";
    hide(statusBox);
  }
}
function show(el, display = "block") { el.classList.add("show"); el.style.display = display; }
function hide(el) { el.classList.remove("show"); el.style.display = "none"; }

btn.addEventListener("click", generate);
copyBtn.addEventListener("click", copyReport);

// ===== PWA: registro del service worker =====
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("sw.js").catch(() => {/* sin conexión: ignorar */});
  });
}

// ===== PWA: botón de instalación (Android/Chrome) =====
let deferredPrompt = null;
const installBox = document.getElementById("install");
const installBtn = document.getElementById("install-btn");

window.addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault();
  deferredPrompt = e;
  show(installBox, "flex");
});

installBtn.addEventListener("click", async () => {
  if (!deferredPrompt) return;
  deferredPrompt.prompt();
  await deferredPrompt.userChoice;
  deferredPrompt = null;
  hide(installBox);
});

window.addEventListener("appinstalled", () => hide(installBox));
