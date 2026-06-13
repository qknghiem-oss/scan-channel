// === KI-Landschaft 2026 — Reader-First App ===

const CATEGORY_META = {
  claude:        { label: "Claude / Anthropic",   color: "#8b5cf6", icon: "🟣" },
  agents:        { label: "AI Agents & Coding",    color: "#3b82f6", icon: "🔵" },
  interview:     { label: "Experten-Interviews",   color: "#10b981", icon: "🟢" },
  robotik:       { label: "Robotik & Hardware",    color: "#06b6d4", icon: "🩵" },
  business:      { label: "Business & Wirtschaft", color: "#f59e0b", icon: "🟠" },
  "google-openai": { label: "Google & OpenAI",     color: "#fbbf24", icon: "🟡" },
  tools:         { label: "Tools & Use Cases",     color: "#14b8a6", icon: "🟢" },
  geopolitik:    { label: "China & Geopolitik",    color: "#ef4444", icon: "🔴" },
};

const STATE = {
  book: null,           // book.json
  videos: [],           // legacy videos.json
  graph: { concepts: {}, connections: [] },
  currentView: "book",
  currentSection: null, // section.id when reading
  searchQuery: "",
  filterCategory: "",
  sortBy: "date",
  sectionsRead: new Set(JSON.parse(localStorage.getItem("sections_read") || "[]")),
};

// === Load Data (sequential — vermeidet TCP-Resets bei lokalem Python-Server) ===
(async function loadData() {
  try {
    const bookRes = await fetch("data/book.json");
    STATE.book = await bookRes.json();
    const vRes = await fetch("data/videos.json");
    STATE.videos = (await vRes.json()).videos;
    try {
      const gRes = await fetch("data/graph.json");
      STATE.graph = await gRes.json();
    } catch {
      STATE.graph = { concepts: {}, connections: [] };
    }
    init();
  } catch (err) {
    document.getElementById("main").innerHTML = `<div class="card"><h2>⚠️ Fehler beim Laden</h2><pre>${err.message}</pre></div>`;
  }
})();

function init() {
  renderBookTOC();
  renderBookWelcome();
  renderFilterOptions();
  renderLibrary();
  renderPaths();
  renderConceptGraph();
  renderTimeline();
  bindNav();
  bindSearch();
  bindFilters();
  bindModal();
  bindDeepDiveTab();
  bindPerVideoTabs();
  bindPraxisCatFilter();
  bindUsecaseSearch();
  loadDeepDiveData();
  loadPerVideoData();
  syncRefreshState();
  updateProgressBadge();

  // Optional: deep-link to section via #SECTION_ID
  if (window.location.hash) {
    const sid = window.location.hash.replace("#", "");
    if (findSection(sid)) loadSection(sid);
  }
}

// === Section Resolution ===
function findSection(sectionId) {
  for (const ch of STATE.book.chapters) {
    for (const s of ch.sections) {
      if (s.id === sectionId) return { section: s, chapter: ch };
    }
  }
  return null;
}

function getAllSectionsFlat() {
  const all = [];
  for (const ch of STATE.book.chapters) {
    for (const s of ch.sections) {
      all.push({ ...s, chapter: ch });
    }
  }
  return all;
}

function findNextSection(sectionId) {
  const all = getAllSectionsFlat();
  const idx = all.findIndex(s => s.id === sectionId);
  return idx >= 0 && idx < all.length - 1 ? all[idx + 1] : null;
}
function findPrevSection(sectionId) {
  const all = getAllSectionsFlat();
  const idx = all.findIndex(s => s.id === sectionId);
  return idx > 0 ? all[idx - 1] : null;
}

// === Book TOC ===
function renderBookTOC() {
  const root = document.getElementById("book-toc");
  root.innerHTML = "";
  for (const ch of STATE.book.chapters) {
    const chDiv = document.createElement("div");
    chDiv.className = "toc-chapter";
    chDiv.dataset.chapter = ch.number;

    const title = document.createElement("div");
    title.className = "toc-chapter-title";
    title.innerHTML = `
      <span class="toc-chapter-num">${ch.number.toString().padStart(2, "0")}</span>
      <span class="toc-ch-title">${escapeHtml(ch.title)}</span>
      <span class="toc-chapter-tier ${ch.tier}">${ch.tier}</span>
    `;
    title.addEventListener("click", () => {
      chDiv.classList.toggle("open");
    });
    chDiv.appendChild(title);

    const secsDiv = document.createElement("div");
    secsDiv.className = "toc-sections";
    for (const s of ch.sections) {
      const sDiv = document.createElement("div");
      sDiv.className = "toc-section";
      sDiv.dataset.sectionId = s.id;
      if (STATE.sectionsRead.has(s.id)) sDiv.classList.add("read");
      sDiv.innerHTML = `
        <span class="toc-section-num">${s.id}</span>
        <span>${escapeHtml(s.title)}</span>
      `;
      sDiv.addEventListener("click", () => loadSection(s.id));
      secsDiv.appendChild(sDiv);
    }
    chDiv.appendChild(secsDiv);
    root.appendChild(chDiv);
  }

  // Alle Kapitel von Anfang an offen — vollständiges Inhaltsverzeichnis sichtbar
  root.querySelectorAll(".toc-chapter").forEach(el => el.classList.add("open"));
}

// === Welcome ===
function renderBookWelcome() {
  document.getElementById("ws-words").textContent = STATE.book.stats.total_words.toLocaleString("de-DE");
  document.getElementById("ws-quotes").textContent = STATE.book.stats.total_quotes;
  document.getElementById("ws-readmin").textContent = Math.round(STATE.book.stats.total_words / 200);
}

// === ElevenLabs Text-to-Speech mit Segmenten (Server-Side) ===
const TTS = {
  audio: null,
  voices: {},
  voice: null,
  rate: 1.0,
  model: "eleven_flash_v2_5",
  state: "idle",           // idle | loading | playing | paused
  segments: [],            // Liste der Segmente fuer aktuelle Sektion
  currentSegIdx: 0,
  autoNext: true,
};

async function ttsInit() {
  try {
    const r = await fetch("/tts/voices");
    const data = await r.json();
    TTS.voices = data.voices;
    TTS.voice = localStorage.getItem("tts_voice") || data.default;
    TTS.model = data.model;
    const savedRate = localStorage.getItem("tts_rate");
    if (savedRate) TTS.rate = parseFloat(savedRate);
  } catch (e) {
    console.error("TTS init failed:", e);
    TTS.unsupported = true;
  }
}

function ttsStop() {
  if (TTS.audio) {
    TTS.audio.pause();
    TTS.audio.currentTime = 0;
  }
  TTS.state = "idle";
  TTS.currentSegIdx = 0;
  ttsUpdateUI();
  ttsHighlightSegment(-1);
}

async function ttsLoadSegments(sectionId) {
  try {
    const r = await fetch(`/tts/segments?section=${encodeURIComponent(sectionId)}`);
    const data = await r.json();
    TTS.segments = data.segments || [];
    TTS.currentSegIdx = 0;
  } catch (e) {
    console.error("TTS segments load failed:", e);
    TTS.segments = [];
  }
}

async function ttsPlaySegment(segIdx) {
  if (segIdx < 0 || segIdx >= TTS.segments.length) {
    ttsStop();
    return;
  }
  TTS.currentSegIdx = segIdx;
  TTS.state = "loading";
  ttsUpdateUI();
  ttsHighlightSegment(segIdx);

  if (TTS.audio) {
    // Listener entfernen, sonst feuert onerror auf dem alten Audio (durch src="")
    // asynchron und setzt TTS.state="idle" — das kollidiert mit dem neuen Segment.
    TTS.audio.onloadedmetadata = null;
    TTS.audio.onplay = null;
    TTS.audio.onpause = null;
    TTS.audio.onended = null;
    TTS.audio.ontimeupdate = null;
    TTS.audio.onerror = null;
    TTS.audio.pause();
    TTS.audio.removeAttribute("src");
    TTS.audio.load();
  }

  const sectionId = STATE.currentSection;
  const url = `/tts/audio?section=${encodeURIComponent(sectionId)}&seg=${segIdx}&voice=${encodeURIComponent(TTS.voice)}`;
  const audio = new Audio(url);
  audio.playbackRate = TTS.rate;
  audio.preload = "auto";

  audio.onloadedmetadata = () => {
    if (TTS.state === "loading") {
      audio.play();
      TTS.state = "playing";
      ttsUpdateUI();
    }
  };
  audio.onplay = () => { TTS.state = "playing"; ttsUpdateUI(); };
  audio.onpause = () => {
    if (TTS.state === "playing") { TTS.state = "paused"; ttsUpdateUI(); }
  };
  audio.onended = () => {
    if (TTS.autoNext && segIdx + 1 < TTS.segments.length) {
      ttsPlaySegment(segIdx + 1);
    } else {
      TTS.state = "idle";
      ttsHighlightSegment(-1);
      ttsUpdateUI();
    }
  };
  audio.ontimeupdate = () => ttsUpdateUI();
  audio.onerror = () => {
    console.error("TTS audio error", audio.error);
    TTS.state = "idle";
    const bar = document.getElementById("tts-bar");
    if (bar) bar.querySelector(".tts-status").textContent = "⚠ Fehler — siehe Konsole";
    ttsUpdateUI();
  };

  TTS.audio = audio;
}

async function ttsPlay() {
  if (TTS.state === "paused" && TTS.audio) {
    TTS.audio.play();
    TTS.state = "playing";
    ttsUpdateUI();
    return;
  }
  if (TTS.state === "playing") return;

  const sectionId = STATE.currentSection;
  if (!sectionId) return;

  if (TTS.segments.length === 0) {
    await ttsLoadSegments(sectionId);
  }
  if (TTS.segments.length === 0) {
    alert("Keine Segmente verfügbar.");
    return;
  }
  ttsPlaySegment(TTS.currentSegIdx || 0);
}

function ttsPause() {
  if (TTS.audio) {
    TTS.audio.pause();
    TTS.state = "paused";
    ttsUpdateUI();
  }
}

function ttsNextSeg() {
  if (TTS.currentSegIdx + 1 < TTS.segments.length) {
    ttsPlaySegment(TTS.currentSegIdx + 1);
  }
}
function ttsPrevSeg() {
  if (TTS.currentSegIdx > 0) {
    ttsPlaySegment(TTS.currentSegIdx - 1);
  }
}

function ttsSeek(seconds) {
  if (TTS.audio) {
    TTS.audio.currentTime = Math.max(0, Math.min(TTS.audio.duration || 0, TTS.audio.currentTime + seconds));
  }
}

window.ttsJumpToSegment = function(segIdx) {
  ttsPlaySegment(segIdx);
};

