chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "addToRAG",
    title: "📚 Add in RAG",
    contexts: ["selection"]
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== "addToRAG" || !info.selectionText) return;

  const { apiKey, apiUrl } = await chrome.storage.local.get({
    apiKey: "",
    apiUrl: "http://localhost:8004"
  });

  if (!apiKey) {
    chrome.tabs.sendMessage(tab.id, {
      type: "rag_error",
      message: "Enter your API key in the settings."
    });
    return;
  }

  try {
    const resp = await fetch(`${apiUrl}/ingest/text`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": apiKey,
      },
      body: JSON.stringify({
        text: info.selectionText,
        source: tab.url || "webpage"
      })
    });

    const data = await resp.json();
    chrome.tabs.sendMessage(tab.id, { type: "rag_success", chunks: data.chunks });
  } catch (error) {
    chrome.tabs.sendMessage(tab.id, { type: "rag_error", message: error.message });
  }
});