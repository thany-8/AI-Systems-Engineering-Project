"use strict";

/* ------------------------------------------------------------------ *
 * Landing page: turn a prompt into a ranked, explained playlist and
 * (optionally) save it to the signed-in user's library.
 * ------------------------------------------------------------------ */

const form = document.getElementById("composer");
const promptEl = document.getElementById("prompt");
const createBtn = document.getElementById("create");

// The playlist renders into #result. If the markup is ever missing it (e.g.
// the section was removed from index.html), create it so generation still
// works instead of throwing "Cannot set properties of null".
const resultEl = ensureResultContainer();

function ensureResultContainer() {
  let el = document.getElementById("result");
  if (el) return el;
  el = document.createElement("section");
  el.id = "result";
  el.className = "result";
  el.hidden = true;
  el.setAttribute("aria-live", "polite");
  const generator = document.querySelector(".generator");
  if (generator && generator.parentNode) {
    generator.parentNode.insertBefore(el, generator.nextSibling);
  } else {
    (document.querySelector("main") || document.body).appendChild(el);
  }
  return el;
}

const VIBE_ART = { calm: "🌙", upbeat: "☀️", intense: "🔥", melancholy: "🌧️" };
let lastResult = null;

/* --- input ergonomics ------------------------------------------------ */
function autogrow() {
  promptEl.style.height = "auto";
  promptEl.style.height = Math.min(promptEl.scrollHeight, 200) + "px";
}
promptEl.addEventListener("input", autogrow);
promptEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    form.requestSubmit();
  }
});

document.querySelectorAll(".chip").forEach((chip) =>
  chip.addEventListener("click", () => {
    promptEl.value = chip.textContent.trim();
    autogrow();
    promptEl.focus();
  })
);

// Prefill from a ?q= link (used by the Quick actions menu).
const preset = new URLSearchParams(location.search).get("q");
if (preset) {
  promptEl.value = preset;
  autogrow();
}

/* --- generate -------------------------------------------------------- */
form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const query = promptEl.value.trim();
  if (!query) {
    promptEl.focus();
    return;
  }
  setLoading(true);
  showSkeleton();
  try {
    const res = await window.API.send("/api/recommend", "POST", { query });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Could not create a playlist.");
    lastResult = { query, ...data };
    renderPlaylist(lastResult);
  } catch (err) {
    resultEl.hidden = true;
    window.toast(err.message || "Something went wrong.", "err");
  } finally {
    setLoading(false);
  }
});

function setLoading(on) {
  createBtn.disabled = on;
  createBtn.innerHTML = on
    ? '<span class="spinner"></span> Creating…'
    : "Create Playlist";
}

function showSkeleton() {
  resultEl.hidden = false;
  resultEl.innerHTML = `
    <div class="playlist-card">
      <div class="loading">
        <div class="skeleton sk-row"></div>
        <div class="skeleton sk-row"></div>
        <div class="skeleton sk-row"></div>
        <div class="skeleton sk-row"></div>
      </div>
    </div>`;
  resultEl.scrollIntoView({ behavior: "smooth", block: "start" });
}

/* --- render ---------------------------------------------------------- */
function titleFor(query) {
  const t = query.trim().replace(/\s+/g, " ");
  return t.charAt(0).toUpperCase() + t.slice(1);
}