function ttsHighlightSegment(idx) {
  document.querySelectorAll(".tts-seg-active").forEach(el => el.classList.remove("tts-seg-active"));
  document.querySelectorAll(".tts-seg-marker").forEach(el => el.classList.remove("active"));
  if (idx < 0) return;
  // Markiere zugehoeriges H2 im Artikel
  const headings = document.querySelectorAll(".book-content article h1, .book-content article h2");
  if (headings[idx]) {
    headings[idx].classList.add("tts-seg-active");
    headings[idx].scrollIntoView({ behavior: "smooth", block: "center" });
  }
  // Markiere Chip in der Player-Leiste
  const chip = document.querySelector(`.tts-seg-marker[data-seg="${idx}"]`);
  if (chip) chip.classList.add("active");
}

function ttsUpdateUI() {
  const bar = document.getElementById("tts-bar");
  if (!bar) return;
  const playBtn = bar.querySelector(".tts-play");
  const pauseBtn = bar.querySelector(".tts-pause");
  const stopBtn = bar.querySelector(".tts-stop");
  const status = bar.querySelector(".tts-status");
  const idx = TTS.currentSegIdx;
  const seg = TTS.segments[idx];
  const total = TTS.segments.length;
  const cur = TTS.audio?.currentTime || 0;
  const dur = TTS.audio?.duration || 0;

  if (TTS.state === "playing") {
    playBtn.style.display = "none";
    pauseBtn.style.display = "inline-flex";
    stopBtn.disabled = false;
    status.innerHTML = `▶ <strong>${idx + 1}/${total}</strong> · ${escapeHtml(seg?.title || "")} <span style="color:var(--text-muted)">${formatTtsTime(cur)} / ${formatTtsTime(dur)}</span>`;
  } else if (TTS.state === "paused") {
    playBtn.style.display = "inline-flex";
    pauseBtn.style.display = "none";
    stopBtn.disabled = false;
    status.innerHTML = `⏸ <strong>${idx + 1}/${total}</strong> · ${escapeHtml(seg?.title || "")}`;
  } else if (TTS.state === "loading") {
    playBtn.style.display = "none";
    pauseBtn.style.display = "none";
    stopBtn.disabled = false;
    status.innerHTML = `<span class="tts-spinner">⏳</span> Audio wird geladen…`;
  } else {
    playBtn.style.display = "inline-flex";
    pauseBtn.style.display = "none";
    stopBtn.disabled = true;
    status.textContent = total > 0
      ? `🎙 ${total} Abschnitte bereit zum Vorlesen`
      : "Vorlesen (ElevenLabs)";
  }
}

