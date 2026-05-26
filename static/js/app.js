const state = {
  messages: [],
  selectedHFModel: "",
  settings: {},
};

const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.ok === false) {
    throw new Error(data.error || `Request failed: ${response.status}`);
  }
  return data;
}

function setOutput(id, text) {
  const el = $(id);
  if (el) el.textContent = typeof text === "string" ? text : JSON.stringify(text, null, 2);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function tags(values = [], limit = 5) {
  return values.slice(0, limit).map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join("");
}

function switchView(view) {
  document.querySelectorAll(".nav-item").forEach((btn) => btn.classList.toggle("active", btn.dataset.view === view));
  document.querySelectorAll(".view").forEach((section) => section.classList.toggle("active", section.id === `view-${view}`));
  const titles = {
    chat: ["Chat", "Conversational coding, reasoning, browsing, tools, and multimodal workflows."],
    models: ["Hugging Face", "Browse, select, and use Hugging Face models and LLMs in app."],
    tools: ["Tools", "Search the web, run code, and generate media."],
    plugins: ["Add-ons", "Search and install VS Code-compatible add-ons into OpenClaw."],
    files: ["Workspace", "Inspect generated files and scripts."],
    settings: ["Settings", "Configure local provider tokens and runtime endpoints."],
  };
  $("viewTitle").textContent = titles[view][0];
  $("viewSubtitle").textContent = titles[view][1];
}

function addMessage(role, content, meta = "") {
  state.messages.push({ role, content });
  const node = document.createElement("article");
  node.className = `message ${role === "user" ? "user" : "assistant"}`;
  node.innerHTML = `${escapeHtml(content)}${meta ? `<small>${escapeHtml(meta)}</small>` : ""}`;
  $("conversation").appendChild(node);
  $("conversation").scrollTop = $("conversation").scrollHeight;
}

async function loadHealth() {
  try {
    const health = await api("/api/health");
    $("healthLabel").textContent = "Ready";
    $("healthMeta").textContent = `${health.build} · ${health.plugin_count} add-ons`;
  } catch (error) {
    $("healthLabel").textContent = "Offline";
    $("healthMeta").textContent = error.message;
  }
}

async function loadSettings() {
  const data = await api("/api/settings");
  state.settings = data.settings;
  $("providerSelect").value = state.settings.provider || "local";
  $("modelInput").value = state.settings.model || "openclaw-local";
  if ($("modelSelect")) {
    $("modelSelect").innerHTML = `<option value="${escapeHtml(state.settings.model || "")}">${escapeHtml(state.settings.model || "Load models")}</option>`;
  }
  ["huggingface_api_key", "openai_api_key", "custom_endpoint", "custom_api_key", "ollama_endpoint"].forEach((id) => {
    if ($(id)) $(id).value = state.settings[id] === "set" ? "" : (state.settings[id] || "");
  });
  if (state.settings.model && state.settings.provider === "huggingface") {
    selectHFModel(state.settings.model, false);
  }
}

async function saveSettings(extra = {}) {
  const payload = {
    provider: $("providerSelect").value,
    model: $("modelInput").value.trim(),
    custom_endpoint: $("custom_endpoint")?.value.trim() || state.settings.custom_endpoint || "",
    custom_api_key: $("custom_api_key")?.value.trim() || "set",
    ollama_endpoint: $("ollama_endpoint")?.value.trim() || state.settings.ollama_endpoint || "",
    huggingface_provider_policy: $("hfPolicy")?.value || "fastest",
    ...extra,
  };
  ["huggingface_api_key", "openai_api_key"].forEach((id) => {
    const value = $(id)?.value.trim();
    if (value) payload[id] = value;
  });
  const data = await api("/api/settings", { method: "POST", body: JSON.stringify(payload) });
  state.settings = data.settings;
  $("providerSelect").value = state.settings.provider || "local";
  $("modelInput").value = state.settings.model || "";
  return data;
}

async function loadProviderModels() {
  const provider = $("providerSelect").value;
  const status = $("modelLoadStatus");
  const modelSelect = $("modelSelect");
  if (status) status.textContent = `Loading ${provider} models...`;
  if (modelSelect) modelSelect.innerHTML = `<option value="">Loading...</option>`;
  try {
    const params = new URLSearchParams({ provider });
    if (provider === "ollama") {
      params.set("endpoint", $("ollama_endpoint")?.value.trim() || state.settings.ollama_endpoint || "http://localhost:11434");
    }
    const data = await api(`/api/models?${params.toString()}`);
    const models = data.models || [];
    if (modelSelect) {
      modelSelect.innerHTML = models.length
        ? `<option value="">Select model</option>` + models.map((model) => `<option value="${escapeHtml(model.id)}">${escapeHtml(model.name || model.id)}</option>`).join("")
        : `<option value="">No models found</option>`;
    }
    if (status) {
      status.textContent = data.message || `${models.length} ${provider} model${models.length === 1 ? "" : "s"} loaded.`;
    }
  } catch (error) {
    if (modelSelect) modelSelect.innerHTML = `<option value="">Load failed</option>`;
    if (status) status.textContent = error.message;
  }
}

async function selectProviderModel(modelId) {
  const provider = $("providerSelect").value;
  if (!modelId) return;
  $("modelInput").value = modelId;
  if (provider === "huggingface") {
    state.selectedHFModel = modelId;
    $("selectedModelCard").innerHTML = `<strong>${escapeHtml(modelId)}</strong><p>Selected for Hugging Face chat and tests.</p>`;
  }
  const data = await api("/api/models/select", {
    method: "POST",
    body: JSON.stringify({ provider, model: modelId }),
  });
  state.settings = data.settings;
  if ($("modelLoadStatus")) $("modelLoadStatus").textContent = `Selected ${provider} model: ${modelId}`;
}

async function sendChat(event) {
  event.preventDefault();
  const prompt = $("promptInput").value.trim();
  if (!prompt) return;
  $("promptInput").value = "";
  addMessage("user", prompt);
  addMessage("assistant", "Thinking...");
  const pending = $("conversation").lastElementChild;
  try {
    const data = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({
        prompt,
        messages: state.messages.slice(-12),
        provider: $("providerSelect").value,
        model: $("modelInput").value.trim(),
      }),
    });
    pending.innerHTML = `${escapeHtml(data.reply)}<small>${escapeHtml(data.provider)} · ${escapeHtml(data.model)}</small>`;
    state.messages.push({ role: "assistant", content: data.reply });
  } catch (error) {
    pending.textContent = `Error: ${error.message}`;
  }
}

