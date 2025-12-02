/* Core state */
const USER_ID = "user123"; // placeholder until auth wires in
let activeChatId = localStorage.getItem("chat_id") || null;
let currentPDF = null;
let streamController = null;
let isSidebarOpen = true;

/* DOM refs */
const sidebar = document.getElementById("sidebar");
const sidebarToggle = document.getElementById("sidebarToggle");
const chatListEl = document.getElementById("chatList");
const newChatBtn = document.getElementById("newChatBtn");
const uploadBtn = document.getElementById("uploadBtn");
const uploadInput = document.getElementById("uploadInput");
const pdfSelect = document.getElementById("pdfSelect");
const currentChatTitleEl = document.getElementById("currentChatTitle");
const currentDocLabel = document.getElementById("currentDocLabel");
const chatWindow = document.getElementById("chatWindow");
const placeholder = document.getElementById("placeholder");
const sendBtn = document.getElementById("sendBtn");
const messageInput = document.getElementById("messageInput");
const deleteBtn = document.getElementById("deleteBtn");
const themePicker = document.getElementById("themePicker");
const appRoot = document.getElementById("appRoot");

const chatSources = (() => {
  try {
    const raw = localStorage.getItem("chat_sources");
    return raw ? JSON.parse(raw) : {};
  } catch (_) {
    return {};
  }
})();

function persistChatSources() {
  try {
    localStorage.setItem("chat_sources", JSON.stringify(chatSources));
  } catch (e) {
    console.error("persistChatSources", e);
  }
}

function persistCurrentPdfForChat() {
  if (!activeChatId) return;
  if (currentPDF) {
    chatSources[activeChatId] = currentPDF;
  } else {
    delete chatSources[activeChatId];
  }
  persistChatSources();
}

function setCurrentPdf(pdfName, { persist = true } = {}) {
  currentPDF = pdfName || null;
  if (pdfSelect) {
    if (currentPDF) {
      const exists = Array.from(pdfSelect.options).some((o) => o.value === currentPDF);
      if (!exists) {
        currentPDF = pdfSelect.options.length ? pdfSelect.options[0].value : null;
      }
    }
    pdfSelect.value = currentPDF || "";
  }
  currentDocLabel.textContent = currentPDF || "No PDF selected";
  if (persist) {
    persistCurrentPdfForChat();
  }
}

function applyChatPdfPreference(chatId) {
  if (!chatId) {
    currentDocLabel.textContent = currentPDF || "No PDF selected";
    return;
  }
  const stored = chatSources[chatId];
  if (stored) {
    setCurrentPdf(stored, { persist: false });
  } else if (!currentPDF && pdfSelect.options.length) {
    setCurrentPdf(pdfSelect.options[0].value, { persist: false });
  } else {
    currentDocLabel.textContent = currentPDF || "No PDF selected";
    if (pdfSelect) pdfSelect.value = currentPDF || "";
  }
}