function formatTtsTime(s) {
  if (!s || isNaN(s)) return "0:00";
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${String(sec).padStart(2, "0")}`;
}

function buildTtsBar() {
  if (TTS.unsupported) {
    return `<div class="tts-bar"><span class="tts-status">⚠ ElevenLabs nicht verfügbar</span></div>`;
  }
  const voiceOpts = Object.entries(TTS.voices).map(([name, id]) => {
    const sel = id === TTS.voice ? "selected" : "";
    return `<option value="${id}" ${sel}>🎙 ${name}</option>`;
  }).join("");

  // Segment-Marker Chips
  const segChips = TTS.segments.map((s, i) => `
    <button class="tts-seg-marker" data-seg="${i}" onclick="ttsJumpToSegment(${i})" title="${escapeHtml(s.title)} · ${s.est_seconds}s">
      ${i + 1}
    </button>
  `).join("");

  return `
    <div class="tts-bar" id="tts-bar">
      <div class="tts-controls">
        <button class="tts-play primary" title="Vorlesen starten" onclick="ttsPlay()">▶</button>
        <button class="tts-pause" title="Pausieren" onclick="ttsPause()" style="display:none">⏸</button>
        <button class="tts-stop" title="Stop" onclick="ttsStop()" disabled>⏹</button>
        <button title="Vorheriger Abschnitt" onclick="ttsPrevSeg()">⏮</button>
        <button title="Nächster Abschnitt" onclick="ttsNextSeg()">⏭</button>
        <button title="-10 Sekunden" onclick="ttsSeek(-10)">⏪</button>
        <button title="+10 Sekunden" onclick="ttsSeek(10)">⏩</button>
      </div>
      <div class="tts-status-wrap">
        <span class="tts-status">${TTS.segments.length > 0 ? `🎙 ${TTS.segments.length} Abschnitte bereit zum Vorlesen` : "Vorlesen (ElevenLabs)"}</span>
      </div>
      <div class="tts-segs-row">${segChips}</div>
      <div class="tts-settings">
        <select onchange="ttsChangeVoice(this.value)">${voiceOpts}</select>
        <div class="speed-control">
          <span style="color:var(--text-muted);font-size:11px">Tempo</span>
          <input type="range" min="0.7" max="1.6" step="0.1" value="${TTS.rate}" oninput="ttsChangeRate(this.value)">
          <span class="speed-val">${TTS.rate.toFixed(1)}x</span>
        </div>
      </div>
    </div>
  `;
}

window.ttsChangeRate = function(v) {
  TTS.rate = parseFloat(v);
  localStorage.setItem("tts_rate", TTS.rate);
  const valEl = document.querySelector("#tts-bar .speed-val");
  if (valEl) valEl.textContent = TTS.rate.toFixed(1) + "x";
  if (TTS.audio) TTS.audio.playbackRate = TTS.rate;
};

window.ttsChangeVoice = function(voiceId) {
  TTS.voice = voiceId;
  localStorage.setItem("tts_voice", voiceId);
  if (TTS.state === "playing" || TTS.state === "paused") {
    ttsStop();
    ttsPlay();
  }
};

window.ttsSeek = ttsSeek;
window.ttsNextSeg = ttsNextSeg;
window.ttsPrevSeg = ttsPrevSeg;

// Init beim Laden
ttsInit();

// === Section Loader ===
window.loadSection = async function(sectionId) {
  // TTS stoppen beim Sektions-Wechsel
  ttsStop();
  TTS.segments = [];
  const found = findSection(sectionId);
  if (!found) return;
  const { section, chapter } = found;
  STATE.currentSection = sectionId;

  // Segmente fuer diese Sektion laden (asynchron, vor render)
  await ttsLoadSegments(sectionId);

  // Mark TOC
  document.querySelectorAll(".toc-section.active").forEach(e => e.classList.remove("active"));
  document.querySelector(`.toc-section[data-section-id="${sectionId}"]`)?.classList.add("active");

  // Ensure chapter open
  document.querySelector(`.toc-chapter[data-chapter="${chapter.number}"]`)?.classList.add("open");

  // Render content
  const contentEl = document.getElementById("book-content");
  const body = renderMarkdown(section.body_md, sectionId, chapter);

  const prev = findPrevSection(sectionId);
  const next = findNextSection(sectionId);

  contentEl.innerHTML = `
    <article>
      ${buildTtsBar()}
      ${body}
      <nav class="section-nav">
        ${prev ? `<a href="#" class="prev" onclick="loadSection('${prev.id}');return false">
          <span class="nav-direction">← Vorherige Sektion</span>
          <span class="nav-title">${escapeHtml(prev.id)} ${escapeHtml(prev.title)}</span>
        </a>` : '<span></span>'}
        ${next ? `<a href="#" class="next" onclick="loadSection('${next.id}');return false">
          <span class="nav-direction">Nächste Sektion →</span>
          <span class="nav-title">${escapeHtml(next.id)} ${escapeHtml(next.title)}</span>
        </a>` : '<span></span>'}
      </nav>
    </article>
  `;

  // Show aside
  renderAside(section);
  renderMarginalia();
  renderInlineVizs();

  // Mark as read after 5 seconds OR scroll to bottom
  scheduleReadMark(sectionId);

  // Scroll to top
  document.getElementById("book-content").scrollTop = 0;
  window.scrollTo({ top: 0, behavior: "smooth" });

  // Update URL hash
  history.replaceState(null, "", "#" + sectionId);
}

function renderMarkdown(md, sectionId, chapter) {
  // === Marginalia-Marker extrahieren ===
  // Erst die Definitionen am Ende des Dokuments sammeln:
  // [^typ:slug]:
  //   Mehrzeilige Definition
  const marginalia = {};
  md = md.replace(/^\[\^([a-z]+):([a-z0-9-]+)\]:\s*\n((?:[ \t]+.+(?:\n|$))+)/gim, (m, type, slug, def) => {
    const cleanDef = def.split("\n").map(l => l.trim()).filter(Boolean).join("\n");
    marginalia[`${type}:${slug}`] = { type, slug, body: cleanDef };
    return "";  // Aus Fließtext entfernen
  });

  // Marginalia-Inline-Marker [^typ:slug] → <a class="marg-ref">
  md = md.replace(/\[\^([a-z]+):([a-z0-9-]+)\]/g, (m, type, slug) => {
    const key = `${type}:${slug}`;
    const data = marginalia[key];
    if (!data) return m;  // unbekannt — Marker bleibt
    const icon = ({ person: "👤", tool: "🛠", firma: "🏢", zahl: "📊", begriff: "📖", quelle: "📰" })[type] || "ℹ";
    return `<a class="marg-ref" data-mkey="${key}" onclick="scrollToMargin('${key}');return false">${icon}</a>`;
  });

  // === Cross-Refs ===
  md = md.replace(/\[\[([0-9]+\.[0-9]+(?:-[a-z-]+)?)\s+([^\]]+)\]\]/g, (match, sid, title) => {
    return `<a class="crossref" data-section="${sid}" onclick="loadSection('${sid}');return false">${sid} ${title}</a>`;
  });

  // === Video-Timestamps ===
  md = md.replace(/\[([^\]]+)\]\(video:([A-Za-z0-9_-]+)(?:\?t=(\d+))?\)/g, (match, label, vid, secs) => {
    const t = secs ? parseInt(secs) : 0;
    return `<a class="timestamp-link" data-video="${vid}" data-time="${t}" onclick="openVideoAt('${vid}',${t});return false">${label}</a>`;
  });

  // === Visualisierungen {{viz:type|params}} ===
  md = md.replace(/\{\{viz:([a-z-]+)((?:\|[^}]+)*)\}\}/g, (m, type, paramsStr) => {
    const params = {};
    (paramsStr || "").split("|").filter(Boolean).forEach(p => {
      const [k, v] = p.split("=");
      if (k) params[k.trim()] = (v || "").trim();
    });
    const id = "viz-" + Math.random().toString(36).slice(2, 10);
    // Daten-Attribute (escaped)
    const dataAttrs = Object.entries(params)
      .map(([k, v]) => `data-${k}="${escapeHtml(v)}"`).join(" ");
    return `<div class="viz" data-viz="${type}" ${dataAttrs} id="${id}"></div>`;
  });

  let html;
  try {
    html = marked.parse(md);
  } catch (e) {
    html = `<pre>${escapeHtml(md)}</pre>`;
  }

  // Marginalia merken für die Sidebar
  STATE.currentMarginalia = marginalia;
  return html;
}

window.scrollToMargin = function(key) {
  const margEl = document.querySelector(`.marg-card[data-mkey="${key}"]`);
  if (margEl) {
    margEl.classList.add("highlight");
    margEl.scrollIntoView({ behavior: "smooth", block: "center" });
    setTimeout(() => margEl.classList.remove("highlight"), 1500);
  }
};

function renderMarginalia() {
  const root = document.getElementById("book-marginalia");
  if (!root) return;
  const items = Object.values(STATE.currentMarginalia || {});
  if (items.length === 0) {
    root.innerHTML = "";
    root.hidden = true;
    return;
  }
  root.hidden = false;
  const ICONS = { person: "👤", tool: "🛠", firma: "🏢", zahl: "📊", begriff: "📖", quelle: "📰" };
  const TITLES = {
    person: "Person", tool: "Werkzeug", firma: "Unternehmen",
    zahl: "Zahl", begriff: "Begriff", quelle: "Quelle",
  };
  root.innerHTML = `<h3>📎 Marginalien</h3>` + items.map(m => `
    <div class="marg-card" data-mkey="${m.type}:${m.slug}">
      <div class="marg-head">
        <span class="marg-icon">${ICONS[m.type] || "ℹ"}</span>
        <span class="marg-type">${TITLES[m.type] || m.type}</span>
      </div>
      <div class="marg-body">${parseMarginBody(m.body)}</div>
    </div>
  `).join("");
}

function parseMarginBody(body) {
  // Bullet-list ohne -/* erlaubt, einfacher Markdown
  return body.split("\n").map(line => {
    line = line.trim();
    if (!line) return "";
    // Cross-Ref
    line = line.replace(/\[\[([0-9.]+(?:-[a-z-]+)?)\s+([^\]]+)\]\]/g,
      (m, sid, title) => `<a class="crossref" onclick="loadSection('${sid}');return false">${sid} ${title}</a>`);
    // Video-Timestamp
    line = line.replace(/\(video:([A-Za-z0-9_-]+)(?:\?t=(\d+))?\)/g,
      (m, vid, secs) => `<a class="timestamp-link" onclick="openVideoAt('${vid}',${secs || 0});return false">▶ ${secs ? Math.floor(secs/60) + ":" + String(secs%60).padStart(2,"0") : ""}</a>`);
    // Bullet
    if (line.startsWith("- ")) return `<div class="marg-line">${line.slice(2)}</div>`;
    return `<div class="marg-line">${line}</div>`;
  }).join("");
}

// === Inline-Visualisierungen ===
function renderInlineVizs() {
  document.querySelectorAll(".viz").forEach(el => {
    if (el.dataset.rendered) return;
    el.dataset.rendered = "1";
    const type = el.dataset.viz;
    try {
      if (type === "evolution") renderVizEvolution(el);
      else if (type === "compare") renderVizCompare(el);
      else if (type === "timeline") renderVizTimeline(el);
      else if (type === "quote-box") renderVizQuoteBox(el);
      else if (type === "network") renderVizNetwork(el);
      else el.innerHTML = `<em>Unbekannte Visualisierung: ${type}</em>`;
    } catch (e) {
      el.innerHTML = `<em>Fehler bei Visualisierung: ${e.message}</em>`;
    }
  });
}

function renderVizEvolution(el) {
  const versions = (el.dataset.versions || "").split(",").map(s => s.trim());
  const notes = (el.dataset.notes || "").split(",").map(s => s.trim());
  el.innerHTML = `
    <div class="viz-evolution">
      ${versions.map((v, i) => `
        <div class="viz-evo-step">
          <div class="viz-evo-version">${escapeHtml(v)}</div>
          <div class="viz-evo-note">${escapeHtml(notes[i] || "")}</div>
        </div>
        ${i < versions.length - 1 ? '<div class="viz-evo-arrow">→</div>' : ''}
      `).join("")}
    </div>
  `;
}

function renderVizCompare(el) {
  const title = el.dataset.title || "";
  const items = (el.dataset.items || "").split(",").map(s => {
    const [name, val] = s.split(":");
    return { name: (name || "").trim(), value: parseFloat(val) || 0 };
  });
  const max = Math.max(...items.map(i => i.value), 1);
  el.innerHTML = `
    <div class="viz-compare">
      ${title ? `<h4>${escapeHtml(title)}</h4>` : ""}
      ${items.map(i => `
        <div class="viz-comp-row">
          <div class="viz-comp-label">${escapeHtml(i.name)}</div>
          <div class="viz-comp-bar"><div class="viz-comp-fill" style="width:${(i.value / max * 100).toFixed(1)}%">${i.value}</div></div>
        </div>
      `).join("")}
    </div>
  `;
}

function renderVizTimeline(el) {
  const topic = el.dataset.topic || "";
  el.innerHTML = `<div class="viz-timeline-placeholder">📅 Zeitleiste fuer "${escapeHtml(topic)}" — Klick auf Konzept-Wiki fuer Details</div>`;
}

function renderVizQuoteBox(el) {
  const text = el.dataset.text || "";
  const author = el.dataset.author || "";
  el.innerHTML = `
    <blockquote class="viz-quote-box">
      <p>${escapeHtml(text)}</p>
      ${author ? `<footer>— ${escapeHtml(author)}</footer>` : ""}
    </blockquote>
  `;
}

function renderVizNetwork(el) {
  const center = el.dataset.center || "";
  const connects = (el.dataset.connects || "").split(",").map(s => s.trim()).filter(Boolean);
  el.innerHTML = `
    <div class="viz-network">
      <div class="viz-net-center">${escapeHtml(center)}</div>
      <div class="viz-net-spokes">
        ${connects.map(c => `<div class="viz-net-spoke">${escapeHtml(c)}</div>`).join("")}
      </div>
    </div>
  `;
}

function scheduleReadMark(sectionId) {
  setTimeout(() => {
    if (STATE.currentSection === sectionId && !STATE.sectionsRead.has(sectionId)) {
      STATE.sectionsRead.add(sectionId);
      localStorage.setItem("sections_read", JSON.stringify([...STATE.sectionsRead]));
      document.querySelector(`.toc-section[data-section-id="${sectionId}"]`)?.classList.add("read");
      updateProgressBadge();
    }
  }, 5000);
}

function updateProgressBadge() {
  const total = STATE.book.stats.total_sections;
  const read = STATE.sectionsRead.size;
  document.getElementById("progress-badge").textContent = `${read}/${total}`;
}

// === Right Aside ===
function renderAside(section) {
  const aside = document.getElementById("book-aside");
  const sources = document.getElementById("book-sources");
  const related = document.getElementById("book-related");

  aside.hidden = false;

  // Sources
  sources.innerHTML = "";
  for (const v of section.source_videos) {
    const div = document.createElement("div");
    div.className = "aside-source";
    div.innerHTML = `
      <div class="src-title">${escapeHtml(v.title)}</div>
      <div class="src-meta">${Math.round(v.duration_min)} min · ${formatViews(v.view_count)} Views · ${formatDate(v.published_date)}</div>
    `;
    div.addEventListener("click", () => openVideoAt(v.id, 0));
    sources.appendChild(div);
  }

  // Related
  related.innerHTML = "";
  if (!section.crossrefs || section.crossrefs.length === 0) {
    related.innerHTML = `<p style="color: var(--text-muted); font-size: 12px;">Keine Verlinkungen.</p>`;
  } else {
    // Deduplizieren
    const seen = new Set();
    for (const cr of section.crossrefs) {
      if (seen.has(cr.section_id)) continue;
      seen.add(cr.section_id);
      const a = document.createElement("a");
      a.className = "aside-related";
      a.href = "#";
      a.onclick = (e) => { e.preventDefault(); loadSection(cr.section_id); };
      a.innerHTML = `<span class="ar-num">${cr.section_id}</span>${escapeHtml(cr.title)}`;
      related.appendChild(a);
    }
  }
}

// === Video Modal at Timestamp ===
window.openVideoAt = function(videoId, seconds) {
  const v = STATE.videos.find(x => x.id === videoId);
  const modal = document.getElementById("modal");
  const body = document.getElementById("modal-body");

  const start = Math.max(0, seconds || 0);
  const platform = v && v.platform;
  let embedUrl = `https://www.youtube-nocookie.com/embed/${videoId}?start=${start}&autoplay=1`;
  if (platform === "tiktok" || platform === "instagram") {
    embedUrl = v.source_url;
  }

  let title = videoId, dateStr = "", viewStr = "", durStr = "", catMeta = {};
  if (v) {
    title = v.title;
    dateStr = formatDate(v.published_date);
    viewStr = formatViews(v.view_count) + " Views";
    durStr = Math.round(v.duration_min) + " min";
    catMeta = CATEGORY_META[v.category] || { label: v.category, color: "#888" };
  }

  // Chapters Block
  const chapters = (v && v.chapters && v.chapters.length) ? `
    <div class="video-detail-block">
      <div class="video-detail-label">Kapitel (${v.chapters.length})</div>
      <div class="chapter-list">
        ${v.chapters.slice(0,12).map(ch => {
          const t = Math.round(ch.start_time || 0);
          return `<button class="chapter-btn" onclick="openVideoAt('${videoId}',${t})">
            <span class="ch-time">${formatTime(t)}</span>
            <span class="ch-title">${escapeHtml(ch.title || "")}</span>
          </button>`;
        }).join("")}
        ${v.chapters.length > 12 ? `<div style="color:var(--muted);font-size:11px;padding:4px 0">+${v.chapters.length-12} weitere</div>` : ""}
      </div>
    </div>` : "";

  // Beschreibung Block
  const desc = v && v.description ? `
    <div class="video-detail-block">
      <div class="video-detail-label">Beschreibung</div>
      <div class="video-desc">${escapeHtml(v.description.slice(0, 400))}${v.description.length > 400 ? "…" : ""}</div>
    </div>` : "";

  // Buch-Sektionen die dieses Video referenzieren
  const bookRefs = STATE.book ? (() => {
    const refs = [];
    for (const ch of (STATE.book.chapters || [])) {
      for (const sec of (ch.sections || [])) {
        const body = sec.body_md || sec.body || "";
        if (body.includes(videoId)) refs.push({id: sec.id, title: sec.title});
        if (refs.length >= 5) break;
      }
      if (refs.length >= 5) break;
    }
    return refs;
  })() : [];
  const bookRefsHtml = bookRefs.length ? `
    <div class="video-detail-block">
      <div class="video-detail-label">Im Wissensbuch erwähnt</div>
      <div class="video-refs">
        ${bookRefs.map(r => `<button class="ref-btn" onclick="loadSection('${r.id}');document.getElementById('modal').hidden=true">
          📖 ${r.id} — ${escapeHtml(r.title)}
        </button>`).join("")}
      </div>
    </div>` : "";

  // Praxis-Items Block (wenn vorhanden)
  const praxisItems = v && v.praxis_items && v.praxis_items.length ? `
    <div class="video-detail-block praxis-block">
      <div class="video-detail-label">🛠 Praxis-Tipps aus diesem Video</div>
      <ul class="praxis-list">
        ${v.praxis_items.slice(0,5).map(item => `<li>${escapeHtml(item)}</li>`).join("")}
      </ul>
    </div>` : "";

  body.innerHTML = `
    <h2>${escapeHtml(title)}</h2>
    <div class="meta-row">
      <span class="cat-pill" style="background:${catMeta.color}20;color:${catMeta.color};border-color:${catMeta.color}40">${catMeta.label || ""}</span>
      <span>📅 ${dateStr}</span>
      <span>⏱ ${durStr}</span>
      <span>👁 ${viewStr}</span>
      ${start ? `<span style="color: var(--cat-agents)">▶ ${formatTime(start)}</span>` : ""}
    </div>
    <iframe class="video-iframe" src="${embedUrl}" allowfullscreen allow="autoplay"></iframe>
    <div style="margin-top:18px; display:flex; gap:10px; flex-wrap:wrap; align-items:center;">
      ${v ? `<button class="dd-start-btn" onclick="bookmarkPerVideoDeepDive('${videoId}','${escapeHtml(v.title).replace(/'/g,"&#39;")}','${v.category || ""}')">
        🔬 Tiefenanalyse anfordern
      </button>` : ""}
      <a href="https://www.youtube.com/watch?v=${videoId}${start ? '&t=' + start : ''}" target="_blank" rel="noopener" class="yt-link-btn">↗ YouTube</a>
    </div>
    ${praxisItems}
    ${chapters}
    ${bookRefsHtml}
    ${desc}
  `;
  modal.hidden = false;
}