function selectHFModel(modelId, persist = true) {
  state.selectedHFModel = modelId;
  $("selectedModelCard").innerHTML = `<strong>${escapeHtml(modelId)}</strong><p>Selected for Hugging Face chat and tests.</p>`;
  $("providerSelect").value = "huggingface";
  $("modelInput").value = modelId;
  if (persist) {
    api("/api/huggingface/select", {
      method: "POST",
      body: JSON.stringify({ model: modelId, provider_policy: $("hfPolicy").value }),
    }).then(loadSettings).catch((error) => setOutput("hfTestOutput", error.message));
  }
}

function renderHFModels(models, router = false) {
  const list = $("hfResults");
  if (!models.length) {
    list.innerHTML = `<div class="result-item">No models found.</div>`;
    return;
  }
  list.innerHTML = models.map((model) => {
    const id = model.id || model.modelId || "";
    const providerTags = router && model.providers
      ? model.providers.slice(0, 5).map((p) => `${p.provider}:${p.status}`)
      : (model.pipeline_tag ? [model.pipeline_tag] : []).concat(model.license ? [`license:${model.license}`] : []).concat(model.tags || []);
    const meta = router && model.providers
      ? `${model.providers.length} providers · ${model.architecture?.input_modalities?.join(",") || "text"}`
      : `${model.downloads || 0} downloads · ${model.likes || 0} likes${model.free_note ? " · free/open catalog" : ""}`;
    return `<article class="result-item">
      <div class="result-title">
        <strong>${escapeHtml(id)}</strong>
        <button class="secondary" data-select-hf="${escapeHtml(id)}">Use</button>
      </div>
      <p>${escapeHtml(meta)}</p>
      <div class="tags">${tags(providerTags, 8)}</div>
      <a href="https://huggingface.co/${escapeHtml(id)}" target="_blank" rel="noreferrer">Open model page</a>
    </article>`;
  }).join("");
}

