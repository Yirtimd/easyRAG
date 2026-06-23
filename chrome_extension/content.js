// Слушаем сообщения от background.js и показываем тост
chrome.runtime.onMessage.addListener((message) => {
  if (message.type === "rag_success") {
    showToast(`✅ Добавлено ${message.chunks} фрагментов в RAG`);
  } else if (message.type === "rag_error") {
    showToast(`❌ Ошибка: ${message.message}`, "error");
  }
});

function showToast(text, type = "success") {
  const toast = document.createElement("div");
  toast.style.cssText = `
    position: fixed;
    bottom: 24px;
    right: 24px;
    background: ${type === "success" ? "#22c55e" : "#ef4444"};
    color: white;
    padding: 12px 20px;
    border-radius: 8px;
    font-family: sans-serif;
    font-size: 14px;
    font-weight: 500;
    z-index: 2147483647;
    box-shadow: 0 4px 12px rgba(0,0,0,0.25);
    opacity: 1;
    transition: opacity 0.4s ease;
  `;
  toast.textContent = text;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => toast.remove(), 400);
  }, 3000);
}