// === Navigation ===
function bindNav() {
  document.querySelectorAll(".tab").forEach(t => {
    t.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach(x => x.classList.remove("active"));
      document.querySelectorAll(".view").forEach(x => x.classList.remove("active"));
      t.classList.add("active");
      const v = t.dataset.view;
      document.getElementById("view-" + v).classList.add("active");
      STATE.currentView = v;
      if (v === "concepts") renderConceptGraph();
      if (v === "praxis") initPraxisView();
    });
  });
}

// === Search ===
function bindSearch() {
  const input = document.getElementById("search");
  input.addEventListener("input", () => {
    STATE.searchQuery = input.value.toLowerCase().trim();
    if (STATE.searchQuery) {
      // Search in book + videos
      runBookSearch(STATE.searchQuery);
    } else {
      // Clear: zurück zum Buch
      if (STATE.currentView === "book" && !STATE.currentSection) {
        renderBookWelcome();
      }
    }
  });
}

function runBookSearch(query) {
  const hits = [];
  for (const ch of STATE.book.chapters) {
    for (const s of ch.sections) {
      const haystack = (s.title + " " + s.body_md).toLowerCase();
      if (haystack.includes(query)) {
        hits.push({ section: s, chapter: ch });
      }
    }
  }

  const contentEl = document.getElementById("book-content");
  document.getElementById("book-aside").hidden = true;

  if (hits.length === 0) {
    contentEl.innerHTML = `<div class="book-welcome"><h1>🔍 Keine Treffer</h1><p class="lead">Im Buch fanden sich keine Stellen zu "${escapeHtml(query)}".</p></div>`;
    return;
  }

  let html = `<div class="book-welcome"><h1>🔍 ${hits.length} Treffer für "${escapeHtml(query)}"</h1><div style="margin-top: 24px;">`;
  for (const h of hits) {
    const snippet = extractSnippet(h.section.body_md, query);
    html += `
      <div style="background: var(--bg-input); border: 1px solid var(--border); border-radius: 8px; padding: 16px; margin-bottom: 12px; cursor: pointer;" onclick="loadSection('${h.section.id}')">
        <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 4px;">${escapeHtml(h.chapter.title)}</div>
        <div style="font-weight: 700; margin-bottom: 8px;">${h.section.id} ${escapeHtml(h.section.title)}</div>
        <div style="font-size: 13px; color: var(--text-secondary); line-height: 1.5;">${snippet}</div>
      </div>
    `;
  }
  html += `</div></div>`;
  contentEl.innerHTML = html;
}

function extractSnippet(text, query) {
  const lower = text.toLowerCase();
  const idx = lower.indexOf(query);
  if (idx === -1) return text.slice(0, 200) + "...";
  const start = Math.max(0, idx - 80);
  const end = Math.min(text.length, idx + query.length + 100);
  let snip = text.slice(start, end);
  // Remove markdown noise
  snip = snip.replace(/[*_>#\[\]\(\)]/g, "");
  return (start > 0 ? "..." : "") + escapeHtml(snip).replace(new RegExp(query, "gi"), m => `<mark style="background: var(--cat-claude); color: white; padding: 1px 4px; border-radius: 3px;">${m}</mark>`) + (end < text.length ? "..." : "");
}

// === Filter ===
function bindFilters() {
  document.getElementById("filter-category").addEventListener("change", e => {
    STATE.filterCategory = e.target.value;
    renderLibrary();
  });
  document.getElementById("filter-sort").addEventListener("change", e => {
    STATE.sortBy = e.target.value;
    renderLibrary();
  });
}

function renderFilterOptions() {
  const sel = document.getElementById("filter-category");
  Object.entries(CATEGORY_META).forEach(([id, meta]) => {
    const opt = document.createElement("option");
    opt.value = id;
    opt.textContent = `${meta.icon} ${meta.label}`;
    sel.appendChild(opt);
  });
}

// === Library ===
function renderLibrary() {
  const grid = document.getElementById("library-grid");
  grid.innerHTML = "";

  let list = STATE.videos.slice();

  if (STATE.filterCategory) {
    list = list.filter(v => v.category === STATE.filterCategory);
  }

  if (STATE.sortBy === "date") {
    list.sort((a, b) => b.published_date.localeCompare(a.published_date));
  } else if (STATE.sortBy === "score") {
    list.sort((a, b) => b.importance_score - a.importance_score || (b.view_count || 0) - (a.view_count || 0));
  } else if (STATE.sortBy === "views") {
    list.sort((a, b) => (b.view_count || 0) - (a.view_count || 0));
  }

  document.getElementById("result-count").textContent = `${list.length} Video${list.length === 1 ? "" : "s"}`;

  if (list.length === 0) {
    grid.innerHTML = `<div class="card" style="grid-column: 1 / -1; text-align: center;"><p>Keine Videos gefunden.</p></div>`;
    return;
  }
  list.forEach(v => grid.appendChild(buildVideoCard(v)));
}

function buildVideoCard(v) {
  const meta = CATEGORY_META[v.category] || { label: v.category, color: "#888" };
  const card = document.createElement("div");
  card.className = "vcard";
  card.style.setProperty("--cat", meta.color);
  const thumbSrc = `https://i.ytimg.com/vi/${v.id}/hqdefault.jpg`;
  card.innerHTML = `
    <img class="thumb" src="${thumbSrc}" alt="" loading="lazy">
    <div class="body">
      <div class="meta">
        <span class="cat-pill">${meta.label}</span>
        <span>${formatDate(v.published_date)}</span>
      </div>
      <div class="vtitle">${escapeHtml(v.title)}</div>
      <div class="vfooter">
        <span>👁 ${formatViews(v.view_count)} · ⏱ ${Math.round(v.duration_min)}min</span>
        <span class="score" style="color: ${meta.color}">★ ${v.importance_score}</span>
      </div>
    </div>
  `;
  card.addEventListener("click", () => openVideoAt(v.id, 0));
  return card;
}

// === Modal ===
function bindModal() {
  document.querySelectorAll("[data-close]").forEach(el => {
    el.addEventListener("click", () => closeModal());
  });
  document.addEventListener("keydown", e => {
    if (e.key === "Escape") closeModal();
  });
}
function closeModal() {
  document.getElementById("modal").hidden = true;
  // Stop video by emptying iframe src
  const iframe = document.querySelector(".video-iframe");
  if (iframe) iframe.src = "";
}

// === Concept Graph ===
function renderConceptGraph() {
  const svg = d3.select("#graph");
  svg.selectAll("*").remove();
  const width = svg.node().clientWidth || 1000;
  const height = 640;

  const concepts = STATE.graph.concepts || {};
  const connections = STATE.graph.connections || [];
  const conceptList = Object.values(concepts).sort((a, b) => (b.video_count || 0) - (a.video_count || 0)).slice(0, 30);
  const conceptSet = new Set(conceptList.map(c => c.label));

  const nodes = conceptList.map(c => ({
    id: c.label, label: c.label, color: c.color, category: c.category,
    radius: 8 + Math.min(c.video_count, 18) * 1.8,
    videos: c.videos, video_count: c.video_count,
  }));
  const links = connections
    .filter(c => conceptSet.has(c.from) && conceptSet.has(c.to))
    .map(c => ({ source: c.from, target: c.to, strength: c.strength }));

  const sim = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links).id(d => d.id).distance(d => 90 - Math.min(d.strength, 8) * 5).strength(0.4))
    .force("charge", d3.forceManyBody().strength(-380))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collide", d3.forceCollide(d => d.radius + 10));

  const zoomGroup = svg.append("g");
  svg.call(d3.zoom().scaleExtent([0.3, 3]).on("zoom", e => zoomGroup.attr("transform", e.transform)));

  const link = zoomGroup.append("g")
    .selectAll("line").data(links).enter().append("line")
    .attr("class", "link").attr("stroke-width", d => 0.6 + Math.min(d.strength, 6) * 0.4);

  const node = zoomGroup.append("g")
    .selectAll("g").data(nodes).enter().append("g")
    .attr("class", "node")
    .call(d3.drag()
      .on("start", (e, d) => { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
      .on("drag", (e, d) => { d.fx = e.x; d.fy = e.y; })
      .on("end", (e, d) => { if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null; })
    );

  node.append("circle")
    .attr("r", d => d.radius).attr("fill", d => d.color).attr("opacity", 0.85);
  node.append("text")
    .attr("text-anchor", "middle").attr("dy", d => d.radius + 14)
    .style("font-size", "11px")
    .text(d => d.label.length > 20 ? d.label.slice(0, 18) + "…" : d.label);

  node.on("click", (e, d) => showConceptDetails(d));
  node.append("title").text(d => `${d.label}\n${d.video_count} Videos · ${d.category}`);

  sim.on("tick", () => {
    link.attr("x1", d => d.source.x).attr("y1", d => d.source.y).attr("x2", d => d.target.x).attr("y2", d => d.target.y);
    node.attr("transform", d => `translate(${d.x},${d.y})`);
  });
}

function showConceptDetails(concept) {
  const videos = STATE.videos.filter(v => concept.videos.includes(v.id));
  const modal = document.getElementById("modal");
  const body = document.getElementById("modal-body");
  body.innerHTML = `
    <h2 style="color: ${concept.color};">${escapeHtml(concept.label)}</h2>
    <div class="meta-row">
      <span style="background: ${concept.color}; color: white; padding: 3px 10px; border-radius: 4px; font-size: 12px;">${concept.category}</span>
      <span>${videos.length} Videos in dieser Sammlung</span>
    </div>
    <button class="dd-start-btn" onclick="startDeepDive('${escapeHtml(concept.label).replace(/'/g, "&#39;")}', '${concept.category}')">
      🔍 Deep Dive auf "${escapeHtml(concept.label)}" starten
    </button>
    <div id="dd-feedback-container"></div>
    <div class="library-grid" id="concept-videos" style="margin-top: 20px;"></div>
  `;
  modal.hidden = false;
  const grid = body.querySelector("#concept-videos");
  videos.forEach(v => grid.appendChild(buildVideoCard(v)));
}

// === Deep Dive: Bookmark erstellen ===
window.startDeepDive = async function(topic, type) {
  const container = document.getElementById("dd-feedback-container");
  if (!container) return;
  container.innerHTML = `<div class="dd-feedback">⏳ Vormerken…</div>`;
  try {
    const res = await fetch("/deep-dive/bookmark", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic, type: type || "concept" }),
    });
    const data = await res.json();
    if (data.status === "ok") {
      container.innerHTML = `<div class="dd-feedback success">✅ "${escapeHtml(topic)}" vorgemerkt. Im Chat: <code>Mache die offenen Deep Dives</code></div>`;
      loadDeepDiveData();
    } else if (data.status === "duplicate") {
      container.innerHTML = `<div class="dd-feedback duplicate">ℹ Bereits vorgemerkt: "${escapeHtml(topic)}"</div>`;
    } else {
      container.innerHTML = `<div class="dd-feedback error">⚠ Fehler: ${escapeHtml(data.error || "unbekannt")}</div>`;
    }
  } catch (e) {
    container.innerHTML = `<div class="dd-feedback error">⚠ Server nicht erreichbar: ${e.message}</div>`;
  }
};