async function searchHFModels() {
  $("hfResults").innerHTML = `<div class="result-item">Searching Hugging Face...</div>`;
  try {
    const data = await api("/api/huggingface/search", {
      method: "POST",
      body: JSON.stringify({
        query: $("hfQuery").value.trim(),
        pipeline: $("hfPipeline").value,
        inference_provider: $("hfProvider").value,
        limit: 30,
      }),
    });
    renderHFModels(data.models || []);
  } catch (error) {
    $("hfResults").innerHTML = `<div class="result-item">Error: ${escapeHtml(error.message)}</div>`;
  }
}

async function loadRouterModels() {
  $("hfResults").innerHTML = `<div class="result-item">Loading Hugging Face router chat models...</div>`;
  try {
    const data = await api("/api/huggingface/router-models");
    renderHFModels(data.models || [], true);
  } catch (error) {
    $("hfResults").innerHTML = `<div class="result-item">Error: ${escapeHtml(error.message)}</div>`;
  }
}

async function loadFreeModels() {
  $("hfResults").innerHTML = `<div class="result-item">Loading public free/open models...</div>`;
  try {
    const data = await api("/api/huggingface/free-models", {
      method: "POST",
      body: JSON.stringify({
        query: $("hfQuery").value.trim(),
        pipeline: $("hfPipeline").value,
        limit: 80,
      }),
    });
    renderHFModels(data.models || []);
    if (data.message) {
      $("hfResults").insertAdjacentHTML("afterbegin", `<div class="result-item"><strong>Free/open filter</strong><p>${escapeHtml(data.message)}</p></div>`);
    }
  } catch (error) {
    $("hfResults").innerHTML = `<div class="result-item">Error: ${escapeHtml(error.message)}</div>`;
  }
}

async function testHFModel() {
  const model = state.selectedHFModel || $("modelInput").value.trim();
  if (!model) {
    setOutput("hfTestOutput", "Select a Hugging Face model first.");
    return;
  }
  setOutput("hfTestOutput", "Testing Hugging Face model...");
  try {
    await api("/api/huggingface/select", {
      method: "POST",
      body: JSON.stringify({ model, provider_policy: $("hfPolicy").value }),
    });
    const data = await api("/api/huggingface/test", {
      method: "POST",
      body: JSON.stringify({ model, prompt: $("hfTestPrompt").value.trim() }),
    });
    setOutput("hfTestOutput", `${data.model}\n\n${data.reply}`);
  } catch (error) {
    setOutput("hfTestOutput", error.message);
  }
}

async function doWebSearch() {
  $("searchResults").innerHTML = `<div class="result-item">Searching...</div>`;
  try {
    const data = await api("/api/search", { method: "POST", body: JSON.stringify({ query: $("searchQuery").value }) });
    $("searchResults").innerHTML = (data.results || []).map((item) => `<article class="result-item">
      <a href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer"><strong>${escapeHtml(item.title)}</strong></a>
      <p>${escapeHtml(item.snippet || "")}</p>
    </article>`).join("");
  } catch (error) {
    $("searchResults").innerHTML = `<div class="result-item">Error: ${escapeHtml(error.message)}</div>`;
  }
}

async function runCode() {
  setOutput("codeOutput", "Running...");
  try {
    const data = await api("/api/code/run", {
      method: "POST",
      body: JSON.stringify({ language: $("codeLanguage").value, code: $("codeInput").value }),
    });
    setOutput("codeOutput", `Exit ${data.returncode}\n\nSTDOUT\n${data.stdout}\n\nSTDERR\n${data.stderr}\n\nFile\n${data.file}`);
  } catch (error) {
    setOutput("codeOutput", error.message);
  }
}

