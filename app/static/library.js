"use strict";

/* ------------------------------------------------------------------ *
 * Library page: list, preview, and delete the signed-in user's saved
 * playlists. Redirects to the login page when the session is missing.
 * ------------------------------------------------------------------ */

const container = document.getElementById("library");
const esc = window.escapeHtml;
const VIBE_ART = { calm: "🌙", upbeat: "☀️", intense: "🔥", melancholy: "🌧️" };

function fmtDate(iso) {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch (_) {
    return "";
  }
}

async function load() {
  let res;
  try {
    res = await window.API.get("/api/playlists");
  } catch (_) {
    container.className = "";
    container.innerHTML = stateBox("😕", "Couldn't reach the server", "Please try again in a moment.");
    return;
  }
  if (res.status === 401) {
    window.location.href = "/login?next=/library";
    return;
  }
  const data = await res.json();
  render(data.playlists || []);
}

function render(playlists) {
  if (!playlists.length) {
    container.className = "";
    container.innerHTML = emptyState();
    return;
  }
  container.className = "library-grid";
  container.innerHTML = "";
  playlists.forEach((p) => container.appendChild(card(p)));
}

function card(playlist) {
  const cover = VIBE_ART[playlist.vibe] || "🎵";
  const songs = playlist.songs || [];
  const shown = songs.slice(0, 4);
  const el = document.createElement("article");
  el.className = "saved";
  el.innerHTML = `
    <div class="saved__head">
      <div class="track__art" style="width:44px;height:44px;font-size:20px">${cover}</div>
      <div style="min-width:0">
        <div class="track__title" title="${esc(playlist.title)}">${esc(playlist.title)}</div>
        <div class="track__artist">${songs.length} track${songs.length === 1 ? "" : "s"}${
          playlist.vibe ? " · " + esc(playlist.vibe) + " vibe" : ""
        }</div>
      </div>
    </div>
    <div class="saved__body">
      <ol class="tracks" style="padding:0">
        ${shown
          .map(
            (s, i) => `
          <li class="track">
            <span class="track__idx">${i + 1}</span>
            <span class="track__art" aria-hidden="true">${VIBE_ART[s.vibe] || "🎵"}</span>
            <div class="track__main">
              <div class="track__title">${esc(s.title)}</div>
              <div class="track__artist">${esc(s.artist)}</div>
            </div>
          </li>`
          )
          .join("")}
      </ol>
      ${songs.length > shown.length ? `<div class="mini-more">+ ${songs.length - shown.length} more</div>` : ""}
    </div>
    <div class="saved__foot">
      <span>Saved ${fmtDate(playlist.created_at)}</span>
      <button class="btn btn--ghost btn--sm" type="button" data-del>Delete</button>
    </div>`;
  el.querySelector("[data-del]").addEventListener("click", () => remove(playlist, el));
  return el;
}

async function remove(playlist, el) {
  if (!window.confirm(`Delete “${playlist.title}”?`)) return;
  try {
    const res = await window.API.send(`/api/playlists/${playlist.id}`, "DELETE");
    if (!res.ok) throw new Error();
    el.remove();
    window.toast("Playlist deleted", "ok");
    if (!container.querySelector(".saved")) render([]);
  } catch (_) {
    window.toast("Couldn't delete playlist", "err");
  }
}

function stateBox(icon, title, body) {
  return `<div class="empty"><div class="empty__ico">${icon}</div><h2>${esc(title)}</h2><p>${esc(body)}</p></div>`;
}

function emptyState() {
  return `
    <div class="empty">
      <div class="empty__ico">🎧</div>
      <h2>No playlists yet</h2>
      <p>Generate your first playlist and hit <strong>Save</strong> to build your library.</p>
      <p style="margin-top:16px"><a class="btn btn--primary" href="/">Create a playlist</a></p>
    </div>`;
}

load();
