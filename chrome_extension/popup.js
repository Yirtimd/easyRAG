const SERVER_URL = "https://yirtimd-easyrag-8bbc.twc1.net";; // Change to Railway URL after deploy

// --- Storage ---
async function getSettings() {
  return new Promise(resolve => {
    chrome.storage.local.get({ apiKey: "" }, data => {
      resolve({ apiKey: data.apiKey, apiUrl: SERVER_URL });
    });
  });
}

// --- Tabs ---
document.querySelectorAll(".tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById(`tab-${tab.dataset.tab}`).classList.add("active");
  });
});

// --- Key tab ---
const apiKeyInput = document.getElementById("apiKey");
const saveBtn = document.getElementById("saveSettings");
const settingsStatus = document.getElementById("settingsStatus");
const toggleKeyBtn = document.getElementById("toggleKeyBtn");
const registerBtn = document.getElementById("registerBtn");
const registerStatus = document.getElementById("registerStatus");

getSettings().then(s => { apiKeyInput.value = s.apiKey; });

saveBtn.addEventListener("click", () => {
  chrome.storage.local.set({ apiKey: apiKeyInput.value.trim() });
  showStatus(settingsStatus, "Key saved", "success");
});

toggleKeyBtn.addEventListener("click", () => {
  apiKeyInput.type = apiKeyInput.type === "password" ? "text" : "password";
});

registerBtn.addEventListener("click", async () => {
  const { apiUrl } = await getSettings();
  registerBtn.disabled = true;
  showStatus(registerStatus, "Generating key...", "loading");
  try {
    const resp = await fetch(`${apiUrl}/auth/register`, { method: "POST" });
    const data = await resp.json();
    apiKeyInput.value = data.api_key;
    chrome.storage.local.set({ apiKey: data.api_key });
    showStatus(registerStatus, "Key generated and saved", "success");
  } catch (e) {
    showStatus(registerStatus, "Failed to generate key", "error");
  } finally {
    registerBtn.disabled = false;
  }
});

// --- PDF Upload ---
const pdfInput = document.getElementById("pdfInput");
const pdfBtn = document.getElementById("pdfBtn");
const pdfStatus = document.getElementById("pdfStatus");
const fileNameEl = document.getElementById("fileName");
const fileMetaEl = document.getElementById("fileMeta");

pdfInput.addEventListener("change", () => {
  const file = pdfInput.files[0];
  if (file) {
    fileNameEl.textContent = file.name;
    fileMetaEl.textContent = `${(file.size / 1024 / 1024).toFixed(1)} MB · PDF document`;
  } else {
    fileNameEl.textContent = "Choose a PDF file";
    fileMetaEl.textContent = "Click to browse";
  }
});

pdfBtn.addEventListener("click", async () => {
  const file = pdfInput.files[0];
  if (!file) { showStatus(pdfStatus, "Choose a PDF file first", "warning"); return; }

  const { apiKey, apiUrl } = await getSettings();
  if (!apiKey) { showStatus(pdfStatus, "Set your API key in the Key tab", "warning"); return; }

  pdfBtn.disabled = true;
  showStatus(pdfStatus, "Indexing PDF...", "loading");

  try {
    const formData = new FormData();
    formData.append("file", file);
    const resp = await fetch(`${apiUrl}/ingest`, {
      method: "POST",
      headers: { "x-api-key": apiKey },
      body: formData,
    });
    const data = await resp.json();
    showStatus(pdfStatus, `Indexed — ${data.chunks} chunks from ${data.filename}`, "success");
    pdfInput.value = "";
    fileNameEl.textContent = "Choose a PDF file";
    fileMetaEl.textContent = "Click to browse";
  } catch (e) {
    showStatus(pdfStatus, "Could not process this PDF", "error");
  } finally {
    pdfBtn.disabled = false;
  }
});

// --- Text Ingest ---
const textInput = document.getElementById("textInput");
const sourceInput = document.getElementById("sourceInput");
const textBtn = document.getElementById("textBtn");
const textStatus = document.getElementById("textStatus");
const clearTextBtn = document.getElementById("clearTextBtn");

clearTextBtn.addEventListener("click", () => {
  textInput.value = "";
  sourceInput.value = "";
  hideStatus(textStatus);
});

