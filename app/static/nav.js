"use strict";

/* ------------------------------------------------------------------ *
 * Shared helpers + auth-aware navigation, loaded on every page.
 * ------------------------------------------------------------------ */

window.API = {
  get(url) {
    return fetch(url, { headers: { Accept: "application/json" } });
  },
  send(url, method, body) {
    return fetch(url, {
      method,
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
  },
};

window.escapeHtml = function (value) {
  const div = document.createElement("div");
  div.textContent = value == null ? "" : String(value);
  return div.innerHTML;
};

window.toast = function (message, kind) {
  let host = document.querySelector(".toast-host");
  if (!host) {
    host = document.createElement("div");
    host.className = "toast-host";
    document.body.appendChild(host);
  }
  const el = document.createElement("div");
  el.className = "toast" + (kind ? ` toast--${kind}` : "");
  el.textContent = message;
  host.appendChild(el);
  setTimeout(() => {
    el.style.transition = "opacity .3s ease, transform .3s ease";
    el.style.opacity = "0";
    el.style.transform = "translateY(8px)";
    setTimeout(() => el.remove(), 320);
  }, 2600);
};

function initial(name) {
  return (name || "?").trim().charAt(0).toUpperCase() || "?";
}

function wireDropdown(el) {
  const btn = el.querySelector("button");
  if (!btn) return;
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    const open = el.classList.toggle("open");
    btn.setAttribute("aria-expanded", String(open));
  });
}

async function renderAuth() {
  const slot = document.getElementById("auth-slot");
  if (!slot) return;
  let user = null;
  try {
    const res = await window.API.get("/api/auth/me");
    user = (await res.json()).user;
  } catch (_) {
    /* offline / network error — treat as logged out */
  }
  window.currentUser = user;
  document.dispatchEvent(new CustomEvent("auth:ready", { detail: { user } }));

  slot.innerHTML = "";
  if (user) {
    const menu = document.createElement("div");
    menu.className = "dropdown";
    menu.innerHTML = `
      <button class="user-chip" type="button" aria-haspopup="true" aria-expanded="false">
        <span class="avatar">${initial(user.name)}</span>
        <span class="user-chip__name">${window.escapeHtml(user.name)}</span>
      </button>
      <div class="dropdown__menu" role="menu">
        <a href="/library"><span class="emoji">📚</span> My playlists</a>
        <a href="#" data-logout><span class="emoji">⏻</span> Log out</a>
      </div>`;
    slot.appendChild(menu);
    wireDropdown(menu);
    menu.querySelector("[data-logout]").addEventListener("click", async (e) => {
      e.preventDefault();
      await window.API.send("/api/auth/logout", "POST");
      window.toast("Logged out", "ok");
      setTimeout(() => (window.location.href = "/"), 450);
    });
  } else {
    const login = document.createElement("a");
    login.className = "nav__link";
    login.href = "/login";
    login.textContent = "Log in";
    const signup = document.createElement("a");
    signup.className = "btn btn--white btn--sm";
    signup.href = "/signup";
    signup.textContent = "Sign up";
    slot.append(login, signup);
  }
}
window.renderAuth = renderAuth;

document.addEventListener("click", () =>
  document.querySelectorAll(".dropdown.open").forEach((d) => d.classList.remove("open"))
);
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape")
    document.querySelectorAll(".dropdown.open").forEach((d) => d.classList.remove("open"));
});

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".dropdown[data-static]").forEach(wireDropdown);
  renderAuth();
});