async function createImage() {
  $("imageResult").textContent = "Generating image...";
  try {
    const data = await api("/api/image", { method: "POST", body: JSON.stringify({ prompt: $("imagePrompt").value }) });
    $("imageResult").innerHTML = `<img src="${escapeHtml(data.url)}" alt="Generated image">`;
  } catch (error) {
    $("imageResult").textContent = error.message;
  }
}

function renderPluginSearch(extensions = []) {
  $("pluginResults").innerHTML = extensions.map((entry) => {
    const ext = entry.namespace ? entry : entry.extension || {};
    const namespace = ext.namespace || entry.namespace || "";
    const name = ext.name || entry.name || "";
    const display = ext.displayName || `${namespace}.${name}`;
    const downloadUrl = ext.files?.download || entry.files?.download || "";
    const version = ext.version || entry.version || "";
    return `<article class="result-item">
      <div class="result-title">
        <strong>${escapeHtml(display)}</strong>
        <button class="secondary" data-install-plugin="${escapeHtml(namespace)}|${escapeHtml(name)}" data-version="${escapeHtml(version)}" data-download-url="${escapeHtml(downloadUrl)}" data-display-name="${escapeHtml(display)}">Install</button>
      </div>
      <p>${escapeHtml(ext.description || entry.description || "")}</p>
      <div class="tags">${tags([namespace, name, version].filter(Boolean), 4)}</div>
      <div class="install-status" aria-live="polite"></div>
    </article>`;
  }).join("") || `<div class="result-item">No add-ons found.</div>`;
}

async function searchPlugins() {
  $("pluginResults").innerHTML = `<div class="result-item">Searching OpenVSX...</div>`;
  try {
    const data = await api("/api/plugins/vscode/search", {
      method: "POST",
      body: JSON.stringify({ query: $("pluginQuery").value.trim(), size: 20 }),
    });
    renderPluginSearch(data.catalog?.extensions || data.catalog?.results || []);
  } catch (error) {
    $("pluginResults").innerHTML = `<div class="result-item">Error: ${escapeHtml(error.message)}</div>`;
  }
}

async function installPlugin(namespace, extension, button) {
  const card = button?.closest(".result-item");
  const status = card?.querySelector(".install-status");
  if (card) {
    card.classList.remove("installed", "failed");
    card.classList.add("installing");
  }
  if (button) {
    button.disabled = true;
    button.textContent = "Installing...";
  }
  if (status) status.textContent = `Downloading ${namespace}.${extension}...`;
  $("installedPlugins").innerHTML = `<div class="result-item">Installing ${escapeHtml(namespace)}.${escapeHtml(extension)}...</div>`;
  try {
    const data = await api("/api/plugins/vscode/install", {
      method: "POST",
      body: JSON.stringify({
        namespace,
        extension,
        version: button?.dataset.version || "",
        download_url: button?.dataset.downloadUrl || "",
        display_name: button?.dataset.displayName || "",
      }),
    });
    if (card) {
      card.classList.remove("installing");
      card.classList.add("installed");
    }
    if (status) status.textContent = `Installed ${data.installed?.display_name || `${namespace}.${extension}`}.`;
    if (button) button.textContent = "Installed";
    await loadInstalledPlugins();
  } catch (error) {
    if (card) {
      card.classList.remove("installing");
      card.classList.add("failed");
    }
    if (button) {
      button.disabled = false;
      button.textContent = "Retry";
    }
    if (status) status.textContent = error.message;
    $("installedPlugins").innerHTML = `<div class="result-item">Error: ${escapeHtml(error.message)}</div>`;
  }
}

async function loadInstalledPlugins() {
  const [data, host] = await Promise.all([
    api("/api/plugins/vscode/installed"),
    api("/api/plugins/vscode/host/status"),
  ]);
  const hostBox = $("vscodeHostStatus");
  if (hostBox) {
    if (host.host?.available) {
      hostBox.className = "host-status ready";
      hostBox.textContent = `VS Code host ready: ${host.host.version?.[0] || host.host.cli}`;
    } else {
      hostBox.className = "host-status missing";
      hostBox.textContent = "VS Code host CLI not found. Add-ons still install into OpenClaw store.";
    }
  }
  $("installedPlugins").innerHTML = (data.installed || []).map((plugin) => `<article class="result-item">
    <strong>${escapeHtml(plugin.display_name || `${plugin.namespace}.${plugin.extension}`)}</strong>
    <p>${escapeHtml(plugin.runtime_note || "")}</p>
    <div class="tags">${tags([plugin.version, plugin.package?.publisher, plugin.package?.engines?.vscode, plugin.vscode_host?.installed ? "VS Code host" : ""].filter(Boolean), 4)}</div>
  </article>`).join("") || `<div class="result-item">No installed add-ons yet.</div>`;
  await loadHealth();
}

