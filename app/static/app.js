"use strict";

const messagesEl = document.getElementById("messages");
const form = document.getElementById("composer");
const input = document.getElementById("message");
const sendBtn = document.getElementById("send");
const badge = document.getElementById("mode-badge");

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

function multiline(parent, text) {
  const lines = String(text).split("\n");
  lines.forEach((line, i) => {
    parent.appendChild(document.createTextNode(line));
    if (i < lines.length - 1) parent.appendChild(document.createElement("br"));
  });
}

function scrollToBottom() {
  const chat = document.querySelector(".chat");
  chat.scrollTop = chat.scrollHeight;
}

function addMessage(role, text) {
  const li = el("li", `msg msg--${role}`);
  const bubble = el("div", "bubble");
  if (text != null) multiline(bubble, text);
  li.appendChild(bubble);
  messagesEl.appendChild(li);
  scrollToBottom();
  return li;
}

function addThinking() {
  const li = addMessage("assistant", null);
  const dots = el("span", "dots");
  dots.setAttribute("aria-label", "Thinking");
  dots.append(el("span"), el("span"), el("span"));
  li.querySelector(".bubble").appendChild(dots);
  return li;
}

/** Render the retrieved-and-ranked songs as compact cards. */
function renderResults(results) {
  const wrap = el("div", "songs");
  wrap.appendChild(el("div", "songs__title", "Retrieved & ranked"));
  results.forEach((s) => {
    const card = el("div", "song");
    const main = el("div", "song__main");
    main.appendChild(el("span", "song__title", s.title));
    main.appendChild(el("span", "song__artist", ` — ${s.artist}`));
    card.appendChild(main);

    const tags = el("div", "song__tags");
    tags.appendChild(el("span", `vibe vibe--${s.vibe}`, s.vibe));
    tags.appendChild(el("span", "song__meta", `${s.mood} · ${s.genre}`));
    tags.appendChild(el("span", "song__meta", `match ${Number(s.final_score).toFixed(2)}`));
    card.appendChild(tags);
    wrap.appendChild(card);
  });
  return wrap;
}

/** Build the collapsible RAG-trace panel. */
function renderTrace(trace, meta) {
  const details = el("details", "trace");
  details.appendChild(el("summary", null, "How this was built (RAG steps)"));
  const list = el("ol", "trace__list");

  trace.forEach((step) => {
    let line = "";
    let cls = "trace__step";
    if (step.step === "retrieve") {
      const titles = (step.hits || []).map((h) => h.title).join(", ");
      line = `🔎 retrieve (top ${step.k}) → ${titles || "no matches"}`;
    } else if (step.step === "rank") {
      line = `🎚️ re-rank → desired vibe: ${step.desired_vibe} (${step.source})`;
    } else if (step.step === "guardrail") {
      line = step.grounded
        ? "🛡️ grounding → passed"
        : `🛡️ grounding → replaced ungrounded: ${(step.offending || []).join(", ")}`;
      if (!step.grounded) cls += " trace__step--revise";
    }
    list.appendChild(el("li", cls, line));
  });

  details.appendChild(list);
  if (meta) details.appendChild(el("span", "bubble__meta", meta));
  return details;
}

async function sendMessage(text) {
  addMessage("user", text);
  input.value = "";
  autoGrow();
  input.disabled = sendBtn.disabled = true;
  const thinking = addThinking();

  try {
    const resp = await fetch("/api/recommend", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: text }),
    });
    const data = await resp.json();
    thinking.remove();

    if (!resp.ok) {
      addMessage("error", data.error || "Something went wrong.");
      return;
    }
    const li = addMessage("assistant", data.answer);
    const bubble = li.querySelector(".bubble");
    if (data.results && data.results.length) {
      bubble.appendChild(renderResults(data.results));
    }
    const meta = `mode: ${data.mode} · ${data.elapsed_ms} ms`;
    if (data.trace && data.trace.length) {
      bubble.appendChild(renderTrace(data.trace, meta));
    }
    scrollToBottom();
  } catch (err) {
    thinking.remove();
    addMessage("error", "Network error — is the server running?");
  } finally {
    input.disabled = sendBtn.disabled = false;
    input.focus();
  }
}

function autoGrow() {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 160) + "px";
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (text) sendMessage(text);
});

input.addEventListener("input", autoGrow);
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    form.requestSubmit();
  }
});

document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    if (!input.disabled) sendMessage(chip.textContent.trim());
  });
});

(async function initBadge() {
  try {
    const data = await (await fetch("/api/health")).json();
    if (data.mode === "gemini") {
      badge.textContent = `Gemini · ${data.model || "on"}`;
      badge.className = "badge badge--gemini";
      badge.title = "Using Google Gemini to generate the recommendation";
    } else {
      badge.textContent = "Offline mode";
      badge.className = "badge badge--offline";
      badge.title = "No GEMINI_API_KEY set — using the deterministic generator";
    }
  } catch {
    badge.textContent = "offline";
    badge.className = "badge badge--offline";
  }
})();

addMessage(
  "assistant",
  "Hi! Tell me a mood, activity, or genre and I'll retrieve matching songs, re-rank them with a trained vibe model, and explain the picks. Try a suggestion below."
);
input.focus();