function snippetFromMarkdown(md, maxLen = 90) {
  if (!md) return "";
  let text = String(md);
  text = text.replace(/```[\s\S]*?```/g, " ");
  text = text.replace(/`([^`]+)`/g, "$1");
  text = text.replace(/\[(.+?)\]\((https?:\/\/[^\s)]+)\)/gi, "$1");
  text = text.replace(/[*_#>-]/g, " ");
  text = text.replace(/\s+/g, " ").trim();
  return text.slice(0, maxLen);
}

/* Theme handling */
function applyTheme(theme) {
  document.documentElement.classList.remove("dark", "coffee");
  if (theme === "system") {
    const dark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    if (dark) document.documentElement.classList.add("dark");
    else document.documentElement.classList.remove("dark");
  } else if (theme === "dark") {
    document.documentElement.classList.add("dark");
  } else if (theme === "coffee") {
    document.documentElement.classList.add("coffee");
  } else {
    document.documentElement.classList.remove("dark", "coffee");
  }
  appRoot.classList.add("theme-fade");
  setTimeout(() => appRoot.classList.remove("theme-fade"), 360);
  localStorage.setItem("theme", theme);
}

themePicker.value = localStorage.getItem("theme") || "system";
applyTheme(themePicker.value);
themePicker.onchange = () => applyTheme(themePicker.value);

function escapeHtmlRaw(s) {
  if (s === null || s === undefined) return "";
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function safeLinkUrl(url) {
  if (!url) return null;
  const trimmed = url.trim();
  if (!/^https?:\/\//i.test(trimmed)) return null;
  return trimmed;
}

function applyInlineFormatting(text) {
  if (text === null || text === undefined) return "";
  let html = escapeHtmlRaw(String(text));
  const codePlaceholders = [];
  html = html.replace(/`([^`]+)`/g, (_, code) => {
    const token = `__CODE_${codePlaceholders.length}__`;
    codePlaceholders.push(`<code>${code}</code>`);
    return token;
  });
  html = html.replace(/~~(.*?)~~/g, "<s>$1</s>");
  html = html.replace(/(\*\*\*|___)(.+?)\1/g, "<strong><em>$2</em></strong>");
  html = html.replace(/(\*\*|__)(.+?)\1/g, "<strong>$2</strong>");
  html = html.replace(/(^|[^*])\*(?!\*)(.*?)\*(?!\*)/g, "$1<em>$2</em>");
  html = html.replace(/(^|[^_])_(?!_)(.*?)_(?!_)/g, "$1<em>$2</em>");
  html = html.replace(/\[(.+?)\]\((https?:\/\/[^\s)]+)\)/gi, (_, label, link) => {
    const safeUrl = safeLinkUrl(link);
    if (!safeUrl) return label;
    return `<a href="${safeUrl}" target="_blank" rel="noopener">${label}</a>`;
  });
  html = html.replace(/__CODE_(\d+)__/g, (_, idx) => codePlaceholders[Number(idx)] || "");
  return html;
}