// === Deep Dive: Tab-Daten laden + rendern ===
async function loadDeepDiveData() {
  try {
    const r = await fetch("/deep-dive/list");
    const data = await r.json();
    STATE.dd = data;
    renderDeepDiveTab();
    updateDeepDiveBadge();
  } catch (e) {
    console.error("Deep dive load failed:", e);
  }
}

function updateDeepDiveBadge() {
  if (!STATE.dd) return;
  const total = (STATE.dd.pending || []).length + (STATE.dd.generated || []).length;
  const badge = document.getElementById("dd-badge");
  if (badge) {
    badge.textContent = total;
    badge.hidden = total === 0;
  }
}

function renderDeepDiveTab() {
  const pending = (STATE.dd && STATE.dd.pending) || [];
  const generated = (STATE.dd && STATE.dd.generated) || [];

  document.getElementById("dd-count-pending").textContent = pending.length;
  document.getElementById("dd-count-generated").textContent = generated.length;

  // Generated Grid
  const gen = document.getElementById("dd-generated-grid");
  if (generated.length === 0) {
    gen.innerHTML = `
      <div class="dd-empty" style="grid-column: 1 / -1;">
        <div class="icon">📚</div>
        <h3>Noch keine fertigen Deep Dives</h3>
        <p>Klick im Konzept-Wiki auf ein Thema → "Deep Dive starten"</p>
      </div>`;
  } else {
    gen.innerHTML = "";
    generated.forEach(g => {
      const card = document.createElement("div");
      card.className = "dd-card";
      card.innerHTML = `
        <h3>${escapeHtml(g.topic || g.slug || "—")}</h3>
        <div class="meta">${g.type || "concept"} · ${formatDate((g.generated_at || "").slice(0, 10))}</div>
        <div class="stats">
          <div><strong>${g.word_count || "?"}</strong>Wörter</div>
          <div><strong>${g.sources_count || "?"}</strong>Quellen</div>
        </div>
      `;
      card.addEventListener("click", () => {
        // Springe zur Sektion im Buch
        const sectionId = "dd-" + (g.slug || "");
        document.querySelector('[data-view="book"]').click();
        if (findSection(sectionId)) loadSection(sectionId);
      });
      gen.appendChild(card);
    });
  }

  // Pending Liste
  const pend = document.getElementById("dd-pending-list");
  if (pending.length === 0) {
    pend.innerHTML = `
      <div class="dd-empty">
        <div class="icon">⏳</div>
        <h3>Keine vorgemerkten Deep Dives</h3>
        <p>Klick im Konzept-Wiki auf ein Thema → "Deep Dive starten"</p>
      </div>`;
  } else {
    pend.innerHTML = "";
    pending.forEach(p => {
      const item = document.createElement("div");
      item.className = "dd-pending-item";
      item.innerHTML = `
        <div class="topic">
          <strong>${escapeHtml(p.topic)}</strong>
          <span class="when">Vorgemerkt: ${formatDate(p.bookmarked_at?.slice(0,10) || "")}</span>
        </div>
        <span class="type-pill">${escapeHtml(p.type || "concept")}</span>
        <button class="delete-btn" data-file="${escapeHtml(p.file)}">🗑 Löschen</button>
      `;
      item.querySelector(".delete-btn").addEventListener("click", async (e) => {
        e.stopPropagation();
        if (!confirm(`Vorgemerkten Deep Dive "${p.topic}" löschen?`)) return;
        try {
          await fetch(`/deep-dive/bookmark/${encodeURIComponent(p.file)}`, { method: "DELETE" });
          loadDeepDiveData();
        } catch (err) {
          alert("Fehler beim Löschen: " + err.message);
        }
      });
      pend.appendChild(item);
    });
  }

  // Dashboard-Selector
  const sel = document.getElementById("dd-dashboard-select");
  sel.innerHTML = `<option value="">— bitte wählen —</option>`;
  // Aus Konzepten + bisherigen Deep Dives befüllen
  const optsSet = new Set();
  Object.values(STATE.graph.concepts || {})
    .sort((a, b) => (b.video_count || 0) - (a.video_count || 0))
    .slice(0, 30)
    .forEach(c => {
      if (optsSet.has(c.label)) return;
      optsSet.add(c.label);
      const opt = document.createElement("option");
      opt.value = c.label;
      opt.textContent = `${c.label} (${c.category}, ${c.video_count}v)`;
      sel.appendChild(opt);
    });
  generated.forEach(g => {
    if (g.topic && !optsSet.has(g.topic)) {
      optsSet.add(g.topic);
      const opt = document.createElement("option");
      opt.value = g.topic;
      opt.textContent = `🔍 ${g.topic} (Deep Dive)`;
      sel.appendChild(opt);
    }
  });
}

// === Deep Dive: Sub-Tab-Switch ===
function bindDeepDiveTab() {
  document.querySelectorAll(".dd-subtab").forEach(t => {
    t.addEventListener("click", () => {
      document.querySelectorAll(".dd-subtab").forEach(x => x.classList.remove("active"));
      document.querySelectorAll(".dd-subview").forEach(x => x.classList.remove("active"));
      t.classList.add("active");
      document.getElementById("dd-subview-" + t.dataset.subview).classList.add("active");
    });
  });
  document.getElementById("dd-dashboard-select").addEventListener("change", async (e) => {
    const topic = e.target.value;
    if (!topic) {
      document.getElementById("dd-dashboard-content").innerHTML = "";
      return;
    }
    try {
      document.getElementById("dd-dashboard-content").innerHTML = `<div class="dd-empty">⏳ Lade Dashboard…</div>`;
      const r = await fetch(`/deep-dive/dashboard?topic=${encodeURIComponent(topic)}`);
      const data = await r.json();
      renderDashboard(data);
    } catch (err) {
      document.getElementById("dd-dashboard-content").innerHTML = `<div class="dd-empty"><div class="icon">⚠</div><h3>Fehler</h3><p>${err.message}</p></div>`;
    }
  });
}

// === Deep Dive: Dashboard-Visualisierung ===
function renderDashboard(data) {
  const root = document.getElementById("dd-dashboard-content");
  const s = data.stats || {};
  root.innerHTML = `
    <div class="dd-stat-row">
      <div class="dd-stat"><div class="num">${s.sections_count || 0}</div><div class="lbl">Sektionen</div></div>
      <div class="dd-stat"><div class="num">${s.videos_count || 0}</div><div class="lbl">Quell-Videos</div></div>
      <div class="dd-stat"><div class="num">${s.related_concepts || 0}</div><div class="lbl">Verwandt</div></div>
      <div class="dd-stat"><div class="num">${(data.timeline || []).length}</div><div class="lbl">Timeline-Punkte</div></div>
    </div>

    <div class="dd-dash-grid">
      <div class="dd-panel full">
        <h3>📅 Zeitverlauf</h3>
        <svg id="dd-timeline-svg"></svg>
      </div>

      <div class="dd-panel">
        <h3>📚 Sektionen im Buch (${(data.sections || []).length})</h3>
        <div id="dd-sections-list"></div>
      </div>

      <div class="dd-panel">
        <h3>🔗 Verwandte Konzepte</h3>
        <div class="dd-tools" id="dd-related"></div>

        <h3 style="margin-top: 20px">🛠 Tools</h3>
        <div class="dd-tools" id="dd-tools"></div>
      </div>
    </div>
  `;

  renderDashboardSections(data);
  renderDashboardTimeline(data);
  renderDashboardRelated(data);
}

function renderDashboardSections(data) {
  const root = document.getElementById("dd-sections-list");
  const sections = (data.sections || []).slice(0, 15);
  if (sections.length === 0) {
    root.innerHTML = `<p style="color: var(--text-muted)">Keine Erwaehnungen im Buch.</p>`;
    return;
  }
  root.innerHTML = "";
  sections.forEach(s => {
    const item = document.createElement("div");
    item.className = "dd-section-item";
    item.innerHTML = `
      <span class="sid">${escapeHtml(s.section_id)}</span>
      <span class="stitle">${escapeHtml(s.title)}</span>
      <span class="scount">${s.mentions_count}x</span>
    `;
    item.addEventListener("click", () => {
      document.querySelector('[data-view="book"]').click();
      loadSection(s.section_id);
    });
    root.appendChild(item);
  });
}

