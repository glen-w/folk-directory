/**
 * Shared utility functions for Folk Directory
 */

(function (global) {
  "use strict";

  /**
   * Normalize a website URL by adding https:// scheme if missing.
   * @param {string} raw - Raw website/www value from listing data
   * @returns {string} Normalized URL with scheme, or empty string if invalid
   */
  function normalizeWebsiteUrl(raw) {
    const s = String(raw || "").trim();
    if (!s || s.includes("@") || /\s/.test(s)) return "";
    if (/^https?:\/\//i.test(s)) return s;
    return `https://${s.replace(/^\/\//, "")}`;
  }

  /**
   * Extract display domain from a URL (removes www. prefix).
   * @param {string} url - Full URL or domain
   * @returns {string} Display-friendly domain name
   */
  function displayDomain(url) {
    try {
      const host = new URL(url).hostname.replace(/^www\./i, "");
      return host || "";
    } catch (_) {
      return String(url || "")
        .replace(/^https?:\/\//i, "")
        .replace(/^www\./i, "")
        .split("/")[0];
    }
  }

  /**
   * Escape HTML special characters.
   * @param {*} value - Value to escape
   * @returns {string} HTML-safe string
   */
  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  // Export to global namespace
  global.FolkUtils = {
    normalizeWebsiteUrl: normalizeWebsiteUrl,
    displayDomain: displayDomain,
    escapeHtml: escapeHtml,
  };
})(typeof window !== "undefined" ? window : this);