function markdownToHtml(md) {
  if (!md && md !== 0) return "";
  let normalized = String(md).replace(/\r\n/g, "\n");
  normalized = normalized
    .replace(/([^\n])(#{1,6}\s+)/g, "$1\n$2")
    .replace(/([^\n])([>*+]\s+)/g, "$1\n$2")
    .replace(/([^\n])(\-\s+)/g, "$1\n$2")
    .replace(/([^\n])(\d+\.\s+)/g, "$1\n$2")
    .replace(/([^\n])([=-]{3,})(?=[^\n])/g, "$1\n$2")
    .replace(/([=-]{3,})([^\n])/g, "$1\n$2");
  const lines = normalized.split("\n");
  const parts = [];
  let paragraph = [];
  let listItems = [];
  let listType = null;
  let inCodeBlock = false;
  let codeLang = "";
  let codeLines = [];
  let pendingHeadingLevel = null;

  const flushParagraph = () => {
    if (!paragraph.length) return;
    const content = paragraph.map((line) => applyInlineFormatting(line)).join("<br>");
    parts.push(`<p>${content}</p>`);
    paragraph = [];
  };

  const flushList = () => {
    if (!listType || !listItems.length) return;
    const items = listItems.map((item) => `<li>${applyInlineFormatting(item)}</li>`).join("");
    parts.push(`<${listType}>${items}</${listType}>`);
    listItems = [];
    listType = null;
  };

  const flushCodeBlock = () => {
    const langAttr = codeLang ? ` data-lang="${escapeHtmlRaw(codeLang)}"` : "";
    parts.push(`<pre><code${langAttr}>${escapeHtmlRaw(codeLines.join("\n"))}</code></pre>`);
    codeLines = [];
    codeLang = "";
  };

  for (const rawLine of lines) {
    const trimmedRight = rawLine.replace(/\s+$/g, "");
    const stripped = trimmedRight.trim();

    if (stripped.startsWith("```")) {
      if (!inCodeBlock) {
        flushParagraph();
        flushList();
        inCodeBlock = true;
        codeLang = stripped.slice(3).trim();
      } else {
        flushCodeBlock();
        inCodeBlock = false;
      }
      continue;
    }

    if (inCodeBlock) {
      codeLines.push(rawLine);
      continue;
    }

    if (!stripped) {
      flushParagraph();
      flushList();
      continue;
    }

    if (/^#{1,6}\s+/.test(stripped)) {
      flushParagraph();
      flushList();
      const headingText = stripped.replace(/^#{1,6}\s+/, "");
      parts.push(`<p class="msg-heading"><strong>${applyInlineFormatting(headingText)}</strong></p>`);
      continue;
    }

    if (/^#{1,6}$/.test(stripped)) {
      flushParagraph();
      flushList();
      pendingHeadingLevel = stripped.length;
      continue;
    }

    if (pendingHeadingLevel) {
      flushParagraph();
      flushList();
      parts.push(`<p class="msg-heading"><strong>${applyInlineFormatting(stripped)}</strong></p>`);
      pendingHeadingLevel = null;
      continue;
    }

    const inlineUnderline = stripped.match(/^(.+?)([=-]{3,})$/);
    if (inlineUnderline && inlineUnderline[1].trim()) {
      flushParagraph();
      flushList();
      parts.push(`<p class="msg-heading"><strong>${applyInlineFormatting(inlineUnderline[1].trim())}</strong></p>`);
      continue;
    }

    if (/^>\s+/.test(stripped)) {
      flushParagraph();
      flushList();
      const quote = stripped.replace(/^>\s+/, "");
      parts.push(`<blockquote>${applyInlineFormatting(quote)}</blockquote>`);
      continue;
    }

    if (/^[-*+]\s+/.test(stripped)) {
      flushParagraph();
      if (listType && listType !== "ul") flushList();
      listType = "ul";
      listItems.push(stripped.replace(/^[-*+]\s+/, ""));
      continue;
    }

    if (/^\d+\.\s+/.test(stripped)) {
      flushParagraph();
      if (listType && listType !== "ol") flushList();
      listType = "ol";
      listItems.push(stripped.replace(/^\d+\.\s+/, ""));
      continue;
    }

    if (/^={3,}\s*$/.test(stripped) && paragraph.length) {
      const headingText = paragraph.join(" ").trim();
      paragraph = [];
      parts.push(`<p class="msg-heading"><strong>${applyInlineFormatting(headingText)}</strong></p>`);
      continue;
    }

    if (/^-{3,}\s*$/.test(stripped) && paragraph.length) {
      const headingText = paragraph.join(" ").trim();
      paragraph = [];
      parts.push(`<p class="msg-heading"><strong>${applyInlineFormatting(headingText)}</strong></p>`);
      continue;
    }

    if (/^[-*_]{3,}\s*$/.test(stripped)) {
      flushParagraph();
      flushList();
      parts.push('<hr class="msg-divider" />');
      continue;
    }

    paragraph.push(trimmedRight.trim());
  }

  if (inCodeBlock) {
    flushCodeBlock();
  }

  flushParagraph();
  flushList();

  const html = parts.join("");
  if (!html) {
    return `<p>${applyInlineFormatting(normalized)}</p>`;
  }
  return html;
}

async function generateDynamicTitle(userMsg, assistantMsg) {
  let text = assistantMsg || userMsg || "New Chat";
  if (assistantMsg && assistantMsg.length > 40) {
    text = assistantMsg;
  }
  text = text.replace(/\s+/g, " ").trim();
  if (userMsg && userMsg.includes("?")) {
    text = userMsg.replace(/\?+$/, "").trim();
  }
  let title = text;
  const separators = [":", "—", " - ", ". "];
  for (const sep of separators) {
    if (title.includes(sep)) {
      title = title.split(sep)[0].trim();
      break;
    }
  }
  if (title.length > 48) {
    const words = title.split(" ");
    let acc = "";
    for (const w of words) {
      if ((acc + " " + w).trim().length > 48) break;
      acc = (acc + " " + w).trim();
    }
    if (acc) title = acc;
    else title = title.slice(0, 48);
  }
  title = title.charAt(0).toUpperCase() + title.slice(1);
  title = title.replace(/[.,:;!?]+$/, "");
  if (title.length < 3) title = "New Chat";
  return title;
}

function isMobile() {
  return window.innerWidth <= 900;
}

function setSidebar(open) {
  isSidebarOpen = !!open;
  if (isMobile()) {
    if (isSidebarOpen) {
      sidebar.classList.add("open");
      sidebar.classList.remove("closed");
      sidebar.setAttribute("aria-hidden", "false");
      sidebarToggle.setAttribute("aria-expanded", "true");
    } else {
      sidebar.classList.remove("open");
      sidebar.classList.add("closed");
      sidebar.setAttribute("aria-hidden", "true");
      sidebarToggle.setAttribute("aria-expanded", "false");
    }
  } else {
    if (isSidebarOpen) {
      sidebar.classList.remove("closed");
      sidebar.classList.add("open");
      sidebar.setAttribute("aria-hidden", "false");
      sidebarToggle.setAttribute("aria-expanded", "true");
    } else {
      sidebar.classList.add("closed");
      sidebar.classList.remove("open");
      sidebar.setAttribute("aria-hidden", "true");
      sidebarToggle.setAttribute("aria-expanded", "false");
    }
  }
}

setSidebar(!isMobile());
window.addEventListener("resize", () => {
  if (!isMobile()) setSidebar(true);
  else setSidebar(false);
});

sidebarToggle.onclick = () => setSidebar(!isSidebarOpen);
document.addEventListener("keydown", (e) => {
  if (e.key.toLowerCase() === "c" && !e.metaKey && !e.ctrlKey && !e.altKey) {
    setSidebar(!isSidebarOpen);
  }
});

document.addEventListener("click", (e) => {
  if (isMobile() && isSidebarOpen && !sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) {
    setSidebar(false);
  }
});

async function loadPDFs(preferredTarget) {
  try {
    const res = await fetch("/api/pdf/list");
    const data = await res.json();
    pdfSelect.innerHTML = "";
    if (!data.files || data.files.length === 0) {
      const opt = document.createElement("option");
      opt.textContent = "No PDFs found";
      opt.value = "";
      pdfSelect.appendChild(opt);
      setCurrentPdf(null, { persist: false });
      return;
    }
    data.files.forEach((f) => {
      const opt = document.createElement("option");
      opt.value = f;
      opt.textContent = f;
      pdfSelect.appendChild(opt);
    });
    const preferredFromChat = activeChatId ? chatSources[activeChatId] : null;
    const initial = preferredTarget || preferredFromChat || currentPDF || (pdfSelect.options[0]?.value ?? null);
    let target = initial;
    if (target && !Array.from(pdfSelect.options).some((o) => o.value === target)) {
      target = pdfSelect.options.length ? pdfSelect.options[0].value : null;
    }
    setCurrentPdf(target, { persist: false });
  } catch (e) {
    console.error("loadPDFs", e);
  }
}

pdfSelect.onchange = () => {
  setCurrentPdf(pdfSelect.value || null);
};

uploadBtn.onclick = () => uploadInput.click();
uploadInput.onchange = async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const form = new FormData();
  form.append("file", file);
  uploadBtn.disabled = true;
  uploadBtn.textContent = "Uploading...";
  try {
    const res = await fetch("/api/upload-and-process", { method: "POST", body: form });
    if (!res.ok) {
      const txt = await res.text();
      alert("Upload failed: " + txt);
    } else {
      const data = await res.json();
      await loadPDFs(data.filename || file.name);
      setCurrentPdf(data.filename || file.name);
    }
  } catch (err) {
    console.error("upload", err);
  } finally {
    uploadBtn.disabled = false;
    uploadBtn.textContent = "Upload PDF";
    uploadInput.value = "";
  }
};

async function loadChatList() {
  try {
    const res = await fetch("/api/chats");
    const data = await res.json();
    const chats = data.chats || [];
    chatListEl.innerHTML = "";
    chats.forEach((c) => {
      const el = document.createElement("div");
      el.className = "chat-item";
      el.dataset.chatId = c.chat_id;
      if (activeChatId && activeChatId === c.chat_id) el.classList.add("active");
      const snippet = snippetFromMarkdown(c.last_message || "");
      el.innerHTML = `<div class="meta"><div class="chat-title">${escapeHtmlRaw(c.title)}</div><div class="chat-snippet">${escapeHtmlRaw(snippet)}</div></div>
                      <div class="small">${c.ts ? new Date(c.ts * 1000).toLocaleString() : ""}</div>`;
      el.onclick = async () => {
        await selectChat(c.chat_id, c.title);
        if (isMobile()) setSidebar(false);
      };
      chatListEl.appendChild(el);
    });
    if (!activeChatId && chats.length > 0) {
      activeChatId = chats[0].chat_id;
      localStorage.setItem("chat_id", activeChatId);
      await loadChatHistory(activeChatId);
      updateHeaderTitle(chats[0].title);
      applyChatPdfPreference(activeChatId);
    }
  } catch (e) {
    console.error("loadChatList", e);
  }
}

newChatBtn.onclick = async () => {
  try {
    const res = await fetch("/api/chats/new", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: "New chat" }),
    });
    const data = await res.json();
    activeChatId = data.chat_id;
    localStorage.setItem("chat_id", activeChatId);
    await loadChatList();
    chatWindow.innerHTML = '<div class="placeholder small">New chat created. Select a PDF and ask a question.</div>';
    updateHeaderTitle(data.title || "New chat");
    persistCurrentPdfForChat();
    if (isMobile()) setSidebar(false);
  } catch (e) {
    console.error("newChat", e);
  }
};

