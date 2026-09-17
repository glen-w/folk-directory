(function () {
  "use strict";

  function val(form, name) {
    const el = form.elements.namedItem(name);
    return el && "value" in el ? String(el.value || "").trim() : "";
  }

  function setVal(form, name, value) {
    if (!value) return;
    const el = form.elements.namedItem(name);
    if (el && "value" in el) el.value = value;
  }

  function buildBody(form) {
    const lines = [
      `Listing name: ${val(form, "name")}`,
      `Listing id: ${val(form, "listing_id")}`,
      `Listing URL: ${val(form, "listing_url") || "(none)"}`,
      `Claimant name: ${val(form, "claimant_name") || "(none)"}`,
      `Claimant email: ${val(form, "claimant_email")}`,
      "",
      "How connected:",
      val(form, "connection") || "(none)",
      "",
      "Verification route:",
      val(form, "verification") || "(none)",
      "",
      "Anything to fix now:",
      val(form, "notes") || "(none)",
    ];
    return lines.join("\n");
  }

  function requireFields(form) {
    const name = val(form, "name");
    const listingId = val(form, "listing_id");
    const email = val(form, "claimant_email");
    const connection = val(form, "connection");
    const verification = val(form, "verification");
    if (!name || !listingId || !email || !connection || !verification) {
      return "Please fill in listing name, id, your email, how you’re connected, and a verification route.";
    }
    return "";
  }

  function openMailto(form) {
    const to = form.getAttribute("data-email") || "";
    const listingName = val(form, "name") || "listing";
    const listingId = val(form, "listing_id") || "unknown";
    const subject = `Folk Directory claim: ${listingName} (${listingId})`;
    const body = buildBody(form);
    const href = `mailto:${encodeURIComponent(to)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    window.location.href = href;
  }

  function prefillFromQuery(form) {
    const params = new URLSearchParams(window.location.search);
    setVal(form, "listing_id", params.get("id"));
    setVal(form, "name", params.get("name"));
    setVal(form, "listing_url", params.get("url"));

    const idEl = form.elements.namedItem("listing_id");
    if (idEl && params.get("id") && "readOnly" in idEl) {
      idEl.readOnly = true;
    }
  }

  function init() {
    const form = document.getElementById("listing-claim-form");
    if (!form) return;
    const status = document.getElementById("listing-claim-status");

    prefillFromQuery(form);

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const err = requireFields(form);
      if (err) {
        if (status) status.textContent = err;
        return;
      }
      if (status) {
        status.textContent = "Opening your email app… Thanks — claims are reviewed before any access or public edits.";
      }
      openMailto(form);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