function renderPlaylist(data) {
  const songs = data.results || [];
  const vibe = data.desired_vibe || (songs[0] && songs[0].vibe) || "";
  const cover = VIBE_ART[vibe] || "🎵";
  const title = titleFor(data.query);

  const card = document.createElement("div");
  card.className = "playlist-card";
  card.innerHTML = `
    <div class="pc__head">
      <div class="pc__cover" aria-hidden="true">${cover}</div>
      <div class="pc__titles">
        <h2 class="pc__title">${window.escapeHtml(title)}</h2>
        <p class="pc__meta">${songs.length} track${songs.length === 1 ? "" : "s"} · matched to your request</p>
        <div class="pc__badges">
          ${vibe ? `<span class="tag tag--vibe">${window.escapeHtml(vibe)} vibe</span>` : ""}
          <span class="tag tag--mode">${data.mode === "gemini" ? "Gemini reasoning" : "Offline engine"}</span>
        </div>
      </div>
    </div>
    ${data.answer ? `<p class="pc__note">${window.escapeHtml(data.answer)}</p>` : ""}
    <ol class="tracks"></ol>
    <div class="pc__actions"></div>`;

  const list = card.querySelector(".tracks");
  songs.forEach((song, i) => list.appendChild(renderTrack(song, i)));

  card.querySelector(".pc__actions").append(...actionButtons(data));

  resultEl.hidden = false;
  resultEl.innerHTML = "";
  resultEl.appendChild(card);
  resultEl.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderTrack(song, index) {
  const pct = Math.round((song.final_score || 0) * 100);
  const art = VIBE_ART[song.vibe] || "🎵";
  const li = document.createElement("li");
  li.className = "track";
  li.innerHTML = `
    <span class="track__idx">${index + 1}</span>
    <span class="track__art" aria-hidden="true">${art}</span>
    <div class="track__main">
      <div class="track__title">${window.escapeHtml(song.title || "Untitled")}</div>
      <div class="track__artist">${window.escapeHtml(song.artist || "Unknown artist")}</div>
      <div class="track__tags">
        ${song.genre ? `<span class="tag">${window.escapeHtml(song.genre)}</span>` : ""}
        ${song.mood ? `<span class="tag">${window.escapeHtml(song.mood)}</span>` : ""}
      </div>
    </div>
    <div class="track__match">
      <div class="match__pct">${pct}%</div>
      <div class="match__bar"><div class="match__fill" style="width:${pct}%"></div></div>
    </div>`;
  return li;
}

function actionButtons(data) {
  const nodes = [];
  const saveWrap = document.createElement("div");
  saveWrap.id = "save-wrap";
  renderSaveControl(saveWrap, data);
  nodes.push(saveWrap);

  const spacer = document.createElement("span");
  spacer.className = "spacer";
  nodes.push(spacer);

  const copyBtn = document.createElement("button");
  copyBtn.className = "btn btn--ghost btn--sm";
  copyBtn.type = "button";
  copyBtn.textContent = "Copy";
  copyBtn.addEventListener("click", () => copyPlaylist(data));
  nodes.push(copyBtn);

  const newBtn = document.createElement("button");
  newBtn.className = "btn btn--ghost btn--sm";
  newBtn.type = "button";
  newBtn.textContent = "New playlist";
  newBtn.addEventListener("click", () => {
    resultEl.hidden = true;
    resultEl.innerHTML = "";
    promptEl.value = "";
    autogrow();
    promptEl.focus();
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
  nodes.push(newBtn);
  return nodes;
}

function renderSaveControl(wrap, data) {
  wrap.innerHTML = "";
  if (window.currentUser) {
    const save = document.createElement("button");
    save.className = "btn btn--primary btn--sm";
    save.type = "button";
    save.textContent = "＋ Save playlist";
    save.addEventListener("click", () => savePlaylist(save, data));
    wrap.appendChild(save);
  } else {
    const login = document.createElement("a");
    login.className = "btn btn--ghost btn--sm";
    login.href = "/login";
    login.textContent = "Log in to save";
    wrap.appendChild(login);
  }
}

// If auth resolves after a playlist is already on screen, refresh the control.
document.addEventListener("auth:ready", () => {
  const wrap = document.getElementById("save-wrap");
  if (wrap && lastResult) renderSaveControl(wrap, lastResult);
});

/* --- save + copy ----------------------------------------------------- */
async function savePlaylist(btn, data) {
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Saving…';
  try {
    const res = await window.API.send("/api/playlists", "POST", {
      title: titleFor(data.query),
      prompt: data.query,
      vibe: data.desired_vibe || null,
      note: data.answer || null,
      songs: data.results || [],
    });
    const body = await res.json();
    if (!res.ok) throw new Error(body.error || "Could not save playlist.");
    window.toast("Saved to your library ✓", "ok");
    const link = document.createElement("a");
    link.className = "btn btn--ghost btn--sm";
    link.href = "/library";
    link.textContent = "Saved ✓ · View library";
    btn.replaceWith(link);
  } catch (err) {
    btn.disabled = false;
    btn.textContent = "＋ Save playlist";
    window.toast(err.message, "err");
  }
}

function copyPlaylist(data) {
  const lines = (data.results || []).map(
    (s, i) => `${i + 1}. ${s.title} — ${s.artist}`
  );
  const text = `${titleFor(data.query)}\n${lines.join("\n")}`;
  navigator.clipboard
    .writeText(text)
    .then(() => window.toast("Playlist copied to clipboard", "ok"))
    .catch(() => window.toast("Couldn't copy playlist", "err"));
}