deleteBtn.onclick = async () => {
  if (!activeChatId) return alert("No chat selected");
  if (!confirm("Delete this chat? This cannot be undone.")) return;
  try {
    await fetch(`/api/chats/${activeChatId}`, { method: "DELETE" });
    localStorage.removeItem("chat_id");
    delete chatSources[activeChatId];
    persistChatSources();
    activeChatId = null;
    await loadChatList();
    chatWindow.innerHTML = '<div class="placeholder small">Chat deleted. Create or select a chat.</div>';
    updateHeaderTitle("New chat");
  } catch (e) {
    console.error("delete", e);
  }
};

async function selectChat(chatId, title) {
  activeChatId = chatId;
  localStorage.setItem("chat_id", chatId);
  [...chatListEl.children].forEach((n) => n.classList.remove("active"));
  const node = chatListEl.querySelector(`[data-chat-id="${chatId}"]`);
  if (node) node.classList.add("active");
  updateHeaderTitle(title || "Chat");
  await loadChatHistory(chatId);
  applyChatPdfPreference(chatId);
}

function updateHeaderTitle(title) {
  currentChatTitleEl.textContent = title || "New chat";
}

async function loadChatHistory(chatId) {
  try {
    const res = await fetch(`/api/chats/${chatId}`);
    if (!res.ok) {
      chatWindow.innerHTML = '<div class="placeholder small">Failed to load chat.</div>';
      return;
    }
    const data = await res.json();
    const history = data.history || [];
    chatWindow.innerHTML = "";
    if (history.length === 0) {
      chatWindow.innerHTML = '<div class="placeholder small">No messages yet. Ask a question to start the conversation.</div>';
      return;
    }
    for (const m of history) {
      const d = document.createElement("div");
      d.className = "msg " + (m.role === "user" ? "user" : "assistant");
      d.innerHTML = markdownToHtml(m.message);
      chatWindow.appendChild(d);
    }
    chatWindow.scrollTop = chatWindow.scrollHeight;
  } catch (e) {
    console.error("loadChatHistory", e);
    chatWindow.innerHTML = '<div class="placeholder small">Failed to load chat.</div>';
  }
}

