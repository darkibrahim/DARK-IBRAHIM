/* ----------------------------------------------------------------------
 * DARK-IBRAHIM - Local AI Software & APK Builder
 * Developer : DARK IBRAHIM
 * Title     : Bug Bounty Hunter & Cyber Security Expert
 * Facebook  : https://www.facebook.com/profile.php?id=61580661413217
 * GitHub    : https://github.com/darkibrahim
 * Telegram  : @Hunter_1B4H14
 * ---------------------------------------------------------------------- */
"use strict";

const $ = (id) => document.getElementById(id);
const POLL_MS = 1000;
let currentProject = null;

function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === "text") node.textContent = value;
    else if (key === "class") node.className = value;
    else node.setAttribute(key, value);
  }
  children.forEach((c) => node.append(c));
  return node;
}

async function api(path, options = {}) {
  const init = { ...options };
  if (init.body && typeof init.body !== "string") {
    init.body = JSON.stringify(init.body);
    init.headers = { "Content-Type": "application/json" };
  }
  const res = await fetch(path, init);
  let data = {};
  try { data = await res.json(); } catch (_) { /* empty body */ }
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

function setChip(id, text, state) {
  const chip = $(id);
  chip.textContent = text;
  chip.className = "chip " + (state || "");
}

async function loadStatus() {
  try {
    const health = await api("/api/health");
    const ai = health.ollama;
    $("version").textContent = health.version;
    setChip("chip-ollama", ai.ollama_available ? "Ollama: online" : "Ollama: offline (templates only)",
      ai.ollama_available ? "ok" : "warn");
    setChip("chip-model", "Model: " + (ai.resolved || "none installed"), ai.resolved ? "ok" : "warn");
    const select = $("model");
    select.replaceChildren(el("option", { value: "", text: "Default" }));
    ai.installed.forEach((name) => select.append(el("option", { value: name, text: name })));
  } catch (err) {
    setChip("chip-ollama", "Server error: " + err.message, "bad");
  }
  try {
    const env = await api("/api/apk/environment");
    setChip("chip-android", env.ready ? "Android build tools: ready" : "Android build tools: not found (project ZIP only)",
      env.ready ? "ok" : "warn");
  } catch (_) {
    setChip("chip-android", "Android build tools: unknown", "warn");
  }
}

function appendLog(lines) {
  const box = $("log");
  box.textContent = lines.length ? lines.join("\n") : "Working…";
  box.scrollTop = box.scrollHeight;
}

async function waitForJob(jobId) {
  for (;;) {
    const job = await api("/api/jobs/" + jobId);
    appendLog(job.logs);
    if (job.status === "done") return job.result;
    if (job.status === "error") throw new Error(job.error || "Build failed");
    await new Promise((r) => setTimeout(r, POLL_MS));
  }
}

function renderResult(result) {
  currentProject = result;
  const report = result.report;
  $("result").hidden = false;
  $("result-title").textContent = report.plan.title + " — " + report.plan.project_type;
  $("result-meta").textContent =
    `${result.files_count} files · engine: ${report.mode}${report.model ? " (" + report.model + ")" : ""} · ${result.zip_name}`;
  $("download").href = result.download_url;
  $("apk-btn").hidden = !(report.files.some((f) => f === "index.html" || f === "www/index.html"));
  $("apk-result").hidden = true;

  const list = $("checks");
  list.replaceChildren();
  report.tests.checks.forEach((c) => list.append(el("li", { class: c.status, text: `${c.name}: ${c.detail}` })));
  report.fixes.forEach((f) => list.append(el("li", { class: "pass", text: "Fixed: " + f })));
  report.warnings.forEach((w) => list.append(el("li", { class: "warn", text: w })));
  list.append(el("li", { class: "skip", text: report.tests.note }));
  loadFiles(result.id);
}

async function loadFiles(projectId) {
  const { files } = await api(`/api/projects/${projectId}/files`);
  const list = $("files");
  list.replaceChildren();
  files.forEach((f) => {
    const button = el("button", { type: "button", text: f.path });
    button.addEventListener("click", async () => {
      list.querySelectorAll("button").forEach((b) => b.removeAttribute("aria-current"));
      button.setAttribute("aria-current", "true");
      try {
        const data = await api(`/api/projects/${projectId}/file?path=${encodeURIComponent(f.path)}`);
        $("preview").textContent = data.content;
      } catch (err) {
        $("preview").textContent = err.message;
      }
    });
    list.append(el("li", {}, button));
  });
}

$("build-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = $("build-btn");
  button.disabled = true;
  button.textContent = "Building…";
  $("result").hidden = true;
  appendLog(["Starting…"]);
  try {
    const { job_id } = await api("/api/projects/build", {
      method: "POST",
      body: {
        prompt: $("prompt").value, name: $("name").value, project_type: $("type").value,
        mode: $("mode").value, model: $("model").value,
      },
    });
    renderResult(await waitForJob(job_id));
    loadHistory();
  } catch (err) {
    $("log").textContent += "\nError: " + err.message;
  } finally {
    button.disabled = false;
    button.textContent = "Build project";
  }
});

$("apk-btn").addEventListener("click", async () => {
  const button = $("apk-btn");
  const box = $("apk-result");
  button.disabled = true;
  box.hidden = false;
  box.replaceChildren(el("p", { text: "Preparing Android project…" }));
  try {
    const { job_id } = await api("/api/apk/build", { method: "POST", body: { project_id: currentProject.id } });
    const result = await waitForJob(job_id);
    box.replaceChildren(el("p", { text: result.message }));
    const links = el("div", { class: "actions" });
    links.append(el("a", { class: "button", href: result.project_zip_url, text: "Android project ZIP" }));
    if (result.apk_url) links.append(el("a", { class: "button primary", href: result.apk_url, text: "Download APK" }));
    box.append(links);
  } catch (err) {
    box.replaceChildren(el("p", { text: "Error: " + err.message }));
  } finally {
    button.disabled = false;
  }
});

async function loadHistory() {
  const { projects } = await api("/api/projects");
  const list = $("history");
  list.replaceChildren();
  if (!projects.length) {
    list.append(el("li", { class: "muted", text: "No projects yet." }));
    return;
  }
  projects.forEach((p) => {
    const info = el("div", { class: "info" },
      el("strong", { text: p.name }),
      el("span", { text: `${p.status} · ${p.project_type || "?"} · ${p.files_count} files · ${p.created_at.slice(0, 16).replace("T", " ")}` }),
      el("span", { text: p.prompt.slice(0, 120) }));
    const item = el("li", {}, info);
    if (p.status === "done") {
      item.append(el("a", { class: "button", href: `/api/projects/${p.id}/download`, text: "ZIP" }));
      const open = el("button", { type: "button", text: "Open" });
      open.addEventListener("click", async () => {
        const full = await api("/api/projects/" + p.id);
        renderResult({ id: p.id, files_count: full.files_count, zip_name: full.zip_name,
                       download_url: `/api/projects/${p.id}/download`, report: full.report });
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
      item.append(open);
    }
    const del = el("button", { type: "button", text: "Delete" });
    del.addEventListener("click", async () => {
      if (!confirm(`Delete "${p.name}"?`)) return;
      await api("/api/projects/" + p.id, { method: "DELETE" });
      loadHistory();
    });
    item.append(del);
    list.append(item);
  });
}

loadStatus();
loadHistory().catch(() => {});
