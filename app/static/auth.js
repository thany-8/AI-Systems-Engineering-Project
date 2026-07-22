"use strict";

/* ------------------------------------------------------------------ *
 * Login / signup form handling. The same script serves both pages;
 * the target endpoint is chosen from the form's data-mode attribute.
 * ------------------------------------------------------------------ */

const form = document.getElementById("auth-form");
const mode = form.dataset.mode; // "login" | "signup"
const errorEl = document.getElementById("form-error");
const submitBtn = form.querySelector("button[type=submit]");
const nextUrl = new URLSearchParams(location.search).get("next") || "/";

function showError(message) {
  errorEl.textContent = message;
  errorEl.classList.add("show");
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  errorEl.classList.remove("show");

  const payload = {
    email: form.email.value.trim(),
    password: form.password.value,
  };
  if (mode === "signup" && form.name) {
    payload.name = form.name.value.trim();
  }

  if (!payload.email || !payload.password) {
    showError("Please fill in your email and password.");
    return;
  }

  const label = submitBtn.textContent;
  submitBtn.disabled = true;
  submitBtn.innerHTML =
    '<span class="spinner"></span> ' + (mode === "signup" ? "Creating…" : "Logging in…");

  try {
    const res = await window.API.send(`/api/auth/${mode}`, "POST", payload);
    const body = await res.json();
    if (!res.ok) throw new Error(body.error || "Something went wrong. Please try again.");
    window.location.href = nextUrl;
  } catch (err) {
    showError(err.message);
    submitBtn.disabled = false;
    submitBtn.textContent = label;
  }
});