sendBtn.onclick = sendQuestion;
messageInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) sendQuestion();
});

async function sendQuestion() {
  const q = messageInput.value.trim();
  if (!q) return;
  if (!currentPDF) {
    alert("Please select a PDF from the sidebar.");
    if (isMobile()) setSidebar(true);
    else setSidebar(true);
    return;
  }
  persistCurrentPdfForChat();
  await ensureActiveChat();
  if (isMobile()) setSidebar(false);
  addLocalMessage("user", q);
  if (!currentChatTitleEl.textContent || currentChatTitleEl.textContent === "New chat") {
    const title = await generateDynamicTitle(q, null);
    updateHeaderTitle(title);
    renameChatOnServer(activeChatId, title);
  }
  messageInput.value = "";
  if (streamController) {
    try {
      streamController.abort();
    } catch (e) {}
    streamController = null;
  }
  streamController = new AbortController();
  const signal = streamController.signal;
  let searchingBubble = document.createElement("div");
  searchingBubble.className = "msg assistant";
  searchingBubble.innerHTML = "<em>Searching document and preparing answer...</em>";
  chatWindow.appendChild(searchingBubble);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  const typingBubble = document.createElement("div");
  typingBubble.className = "typing";
  try {
    const res = await fetch("/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chat_id: activeChatId, question: q, source: currentPDF }),
      signal,
    });
    if (!res.ok) {
      const txt = await res.text();
      if (searchingBubble) searchingBubble.remove();
      addLocalMessage("assistant", "Error: " + txt);
      return;
    }
    if (searchingBubble) searchingBubble.remove();
    chatWindow.appendChild(typingBubble);
    chatWindow.scrollTop = chatWindow.scrollHeight;
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let partial = "";
    let bubble = null;
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      const parts = chunk.split("\n");
      for (const p of parts) {
        if (!p) continue;
        if (!p.startsWith("data: ")) continue;
        const payload = p.replace("data: ", "");
        if (payload === "[END]") {
          if (bubble) bubble.dataset.partial = "done";
          if (typingBubble) typingBubble.remove();
          await loadChatList();
          const assistantCount = document.querySelectorAll(".msg.assistant").length;
          if (assistantCount === 1) {
            const newTitle = await generateDynamicTitle(null, partial);
            updateHeaderTitle(newTitle);
            renameChatOnServer(activeChatId, newTitle);
          }
          return;
        }
        try {
          const parsed = JSON.parse(payload);
          if (parsed && parsed.error) {
            if (typingBubble) typingBubble.remove();
            addLocalMessage("assistant", "Error: " + parsed.error);
            return;
          }
        } catch (_) {}
        partial += payload;
        if (!bubble) {
          if (typingBubble) typingBubble.remove();
          bubble = document.createElement("div");
          bubble.className = "msg assistant";
          bubble.dataset.partial = "1";
          chatWindow.appendChild(bubble);
        }
        bubble.innerHTML = markdownToHtml(partial);
        chatWindow.scrollTop = chatWindow.scrollHeight;
      }
    }
    if (typingBubble) typingBubble.remove();
    await loadChatList();
  } catch (err) {
    if (err.name === "AbortError") {
      addLocalMessage("assistant", "Generation stopped.");
    } else {
      addLocalMessage("assistant", "Connection error: " + (err.message || err));
    }
  } finally {
    streamController = null;
    try {
      if (typingBubble) typingBubble.remove();
    } catch (e) {}
    try {
      if (searchingBubble) searchingBubble.remove();
    } catch (e) {}
    await loadChatList();
  }
}