textBtn.addEventListener("click", async () => {
  const text = textInput.value.trim();
  if (!text) { showStatus(textStatus, "Paste some text first", "warning"); return; }

  const { apiKey, apiUrl } = await getSettings();
  if (!apiKey) { showStatus(textStatus, "Set your API key in the Key tab", "warning"); return; }

  textBtn.disabled = true;
  showStatus(textStatus, "Saving...", "loading");

  try {
    const resp = await fetch(`${apiUrl}/ingest/text`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-api-key": apiKey },
      body: JSON.stringify({ text, source: sourceInput.value.trim() || "clipboard" }),
    });
    const data = await resp.json();
    showStatus(textStatus, `Saved — ${data.chunks} chunks as "${data.source}"`, "success");
    textInput.value = "";
    sourceInput.value = "";
  } catch (e) {
    showStatus(textStatus, "Failed to save text", "error");
  } finally {
    textBtn.disabled = false;
  }
});

// --- Export ---
const exportBtn = document.getElementById("exportBtn");

exportBtn.addEventListener("click", async () => {
  const { apiKey, apiUrl } = await getSettings();
  if (!apiKey) return;
  exportBtn.disabled = true;
  try {
    const resp = await fetch(`${apiUrl}/export`, { headers: { "x-api-key": apiKey } });
    const data = await resp.json();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "rag_export.json"; a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    console.error("Export failed", e);
  } finally {
    exportBtn.disabled = false;
  }
});

// --- Chat ---
const chatMessages = document.getElementById("chatMessages");
const chatInput = document.getElementById("chatInput");
const chatBtn = document.getElementById("chatBtn");
const chatStatus = document.getElementById("chatStatus");
let sessionId = "";
let messageHistory = [];

// Restore chat on popup open
chrome.storage.local.get({ sessionId: "", messageHistory: [] }, data => {
  sessionId = data.sessionId;
  messageHistory = data.messageHistory;
  messageHistory.forEach(m => appendMessage(m.role, m.text));
});

chatBtn.addEventListener("click", sendChat);
chatInput.addEventListener("keydown", e => { if (e.key === "Enter") sendChat(); });

async function sendChat() {
  const question = chatInput.value.trim();
  if (!question) return;

  const { apiKey, apiUrl } = await getSettings();
  if (!apiKey) { showStatus(chatStatus, "Set your API key in the Key tab", "warning"); return; }

  appendMessage("user", question);
  chatInput.value = "";
  chatBtn.disabled = true;
  hideStatus(chatStatus);

  const assistantEl = appendMessage("assistant", "");
  let streamedText = "";

  try {
    const resp = await fetch(`${apiUrl}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-api-key": apiKey },
      body: JSON.stringify({ question, session_id: sessionId }),
    });

    if (resp.headers.get("x-session-id")) {
      sessionId = resp.headers.get("x-session-id");
      chrome.storage.local.set({ sessionId });
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      streamedText += decoder.decode(value, { stream: true });
      assistantEl.textContent = streamedText;
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }
  } catch (e) {
    streamedText = `Error: ${e.message}`;
    assistantEl.textContent = streamedText;
  } finally {
    chatBtn.disabled = false;
  }

  if (streamedText) {
    messageHistory.push({ role: "assistant", text: streamedText });
    chrome.storage.local.set({ messageHistory });
  }
}

function appendMessage(role, text) {
  const wrap = document.createElement("div");
  wrap.className = role === "user" ? "msg-user-wrap" : "msg-rag-wrap";

  const inner = document.createElement("div");

  const label = document.createElement("div");
  label.className = `msg-label${role === "user" ? " msg-user-label" : ""}`;
  label.textContent = role === "user" ? "You" : "RAG";

  const bubble = document.createElement("div");
  bubble.className = role === "user" ? "bubble-user" : "bubble-rag";
  bubble.textContent = text;

  inner.appendChild(label);
  inner.appendChild(bubble);
  wrap.appendChild(inner);
  chatMessages.appendChild(wrap);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  if (text) {
    messageHistory.push({ role, text });
    chrome.storage.local.set({ messageHistory });
  }

  return bubble;
}

// --- Helpers ---
function showStatus(el, msg, type = "success") {
  el.textContent = msg;
  el.className = `status-row visible ${type}`;
}

function hideStatus(el) {
  el.className = "status-row";
  el.textContent = "";
}

// --- Clear chat ---
document.getElementById("clearChatBtn").addEventListener("click", () => {
  chatMessages.innerHTML = "";
  messageHistory = [];
  sessionId = "";
  chrome.storage.local.set({ messageHistory: [], sessionId: "" });
});