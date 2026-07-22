"use strict";

const messagesEl = document.getElementById("messages");
const form = document.getElementById("composer");
const input = document.getElementById("message");
const sendBtn = document.getElementById("send");
const badge = document.getElementById("mode-badge");

/** Create an element with optional class and text. */
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

/** Render multi-line text safely (no HTML injection). */
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

/** Add a message bubble. Returns the <li> so it can be updated later. */
function addMessage(role, text) {
  const li = el("li", `msg msg--${role}`);
  const bubble = el("div", "bubble");
  if (text != null) multiline(bubble, text);
  li.appendChild(bubble);
  messagesEl.appendChild(li);
  scrollToBottom();
  return li;
}

/** Show an animated typing indicator; returns the <li>. */
function addThinking() {
  const li = addMessage("assistant", null);
  const dots = el("span", "dots");
  dots.setAttribute("aria-label", "Thinking");
  dots.append(el("span"), el("span"), el("span"));
  li.querySelector(".bubble").appendChild(dots);
  return li;
}

/** Build the collapsible agent-trace panel from the trace array. */
function renderTrace(trace, meta) {
  const details = el("details", "trace");
  const summary = el("summary", null, "Agent steps");
  details.appendChild(summary);
  const list = el("ol", "trace__list");

  trace.forEach((step) => {
    let cls = "trace__step";
    let line = "";
    if (step.step === "plan") {
      line = step.final
        ? "🧠 plan → direct reply"
        : `🧠 plan → tools: ${(step.tool_calls || []).join(", ") || "none"}`;
    } else if (step.step === "act") {
      const args = step.args && Object.keys(step.args).length
        ? JSON.stringify(step.args) : "{}";
      line = `${step.ok ? "⚙️" : "⛔"} act → ${step.tool}(${args})`;
      if (step.error) { line += ` — ${step.error}`; cls += " trace__step--fail"; }
    } else if (step.step === "check") {
      if (step.ok) {
        line = `✅ check → ${step.reason}`;
      } else {
        line = `🔁 check → revise: ${step.reason} (add: ${(step.add || []).join(", ")})`;
        cls += " trace__step--revise";
      }
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
    const resp = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });
    const data = await resp.json();
    thinking.remove();

    if (!resp.ok) {
      addMessage("error", data.error || "Something went wrong.");
      return;
    }
    const li = addMessage("assistant", data.answer);
    const meta = `mode: ${data.mode} · ${data.elapsed_ms} ms`;
    if (data.trace && data.trace.length) {
      li.querySelector(".bubble").appendChild(renderTrace(data.trace, meta));
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

/** Fetch reasoning mode for the badge. */
(async function initBadge() {
  try {
    const data = await (await fetch("/api/health")).json();
    if (data.mode === "gemini") {
      badge.textContent = `Gemini · ${data.model || "on"}`;
      badge.className = "badge badge--gemini";
      badge.title = "Using Google Gemini for reasoning";
    } else {
      badge.textContent = "Offline mode";
      badge.className = "badge badge--offline";
      badge.title = "No GEMINI_API_KEY set — using the deterministic planner";
    }
  } catch {
    badge.textContent = "offline";
    badge.className = "badge badge--offline";
  }
})();

addMessage(
  "assistant",
  "Hi! I'm PawPal+ Companion. I can plan your pets' care day and recommend music — try a suggestion below or ask me both at once."
);
input.focus();