async function renameChatOnServer(chatId, newTitle) {
  if (!chatId) return;
  try {
    await fetch(`/api/chats/${chatId}/rename`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: newTitle }),
    });
    await loadChatList();
  } catch (e) {
    console.error("Could not rename chat:", e);
  }
}

async function ensureActiveChat() {
  if (activeChatId) return;
  try {
    const res = await fetch("/api/chats/new", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: "Quick Chat" }),
    });
    const data = await res.json();
    activeChatId = data.chat_id;
    localStorage.setItem("chat_id", activeChatId);
    await loadChatList();
    updateHeaderTitle(data.title || "Chat");
    persistCurrentPdfForChat();
  } catch (e) {
    console.error("ensureActiveChat", e);
  }
}

function addLocalMessage(role, text) {
  const ph = document.getElementById("placeholder");
  if (ph) ph.remove();
  const d = document.createElement("div");
  d.className = "msg " + (role === "user" ? "user" : "assistant");
  d.innerHTML = markdownToHtml(text);
  chatWindow.appendChild(d);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

(async () => {
  await loadPDFs();
  await loadChatList();
  if (activeChatId) {
    try {
      await loadChatHistory(activeChatId);
      const res = await fetch("/api/chats");
      const data = await res.json();
      const found = (data.chats || []).find((c) => c.chat_id === activeChatId);
      if (found) updateHeaderTitle(found.title);
      applyChatPdfPreference(activeChatId);
    } catch (e) {
      console.error("init load", e);
    }
  }
})();