async function loadFiles() {
  $("fileList").innerHTML = `<div class="result-item">Loading files...</div>`;
  try {
    const data = await api("/api/files");
    $("fileList").innerHTML = `<div class="result-item"><strong>${escapeHtml(data.workspace)}</strong></div>` +
      (data.files || []).map((file) => `<article class="result-item">
        <strong>${escapeHtml(file.path)}</strong>
        <p>${file.size} bytes</p>
      </article>`).join("");
  } catch (error) {
    $("fileList").innerHTML = `<div class="result-item">Error: ${escapeHtml(error.message)}</div>`;
  }
}

function startVoiceInput() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    addMessage("assistant", "Voice input is not available in this browser.");
    return;
  }
  const recognition = new SpeechRecognition();
  recognition.lang = "en-US";
  recognition.interimResults = false;
  recognition.onresult = (event) => {
    $("promptInput").value = event.results[0][0].transcript;
  };
  recognition.onerror = (event) => addMessage("assistant", `Voice input error: ${event.error}`);
  recognition.start();
}

function bindEvents() {
  document.querySelectorAll(".nav-item").forEach((btn) => btn.addEventListener("click", () => switchView(btn.dataset.view)));
  $("chatForm").addEventListener("submit", sendChat);
  $("saveProviderBtn").addEventListener("click", () => saveSettings().then(loadSettings));
  $("loadModelsBtn").addEventListener("click", loadProviderModels);
  $("modelSelect").addEventListener("change", (event) => selectProviderModel(event.target.value).catch((error) => {
    if ($("modelLoadStatus")) $("modelLoadStatus").textContent = error.message;
  }));
  $("providerSelect").addEventListener("change", () => {
    if ($("modelLoadStatus")) $("modelLoadStatus").textContent = "";
  });
  $("saveSettingsBtn").addEventListener("click", () => saveSettings().then(loadSettings));
  $("hfSearchBtn").addEventListener("click", searchHFModels);
  $("loadFreeModelsBtn").addEventListener("click", loadFreeModels);
  $("loadRouterModelsBtn").addEventListener("click", loadRouterModels);
  $("hfTestBtn").addEventListener("click", testHFModel);
  $("searchBtn").addEventListener("click", doWebSearch);
  $("runCodeBtn").addEventListener("click", runCode);
  $("imageBtn").addEventListener("click", createImage);
  $("pluginSearchBtn").addEventListener("click", searchPlugins);
  $("refreshInstalledPluginsBtn").addEventListener("click", loadInstalledPlugins);
  $("refreshFilesBtn").addEventListener("click", loadFiles);
  $("voiceBtn").addEventListener("click", startVoiceInput);
  document.addEventListener("click", (event) => {
    const hfButton = event.target.closest("[data-select-hf]");
    if (hfButton) selectHFModel(hfButton.dataset.selectHf);
    const pluginButton = event.target.closest("[data-install-plugin]");
    if (pluginButton) {
      const [namespace, extension] = pluginButton.dataset.installPlugin.split("|");
      installPlugin(namespace, extension, pluginButton);
    }
  });
}

document.addEventListener("DOMContentLoaded", async () => {
  bindEvents();
  await Promise.allSettled([loadHealth(), loadSettings(), loadInstalledPlugins(), loadFiles()]);
  addMessage("assistant", "OpenClaw is ready. Pick a Hugging Face model in the Hugging Face tab, save your token in Settings, then use it directly in Chat.");
  if (window.lucide) window.lucide.createIcons();
  setTimeout(() => $("splash")?.classList.add("hidden"), 650);
});