function renderDashboardTimeline(data) {
  const svg = d3.select("#dd-timeline-svg");
  svg.selectAll("*").remove();
  const tl = data.timeline || [];
  if (tl.length === 0) {
    svg.append("text").attr("x", 20).attr("y", 30).style("fill", "var(--text-muted)").text("Keine Timeline-Daten.");
    return;
  }
  const w = svg.node().clientWidth || 800;
  const h = 240;
  const m = { t: 20, r: 30, b: 40, l: 50 };

  const dates = tl.map(d => new Date(d.date));
  const x = d3.scaleTime().domain(d3.extent(dates)).range([m.l, w - m.r]);
  const maxMentions = d3.max(tl, d => d.mentions) || 1;
  const y = d3.scaleLinear().domain([0, maxMentions]).range([h - m.b, m.t]);
  const r = d3.scaleSqrt().domain([0, d3.max(tl, d => d.views) || 1]).range([4, 16]);

  svg.append("g").attr("class", "axis").attr("transform", `translate(0, ${h - m.b})`)
    .call(d3.axisBottom(x).ticks(8).tickFormat(d3.timeFormat("%d.%m")));
  svg.append("g").attr("class", "axis").attr("transform", `translate(${m.l}, 0)`)
    .call(d3.axisLeft(y).ticks(4));

  // Verbindungslinie
  svg.append("path")
    .datum(tl)
    .attr("fill", "none")
    .attr("stroke", "var(--cat-claude)")
    .attr("stroke-width", 1.5)
    .attr("stroke-opacity", 0.4)
    .attr("d", d3.line()
      .x(d => x(new Date(d.date)))
      .y(d => y(d.mentions))
    );

  svg.append("g").selectAll("circle").data(tl).enter().append("circle")
    .attr("cx", d => x(new Date(d.date)))
    .attr("cy", d => y(d.mentions))
    .attr("r", d => r(d.views))
    .attr("fill", "var(--cat-claude)")
    .attr("opacity", 0.7)
    .on("click", (e, d) => openVideoAt(d.video_id, d.first_mention_seconds || 0))
    .append("title").text(d => `${d.title}\n${d.date} · ${d.mentions} Erwaehnungen · ${formatViews(d.views)} Views`);
}

function renderDashboardRelated(data) {
  const rel = document.getElementById("dd-related");
  rel.innerHTML = "";
  (data.related_concepts || []).slice(0, 10).forEach(r => {
    const chip = document.createElement("span");
    chip.className = "dd-person-chip";
    chip.style.borderLeftColor = r.color || "var(--cat-claude)";
    chip.textContent = `${r.label} (${r.video_count}v)`;
    rel.appendChild(chip);
  });
  const tools = document.getElementById("dd-tools");
  tools.innerHTML = "";
  (data.tools || []).forEach(t => {
    const chip = document.createElement("span");
    chip.className = "dd-tool-chip";
    chip.textContent = `${t.label} (${t.video_count}v)`;
    tools.appendChild(chip);
  });
  if ((data.tools || []).length === 0) {
    tools.innerHTML = `<span style="color: var(--text-muted); font-size: 12px;">Keine Tool-Verbindungen.</span>`;
  }
}

// === Timeline ===
function renderTimeline() {
  const root = document.getElementById("timeline");
  root.innerHTML = "";
  const sorted = [...STATE.videos].sort((a, b) => a.published_date.localeCompare(b.published_date));
  const track = document.createElement("div");
  track.className = "timeline-track";
  sorted.forEach(v => {
    const meta = CATEGORY_META[v.category] || { color: "#888" };
    const col = document.createElement("div");
    col.className = "dot-row";
    col.innerHTML = `
      <div class="dot" style="--cat: ${meta.color}; background: ${meta.color};" title="${escapeHtml(v.title)}"></div>
      <div class="dot-date">${v.published_date.slice(5)}</div>
    `;
    col.querySelector(".dot").addEventListener("click", () => openVideoAt(v.id, 0));
    track.appendChild(col);
  });
  root.appendChild(track);
}

// === Reading Paths ===
function renderPaths() {
  const root = document.getElementById("paths-grid");
  root.innerHTML = "";
  const paths = STATE.book.reading_paths || [];
  paths.forEach(p => {
    let sectionsList = p.sections === "all" ? "Alle 39 Sektionen" :
      Array.isArray(p.sections) ? p.sections.join(", ") : "—";
    const totalMin = Array.isArray(p.sections) ?
      p.sections.length * 5 :
      Math.round(STATE.book.stats.total_words / 200);

    const card = document.createElement("div");
    card.className = "path-card";
    card.style.setProperty("--cat", "#8b5cf6");
    card.innerHTML = `
      <div class="path-icon">${p.id === 'schnell-einstieg' ? '⚡' : p.id === 'vollständig' ? '📖' : '🎯'}</div>
      <h3>${escapeHtml(p.title)}</h3>
      <p>${escapeHtml(p.description)}</p>
      <div class="pmeta">
        <span>${Array.isArray(p.sections) ? p.sections.length + ' Sektionen' : '39 Sektionen'}</span>
        <span>${totalMin} Min</span>
      </div>
      <div style="margin-top: 12px; font-size: 11px; color: var(--text-muted); font-family: 'JetBrains Mono', monospace;">${sectionsList.slice(0, 80)}</div>
    `;
    card.addEventListener("click", () => {
      // Start reading first section of path
      const firstSection = p.sections === "all" ? "1.1" : (p.sections[0] || "1.1");
      document.querySelector('[data-view="book"]').click();
      loadSection(firstSection);
    });
    root.appendChild(card);
  });
}

// === SYNC ===
async function syncRefreshState() {
  try {
    const r = await fetch("/sync/state");
    const data = await r.json();
    const meta = document.getElementById("sync-meta");
    if (data.last_sync_at) {
      const date = new Date(data.last_sync_at);
      const now = new Date();
      const diffH = Math.round((now - date) / 1000 / 3600);
      meta.textContent = diffH < 1 ? "gerade eben" : diffH < 24 ? `vor ${diffH}h` : `vor ${Math.round(diffH/24)}d`;
    } else {
      meta.textContent = "noch nie";
    }
  } catch (e) { console.warn("sync state failed", e); }
}

// === FULL UPDATE (Phase 15 — Sync + komplette Pipeline) ===
function renderUpdatePhases(phases) {
  const root = document.getElementById("update-phases");
  if (!root) return;
  root.innerHTML = phases.map(p => `
    <li class="update-phase" data-status="${p.status}" data-phase="${p.n}">
      <span class="update-phase-num">${String(p.n).padStart(2, "0")}</span>
      <span class="update-phase-name">${escapeHtml(p.name)}</span>
      <span class="update-phase-dur">${p.duration_s != null ? p.duration_s.toFixed(1) + "s" : ""}</span>
      <span class="update-phase-status"></span>
    </li>
  `).join("");
}

window.startUpdate = async function() {
  const btn = document.getElementById("update-button");
  const modal = document.getElementById("update-modal");
  const current = document.getElementById("update-current");
  const result = document.getElementById("update-result");
  btn.classList.add("syncing");
  modal.hidden = false;
  current.textContent = "Starte…";
  result.innerHTML = "";

  try {
    const r = await fetch("/update/trigger", { method: "POST" });
    const data = await r.json();
    const jobId = data.job_id;

    const poll = async () => {
      try {
        const sr = await fetch(`/update/status?job_id=${jobId}`);
        const status = await sr.json();
        renderUpdatePhases(status.phases || []);
        current.textContent = "▸ " + (status.current_message || "Läuft…");

        if (status.status === "done") {
          const newVids = status.new_videos || [];
          if (newVids.length === 0) {
            result.innerHTML = `
              <div class="update-success">✓ Update abgeschlossen — keine neuen Videos. Buch + Site neu gebaut.</div>
              <p style="margin-top:12px;font-size:12px;color:var(--text-secondary)">
                Total: ${status.total_duration_s ? status.total_duration_s.toFixed(1) + 's' : '—'}
              </p>
            `;
          } else {
            result.innerHTML = `
              <div class="update-success">✓ ${newVids.length} neue Video(s) + Pipeline durchgelaufen!</div>
              ${newVids.map(v => `<div class="sync-new-video">📹 <strong>${escapeHtml(v.title || "")}</strong></div>`).join("")}
              <p style="margin-top:12px;font-size:12px;color:var(--text-secondary)">
                Total: ${status.total_duration_s ? status.total_duration_s.toFixed(1) + 's' : '—'}.
                <br>Nächster Schritt: <strong>✨ Synthese</strong> klicken (oder im Chat: <code>Mache die offenen Deep Dives</code>).
              </p>
              <button class="btn-primary" style="margin-top:12px" onclick="location.reload()">⟳ Seite neu laden (neue Inhalte sehen)</button>
            `;
          }
          btn.classList.remove("syncing");
          syncRefreshState();
          loadDeepDiveData();
          return;
        } else if (status.status === "failed") {
          result.innerHTML = `<div class="update-failure">⚠ Update fehlgeschlagen: ${escapeHtml(status.current_message || "unbekannt")}</div>`;
          btn.classList.remove("syncing");
          return;
        }
        setTimeout(poll, 1500);
      } catch (e) {
        current.textContent = "Polling-Fehler: " + e.message;
        btn.classList.remove("syncing");
      }
    };
    setTimeout(poll, 700);
  } catch (e) {
    current.textContent = "⚠ Update konnte nicht gestartet werden: " + e.message;
    btn.classList.remove("syncing");
  }
};

