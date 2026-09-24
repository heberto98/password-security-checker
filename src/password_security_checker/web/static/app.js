"use strict";

const form = document.querySelector("#password-form");
const input = document.querySelector("#password");
const toggle = document.querySelector("#toggle-password");
const submit = document.querySelector("#analyze-button");
const submitLabel = document.querySelector("#analyze-label");
const clear = document.querySelector("#clear-button");
const error = document.querySelector("#form-error");
const status = document.querySelector("#status");
const results = document.querySelector("#results");
const panel = document.querySelector("#score-panel");
const meter = document.querySelector("#score-meter");
let controller = null;
let requestNumber = 0;

function conceal() {
  input.type = "password";
  toggle.textContent = "Mostrar";
  toggle.setAttribute("aria-pressed", "false");
}

function setBusy(busy) {
  input.disabled = busy;
  submit.disabled = busy;
  toggle.disabled = busy;
  form.setAttribute("aria-busy", String(busy));
  submitLabel.textContent = busy ? "Analizando…" : "Analizar contraseña";
}

function clearError() {
  error.hidden = true;
  error.textContent = "";
  input.removeAttribute("aria-invalid");
}

function resetResults() {
  results.hidden = true;
  document.querySelector("#findings").replaceChildren();
  document.querySelector("#recommendations").replaceChildren();
  panel.dataset.level = "idle";
  document.querySelector("#result-state").textContent = "Sin analizar";
  document.querySelector("#score-value").textContent = "—";
  document.querySelector("#score-ring").setAttribute("stroke-dashoffset", "100");
  document.querySelector("#score-title").textContent = "Tu análisis empieza aquí";
  document.querySelector("#score-description").textContent = "Introduce una contraseña para ver lo que nuestras reglas detectan.";
  meter.setAttribute("aria-valuenow", "0");
  meter.setAttribute("aria-valuetext", "Sin análisis");
  for (const id of ["length-value", "length-detail", "diversity-value", "diversity-detail", "patterns-value"]) {
    document.getElementById(id).textContent = "";
  }
}

function reset() {
  requestNumber += 1;
  controller?.abort();
  controller = null;
  form.reset();
  input.value = "";
  conceal();
  setBusy(false);
  clearError();
  resetResults();
  status.textContent = "Listo para analizar. Los resultados aparecerán en esta página.";
}

function showError(message, invalid = false) {
  error.textContent = message;
  error.hidden = false;
  if (invalid) input.setAttribute("aria-invalid", "true");
  status.textContent = "No se completó el análisis.";
  input.focus();
}

function render(data) {
  const analysis = data.analysis;
  const levels = { baja: "Baja", media: "Media", alta: "Alta" };
  const categories = { has_lowercase: "minúsculas", has_uppercase: "mayúsculas", has_digit: "dígitos", has_symbol: "símbolos" };
  if (!analysis || !Object.hasOwn(levels, analysis.level) ||
      !Number.isInteger(analysis.score) || analysis.score < 0 || analysis.score > 100 ||
      !Number.isInteger(analysis.length) || !Number.isInteger(analysis.minimum_length) ||
      !analysis.diversity || !Object.keys(categories).every(key => typeof analysis.diversity[key] === "boolean") ||
      ![analysis.meets_minimum, analysis.has_repetition, analysis.has_sequence].every(value => typeof value === "boolean") ||
      !Array.isArray(data.recommendations) || !data.recommendations.every(item => typeof item === "string")) {
    throw new Error("Invalid response");
  }
  panel.dataset.level = analysis.level;
  document.querySelector("#result-state").textContent = "Análisis completado";
  document.querySelector("#score-value").textContent = analysis.score;
  document.querySelector("#score-ring").setAttribute("stroke-dashoffset", String(100 - analysis.score));
  document.querySelector("#score-title").textContent = `Evaluación ${analysis.level}`;
  document.querySelector("#score-description").textContent = {
    baja: "Hay aspectos por revisar. Consulta las observaciones y los siguientes pasos.",
    media: "Aún hay margen de mejora según las reglas de esta herramienta.",
    alta: "Buen resultado en estas reglas. No descarta otros patrones o riesgos."
  }[analysis.level];
  meter.setAttribute("aria-valuenow", String(analysis.score));
  meter.setAttribute("aria-valuetext", `${analysis.score} de 100. Evaluación ${analysis.level}.`);
  document.querySelector("#length-value").textContent = analysis.length;
  document.querySelector("#length-detail").textContent = `${analysis.meets_minimum ? "Cumple" : "No cumple"} el mínimo educativo de ${analysis.minimum_length}.`;
  const present = Object.keys(categories).filter(key => analysis.diversity[key]);
  document.querySelector("#diversity-value").textContent = present.length;
  document.querySelector("#diversity-detail").textContent = present.length ? `${present.map(key => categories[key]).join(", ")}. No suma puntos.` : "Ninguno de los cuatro tipos. No suma puntos.";
  document.querySelector("#patterns-value").textContent = Number(analysis.has_repetition) + Number(analysis.has_sequence);

  const findings = [];
  if (!analysis.meets_minimum) findings.push(`Longitud inferior al mínimo configurado de ${analysis.minimum_length} puntos de código.`);
  if (analysis.has_repetition) findings.push("Tres o más caracteres idénticos consecutivos.");
  if (analysis.has_sequence) findings.push("Una secuencia alfabética o numérica de tres o más caracteres.");
  const list = document.querySelector("#findings");
  list.replaceChildren();
  for (const finding of findings.length ? findings : ["Sin problemas detectados por estas reglas. Esto no garantiza que la contraseña sea segura."]) {
    const item = document.createElement("li");
    item.textContent = finding;
    if (!findings.length) item.className = "neutral";
    list.append(item);
  }
  const recommendations = document.querySelector("#recommendations");
  recommendations.replaceChildren();
  for (const recommendation of data.recommendations) {
    const item = document.createElement("li");
    item.textContent = recommendation;
    recommendations.append(item);
  }
  results.hidden = false;
  status.textContent = `Análisis completado: ${analysis.score} de 100, evaluación ${levels[analysis.level].toLowerCase()}. La entrada se ha borrado del campo.`;
  document.querySelector("#score-title").focus({ preventScroll: true });
}

