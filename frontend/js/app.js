/*
  app.js
  ------
  Shared helpers loaded on every page (index.html, dashboard.html, scheme.html).
  Keeps three small jobs:
    1. A stable, anonymous "client id" so bookmarks can be saved without
       asking for any personal information (see database.py for why).
    2. A tiny wrapper around fetch() that turns network/server failures into
       friendly messages instead of raw errors reaching the user.
    3. A simple toast notification for quick confirmations (e.g. "Bookmarked").
*/

const FarmaSchema = (() => {
  const CLIENT_ID_KEY = "farmaschema_client_id";

  function getClientId() {
    let id = localStorage.getItem(CLIENT_ID_KEY);
    if (!id) {
      id = "farmer-" + Math.random().toString(36).slice(2) + Date.now().toString(36);
      localStorage.setItem(CLIENT_ID_KEY, id);
    }
    return id;
  }

  /**
   * Wrapper around fetch() for talking to our own Flask API.
   * Because app.py serves the frontend AND the API from the same origin,
   * a plain relative path like "/api/schemes" works whether you open
   * the site via Flask, a different port, or a preview tool.
   */
  async function apiRequest(path, options = {}) {
    let response;
    try {
      response = await fetch(path, {
        headers: { "Content-Type": "application/json" },
        ...options,
      });
    } catch (networkError) {
      // The backend isn't reachable at all.
      throw new Error(
        "Can't reach the FarmaSchema server. Make sure the Flask backend is running, then reload this page."
      );
    }

    let body = null;
    try {
      body = await response.json();
    } catch (parseError) {
      // Server responded but not with JSON — treat as a generic failure.
    }

    if (!response.ok) {
      const message = (body && body.error) || `Something went wrong (status ${response.status}).`;
      throw new Error(message);
    }

    return body;
  }

  function showToast(message) {
    let toast = document.querySelector(".toast");
    if (!toast) {
      toast = document.createElement("div");
      toast.className = "toast";
      document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.classList.add("visible");
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => toast.classList.remove("visible"), 2200);
  }

  function relevanceFillClass(score) {
    if (score >= 0.5) return "strong";
    if (score >= 0.2) return "";
    return "weak";
  }

  function scorePercent(score) {
    // TF-IDF cosine similarity scores on short text rarely reach 1.0, so we
    // scale for display purposes only (never for ranking, which always
    // uses the raw score). This keeps the percentages readable without
    // changing which scheme is ranked above another.
    return Math.min(100, Math.round(score * 220));
  }

  return { getClientId, apiRequest, showToast, relevanceFillClass, scorePercent };
})();