// === SYNTHESIZE (Phase 2 — Backend folgt) ===
window.startSynthesize = async function() {
  const modal = document.getElementById("synthesize-modal");
  const list = document.getElementById("synthesize-list");
  const result = document.getElementById("synthesize-result");
  modal.hidden = false;
  list.innerHTML = `<div class="synth-empty">Lädt…</div>`;
  result.innerHTML = "";

  try {
    const r = await fetch("/synthesize/status");
    const data = await r.json();
    const t = data.totals || {};

    let html = "";
    if (t.topic_dds === 0 && t.video_dds === 0 && t.new_videos === 0) {
      html = `<div class="synth-empty">✓ Nichts offen — alle Themen und Videos synthetisiert.</div>`;
    } else {
      if (t.topic_dds > 0) {
        html += `<div class="synth-section"><h3>📚 Vorgemerkte Topic Deep Dives (${t.topic_dds})</h3>`;
        html += (data.pending_topic_dds || []).map(d => `
          <div class="synth-item">
            <span><strong>${escapeHtml(d.topic || "")}</strong> <code style="font-size:10px;color:var(--text-muted)">${escapeHtml(d.slug || "")}</code></span>
            <span class="synth-badge">${escapeHtml(d.priority || "mega")}</span>
          </div>
        `).join("");
        html += `</div>`;
      }
      if (t.video_dds > 0) {
        html += `<div class="synth-section"><h3>📹 Vorgemerkte Per-Video Deep Dives (${t.video_dds})</h3>`;
        html += (data.pending_video_dds || []).slice(0, 12).map(d => `
          <div class="synth-item">
            <span>${escapeHtml(d.title || d.video_id || "")}</span>
            <span class="synth-badge">video</span>
          </div>
        `).join("");
        if (data.pending_video_dds.length > 12) html += `<div class="synth-empty">+ ${data.pending_video_dds.length - 12} weitere…</div>`;
        html += `</div>`;
      }
      if (t.new_videos > 0) {
        html += `<div class="synth-section"><h3>🆕 Neue Videos ohne Sektions-Zuordnung (${t.new_videos})</h3>`;
        html += (data.new_videos_without_section || []).map(v => `
          <div class="synth-item">
            <span>${escapeHtml(v.title || v.id || "")}</span>
            <span class="synth-badge" style="background:var(--cat-business)">neu</span>
          </div>
        `).join("");
        html += `</div>`;
      }
    }
    list.innerHTML = html;

    result.innerHTML = `
      <div class="synth-note">
        <strong>Phase 2 — Backend-Synthese ist in Vorbereitung.</strong><br>
        Aktuell wird der Synthese-Job nicht hier im Hintergrund gestartet, sondern manuell im Chat.<br>
        <strong>So geht es heute:</strong><br>
        • Topic-DDs: <code>Mache die offenen Deep Dives</code><br>
        • Per-Video-DDs: <code>Mache die Per-Video-Deep-Dives</code><br>
        • Neue Videos: <code>Synthetisiere die neuen Sektionen aus den Briefings</code><br>
        <em style="display:block;margin-top:8px">Geplant: dieser Knopf spawnt direkt parallele Agents im Backend (siehe Skill-Backlog).</em>
      </div>
    `;
  } catch (e) {
    list.innerHTML = `<div class="synth-empty">⚠ Konnte Synthese-Status nicht laden: ${escapeHtml(e.message)}</div>`;
  }
};

// Update + Synthesize modal close
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-close-update]").forEach(el => {
    el.addEventListener("click", () => {
      document.getElementById("update-modal").hidden = true;
    });
  });
  document.querySelectorAll("[data-close-synth]").forEach(el => {
    el.addEventListener("click", () => {
      document.getElementById("synthesize-modal").hidden = true;
    });
  });
});

// Synth-Badge im Header refresh
async function refreshSynthBadge() {
  try {
    const r = await fetch("/synthesize/status");
    const data = await r.json();
    const t = data.totals || {};
    const total = (t.topic_dds || 0) + (t.video_dds || 0) + (t.new_videos || 0);
    const meta = document.getElementById("synth-meta");
    if (meta) meta.textContent = total > 0 ? `${total} offen` : "✓ leer";
  } catch (e) { /* silent */ }
}
refreshSynthBadge();
setInterval(refreshSynthBadge, 30000);

// === SCHEDULER (Automatik-Protokoll) ===
async function refreshSchedulerBadge() {
  try {
    const r = await fetch("/scheduler/log");
    const data = await r.json();
    const meta = document.getElementById("scheduler-meta");
    if (!meta) return;
    const state = data.state || {};
    if (state.last_daily) {
      const d = new Date(state.last_daily + "T00:00:00");
      const diff = Math.floor((Date.now() - d)/86400000);
      meta.textContent = diff === 0 ? "heute" : `vor ${diff}d`;
    } else {
      meta.textContent = "nie";
    }
  } catch (e) { /* silent */ }
}
refreshSchedulerBadge();
setInterval(refreshSchedulerBadge, 60000);

window.showSchedulerLog = async function() {
  const modal = document.getElementById("scheduler-modal");
  const stateDiv = document.getElementById("scheduler-state");
  const logDiv = document.getElementById("scheduler-log-list");
  modal.hidden = false;
  stateDiv.textContent = "Lade…";
  logDiv.innerHTML = "";
  try {
    const r = await fetch("/scheduler/log");
    const data = await r.json();
    const state = data.state || {};
    stateDiv.innerHTML = `Letzter Sync: <strong>${state.last_daily || "—"}</strong>  &nbsp;|&nbsp;  Letzte Wochensynthese: <strong>${state.last_weekly || "—"}</strong>`;
    const entries = data.log || [];
    if (entries.length === 0) {
      logDiv.innerHTML = '<p style="color:var(--muted);padding:12px">Noch keine automatischen Jobs gelaufen.</p>';
      return;
    }
    logDiv.innerHTML = entries.map(e => {
      const ts = new Date(e.timestamp).toLocaleString("de-DE");
      const icon = e.ok ? "✅" : "⚠️";
      const typeLabel = e.type === "daily_sync" ? "Täglicher Sync" : "Wöchentliche Buch-Erneuerung";
      const extra = e.type === "daily_sync"
        ? `${e.new_videos || 0} neue Videos`
        : Object.entries(e.steps || {}).map(([k,v]) => `${k}: ${v ? "✓" : "✗"}`).join(" · ");
      return `<div style="padding:8px 0;border-bottom:1px solid var(--border);font-size:0.85em">
        <span style="color:var(--muted)">${ts}</span>  ${icon} <strong>${typeLabel}</strong><br>
        <span style="color:var(--muted);margin-left:20px">${extra} · ${Math.round((e.elapsed_seconds||0)/60)}min</span>
      </div>`;
    }).join("");
  } catch (e) {
    stateDiv.textContent = "Scheduler nicht erreichbar (Container noch nicht gestartet?)";
  }
};

// === PER-VIDEO DEEP DIVE ===
async function loadPerVideoData() {
  try {
    const r = await fetch("/per-video/list");
    const data = await r.json();
    STATE.perVideo = data;
    renderPerVideo();
  } catch (e) {
    console.error("per-video load failed:", e);
  }
}

function renderPerVideo() {
  if (!STATE.perVideo) return;
  const pending = STATE.perVideo.pending || [];
  const generated = STATE.perVideo.generated || [];
  document.getElementById("pv-count-pend").textContent = pending.length;
  document.getElementById("pv-count-gen").textContent = generated.length;
  const ddCountPv = document.getElementById("dd-count-per-video");
  if (ddCountPv) ddCountPv.textContent = pending.length + generated.length;

  // Generated grid
  const gen = document.getElementById("pv-generated-list");
  if (generated.length === 0) {
    gen.innerHTML = `<div class="dd-empty" style="grid-column:1/-1"><div class="icon">📹</div><h3>Noch keine Per-Video-Deep-Dives</h3><p>Klick in der Quellen-Bibliothek auf ein Video → "Tiefenanalyse anfordern"</p></div>`;
  } else {
    gen.innerHTML = "";
    generated.forEach(g => {
      const v = STATE.videos.find(x => x.id === g.video_id);
      const meta = CATEGORY_META[v?.category] || { color: "#6b7280" };
      const thumb = `https://img.youtube.com/vi/${g.video_id}/hqdefault.jpg`;
      const dur = g.duration_min ? `${Math.round(g.duration_min)} min` : "";
      const card = document.createElement("div");
      card.className = "dd-card pv-card";
      card.innerHTML = `
        <div class="pv-card-thumb" style="background-image:url('${thumb}')"></div>
        <div class="pv-card-body">
          <div class="pv-cat-pill" style="background:${meta.color}22;color:${meta.color}">${meta.label || v?.category || "Video"}</div>
          <h3>${escapeHtml(g.title || g.video_id)}</h3>
          <div class="pv-card-meta">
            ${g.published ? `<span>📅 ${g.published}</span>` : ""}
            ${dur ? `<span>⏱ ${dur}</span>` : ""}
            ${g.word_count ? `<span>📝 ${g.word_count} Wörter</span>` : ""}
          </div>
        </div>
      `;
      card.addEventListener("click", () => openPerVideoDeepDive(g.video_id));
      gen.appendChild(card);
    });
  }

  // Pending
  const pend = document.getElementById("pv-pending-list");
  if (pending.length === 0) {
    pend.innerHTML = `<div class="dd-empty"><div class="icon">⏳</div><h3>Keine vorgemerkten Per-Video-Deep-Dives</h3></div>`;
  } else {
    pend.innerHTML = pending.map(p => `
      <div class="dd-pending-item">
        <div class="topic">
          <strong>${escapeHtml(p.title || p.video_id)}</strong>
          <span class="when">Vorgemerkt: ${formatDate(p.bookmarked_at?.slice(0,10) || "")}</span>
        </div>
        <span class="type-pill">${escapeHtml(p.category || "—")}</span>
      </div>
    `).join("");
  }
}