toggle.addEventListener("click", () => {
  const visible = input.type === "password";
  input.type = visible ? "text" : "password";
  toggle.textContent = visible ? "Ocultar" : "Mostrar";
  toggle.setAttribute("aria-pressed", String(visible));
});

clear.addEventListener("click", () => { reset(); input.focus(); });
input.addEventListener("input", () => {
  clearError();
  resetResults();
  status.textContent = "Entrada nueva. Pulsa Analizar contraseña para evaluarla.";
});

form.addEventListener("submit", async event => {
  event.preventDefault();
  if (controller) return;
  clearError();
  resetResults();
  if (!input.value.length) { showError("Introduce una contraseña para analizarla.", true); return; }
  if ([...input.value].length > 1024) {
    input.value = "";
    conceal();
    showError("La entrada supera los 1024 puntos de código. Se ha borrado del campo.", true);
    return;
  }
  const currentRequest = ++requestNumber;
  const activeController = new AbortController();
  controller = activeController;
  const timeout = setTimeout(() => activeController.abort(), 10000);
  setBusy(true);
  panel.dataset.level = "loading";
  document.querySelector("#result-state").textContent = "Analizando…";
  status.textContent = "Analizando en el servidor de esta aplicación…";
  try {
    // La entrada no se conserva en variables, historial ni resultados.
    const pending = fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: input.value }),
      cache: "no-store",
      credentials: "omit",
      redirect: "error",
      signal: activeController.signal
    });
    input.value = "";
    conceal();
    const response = await pending;
    if (currentRequest !== requestNumber) return;
    if (!response.ok) {
      const messages = {
        400: "La solicitud no es válida. Vuelve a introducir la contraseña.",
        403: "Abre la aplicación desde su dirección local e inténtalo de nuevo.",
        413: "La solicitud es demasiado grande. Prueba con una entrada más corta.",
        415: "No se pudo enviar la solicitud. Recarga la página.",
        422: "La entrada no es válida. Introduce entre 1 y 1024 puntos de código."
      };
      resetResults();
      setBusy(false);
      showError(messages[response.status] || "El servidor no pudo completar el análisis. Vuelve a intentarlo.");
      return;
    }
    const data = await response.json();
    if (currentRequest !== requestNumber) return;
    render(data);
  } catch {
    if (currentRequest !== requestNumber) return;
    resetResults();
    setBusy(false);
    showError("No se pudo completar el análisis. Comprueba que el servidor local sigue activo e inténtalo de nuevo.");
  } finally {
    clearTimeout(timeout);
    if (currentRequest === requestNumber) {
      controller = null;
      input.value = "";
      conceal();
      setBusy(false);
    }
  }
});

window.addEventListener("pagehide", reset);
window.addEventListener("pageshow", reset);
clear.disabled = false;
reset();