window.openPerVideoDeepDive = async function(videoId) {
  const modal = document.getElementById("modal");
  const body = document.getElementById("modal-body");

  // Lade-Zustand
  body.innerHTML = `<div style="text-align:center;padding:40px 0">
    <div style="font-size:2em;margin-bottom:12px">📹</div>
    <p style="color:var(--text-secondary)">Lade Deep Dive…</p>
  </div>`;
  modal.hidden = false;

  try {
    const resp = await fetch(`/per-video/content?id=${encodeURIComponent(videoId)}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    const md = data.markdown || "";

    // Frontmatter entfernen
    const stripped = md.replace(/^---[\s\S]*?---\n*/m, "");

    // Markdown → HTML
    const html = typeof marked !== "undefined"
      ? marked.parse(stripped)
      : `<pre>${escapeHtml(stripped)}</pre>`;

    // Timestamps zu klickbaren Links
    const linked = html.replace(
      /\(video:([^?]+)\?t=(\d+)\)/g,
      (_, vid, sec) => `(<a href="https://www.youtube.com/watch?v=${vid}&t=${sec}" target="_blank" rel="noopener">▶ ${Math.floor(parseInt(sec)/60)}:${String(parseInt(sec)%60).padStart(2,'0')}</a>)`
    );

    body.innerHTML = `<div class="pv-deep-dive-article book-section-content">${linked}</div>`;
  } catch (err) {
    body.innerHTML = `<p style="color:var(--error)">Fehler: ${escapeHtml(err.message)}</p>
      <p style="color:var(--text-secondary);margin-top:8px">Deep Dive noch nicht synthetisiert — bitte im Chat ausführen: "Mache die Per-Video Deep Dives"</p>`;
  }
};

window.bookmarkPerVideoDeepDive = async function(videoId, title, category) {
  try {
    const r = await fetch("/per-video/bookmark", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ video_id: videoId, title, category }),
    });
    const data = await r.json();
    if (data.status === "ok") {
      alert(`✅ Per-Video-Deep-Dive für "${title}" vorgemerkt.\n\nIm Chat:\n"Mache die Per-Video-Deep-Dives"`);
      loadPerVideoData();
    } else if (data.status === "duplicate") {
      alert(`ℹ "${title}" ist bereits vorgemerkt.`);
    } else {
      alert(`⚠ Fehler: ${data.error || "unbekannt"}`);
    }
  } catch (e) {
    alert(`⚠ Server nicht erreichbar: ${e.message}`);
  }
};

// PV sub-tab switcher
function bindPerVideoTabs() {
  document.querySelectorAll('#pv-tabs .dd-subtab').forEach(t => {
    t.addEventListener("click", () => {
      document.querySelectorAll('#pv-tabs .dd-subtab').forEach(x => x.classList.remove("active"));
      t.classList.add("active");
      const which = t.dataset.pv;
      document.getElementById("pv-generated-list").style.display = which === "generated" ? "" : "none";
      document.getElementById("pv-pending-list").style.display = which === "pending" ? "block" : "none";
    });
  });
}

// === Use-Case-Suche ===
function bindUsecaseSearch() {
  const input = document.getElementById("usecase-input");
  const btn   = document.getElementById("usecase-btn");
  const resultsDiv = document.getElementById("usecase-results");

  async function runSearch() {
    const q = (input.value || "").trim();
    if (!q) return;
    btn.textContent = "Suche…";
    btn.disabled = true;
    resultsDiv.hidden = false;
    resultsDiv.innerHTML = '<p class="hint">KI analysiert Anfrage…</p>';

    try {
      const resp = await fetch("/search/usecase", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({query: q}),
      });
      const data = await resp.json();
      renderUsecaseResults(q, data);
    } catch (e) {
      resultsDiv.innerHTML = `<p class="hint">Fehler: ${escapeHtml(e.message)}</p>`;
    } finally {
      btn.textContent = "Anwenden";
      btn.disabled = false;
    }
  }

  btn.addEventListener("click", runSearch);
  input.addEventListener("keydown", e => { if (e.key === "Enter") runSearch(); });

  document.querySelectorAll(".usecase-ex").forEach(b => {
    b.addEventListener("click", () => {
      input.value = b.dataset.q;
      runSearch();
    });
  });
}

function renderUsecaseResults(query, data) {
  const resultsDiv = document.getElementById("usecase-results");
  // Bevorzuge semantische Ergebnisse, Fallback auf keyword
  const semantic = data.semantic;
  const keyword  = data.keyword || {};

  const praxisItems   = semantic ? semantic.praxis   : keyword.praxis   || [];
  const sections      = semantic ? semantic.sections : keyword.sections || [];
  const dds           = semantic ? semantic.dds      : keyword.dds      || [];
  const erklaerung    = semantic ? semantic.erklaerung : "";

  const hasResults = praxisItems.length + sections.length + dds.length > 0;

  if (!hasResults) {
    resultsDiv.innerHTML = `<div class="usecase-no-results">
      <strong>Keine Treffer</strong> für „${escapeHtml(query)}" — versuche andere Begriffe.
    </div>`;
    return;
  }

  const badge = semantic ? '<span class="usecase-ai-badge">🤖 KI-Suche</span>' : '<span class="usecase-ai-badge kw">🔤 Keyword</span>';

  let html = `<div class="usecase-result-header">
    <strong>Treffer für „${escapeHtml(query)}"</strong> ${badge}
    ${erklaerung ? `<p class="usecase-erklaerung">${escapeHtml(erklaerung)}</p>` : ""}
  </div>`;

  if (praxisItems.length) {
    html += `<div class="usecase-group">
      <div class="usecase-group-title">🛠 Sofort umsetzbar</div>
      <div class="usecase-cards">
        ${praxisItems.map(it => {
          const cat = it.category || "technik";
          const color = (PRAXIS_CAT_COLORS||{})[cat] || "#888";
          return `<div class="usecase-card" style="--cat-color:${color}">
            <span class="praxis-cat-pill">${(PRAXIS_CAT_LABELS||{})[cat]||cat}</span>
            <p class="praxis-card-text">${escapeHtml(it.text||"")}</p>
            ${it.kontext ? `<p class="praxis-card-kontext">${escapeHtml(it.kontext)}</p>` : ""}
            <button class="praxis-video-btn" onclick="openVideoAt('${escapeHtml(it.video_id||"")}',0)">
              ▶ ${escapeHtml((it.video_title||"").slice(0,50))}${(it.video_title||"").length>50?"…":""}
            </button>
          </div>`;
        }).join("")}
      </div>
    </div>`;
  }

  if (sections.length) {
    html += `<div class="usecase-group">
      <div class="usecase-group-title">📖 Im Wissensbuch</div>
      <div class="usecase-cards">
        ${sections.map(s => `<div class="usecase-card section-card" onclick="loadSection('${escapeHtml(s.id||"")}')">
          <span class="usecase-section-id">${escapeHtml(s.id||"")}</span>
          <p class="praxis-card-text">${escapeHtml(s.title||"")}</p>
          ${s.body_preview ? `<p class="praxis-card-kontext">${escapeHtml(s.body_preview.slice(0,150))}…</p>` : ""}
          <span class="usecase-link">Jetzt lesen →</span>
        </div>`).join("")}
      </div>
    </div>`;
  }

  if (dds.length) {
    html += `<div class="usecase-group">
      <div class="usecase-group-title">🔍 Deep Dives</div>
      <div class="usecase-cards">
        ${dds.map(d => `<div class="usecase-card dd-card" onclick="loadSection('${escapeHtml(d.section_id||"")}')">
          <span class="usecase-section-id">Deep Dive</span>
          <p class="praxis-card-text">${escapeHtml(d.topic||"")}</p>
          <span class="usecase-link">Tiefenanalyse lesen →</span>
        </div>`).join("")}
      </div>
    </div>`;
  }

  resultsDiv.innerHTML = html;
}

// === Praxis-View (Layer 3) ===
const PRAXIS_STATE = {
  items: [],
  activeCat: "",
  activeTopic: "",
  loaded: false,
};

const PRAXIS_CAT_LABELS = {
  tool:      "🔧 Tool",
  technik:   "⚙️ Technik",
  workflow:  "🔄 Workflow",
  framework: "🏗️ Framework",
  mindset:   "💡 Mindset",
};
const PRAXIS_CAT_COLORS = {
  tool:      "#4f8ef7",
  technik:   "#22c55e",
  workflow:  "#f59e0b",
  framework: "#a855f7",
  mindset:   "#ec4899",
};

async function initPraxisView() {
  if (PRAXIS_STATE.loaded) {
    renderPraxisGrid();
    return;
  }
  const grid = document.getElementById("praxis-grid");
  grid.innerHTML = '<p class="hint">Lade Praxis-Daten…</p>';
  try {
    const resp = await fetch("/praxis/index");
    if (!resp.ok) throw new Error(resp.status);
    const data = await resp.json();
    PRAXIS_STATE.items = data.all_items || [];
    PRAXIS_STATE.loaded = true;

    // Counts in Filter-Buttons aktualisieren
    document.getElementById("praxis-count-all").textContent = PRAXIS_STATE.items.length;
    ["tool","technik","workflow","framework","mindset"].forEach(cat => {
      const cnt = PRAXIS_STATE.items.filter(i => i.category === cat).length;
      const el = document.getElementById("praxis-count-" + cat);
      if (el) el.textContent = cnt;
    });

    // Badge in Tab-Leiste
    const badge = document.getElementById("praxis-badge");
    if (PRAXIS_STATE.items.length > 0) {
      badge.textContent = PRAXIS_STATE.items.length;
      badge.hidden = false;
    }

    // Topic-Filter befüllen
    const topics = [...new Set(PRAXIS_STATE.items.map(i => i.video_category).filter(Boolean))].sort();
    const sel = document.getElementById("praxis-topic-select");
    topics.forEach(t => {
      const opt = document.createElement("option");
      opt.value = t;
      opt.textContent = t;
      sel.appendChild(opt);
    });
    sel.addEventListener("change", () => {
      PRAXIS_STATE.activeTopic = sel.value;
      renderPraxisGrid();
    });

    renderPraxisGrid();
  } catch (e) {
    grid.innerHTML = `<p class="hint">Fehler beim Laden: ${e.message}. <br>Führe zuerst <code>python scripts/18_extract_praxis.py</code> aus.</p>`;
  }
}

function renderPraxisGrid() {
  let items = PRAXIS_STATE.items;
  if (PRAXIS_STATE.activeCat) items = items.filter(i => i.category === PRAXIS_STATE.activeCat);
  if (PRAXIS_STATE.activeTopic) items = items.filter(i => i.video_category === PRAXIS_STATE.activeTopic);

  const grid = document.getElementById("praxis-grid");
  const empty = document.getElementById("praxis-empty");

  if (items.length === 0) {
    grid.innerHTML = "";
    empty.hidden = false;
    return;
  }
  empty.hidden = true;
  grid.innerHTML = items.map(item => {
    const cat = item.category || "technik";
    const color = PRAXIS_CAT_COLORS[cat] || "#888";
    const label = PRAXIS_CAT_LABELS[cat] || cat;
    const kontext = item.kontext ? `<p class="praxis-card-kontext">${escapeHtml(item.kontext)}</p>` : "";
    return `<div class="praxis-card" style="--cat-color:${color}">
      <span class="praxis-cat-pill">${label}</span>
      <p class="praxis-card-text">${escapeHtml(item.text)}</p>
      ${kontext}
      <button class="praxis-video-btn" onclick="openVideoAt('${escapeHtml(item.video_id)}',0)"
        title="${escapeHtml(item.video_title)}">
        ▶ ${escapeHtml((item.video_title||"").slice(0,50))}${(item.video_title||"").length>50?"…":""}
      </button>
    </div>`;
  }).join("");
}

function bindPraxisCatFilter() {
  document.querySelectorAll(".praxis-cat-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".praxis-cat-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      PRAXIS_STATE.activeCat = btn.dataset.cat;
      renderPraxisGrid();
    });
  });
}

// === Utils ===
function escapeHtml(s) {
  if (!s) return "";
  return String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}
function formatDate(iso) {
  if (!iso) return "";
  const [y, m, d] = iso.split("-");
  return `${d}.${m}.${y}`;
}
function formatTime(seconds) {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}
function formatViews(n) {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return Math.round(n / 1000) + "k";
  return n;
}
