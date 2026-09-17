(function () {
  "use strict";

  function val(form, name) {
    const el = form.elements.namedItem(name);
    return el && "value" in el ? String(el.value || "").trim() : "";
  }

  function buildBody(form) {
    const lines = [
      `Name: ${val(form, "name")}`,
      `Type: ${val(form, "type")}`,
      `Venue: ${val(form, "venue")}`,
      `Place: ${val(form, "place")}`,
      `County: ${val(form, "county")}`,
      `When: ${val(form, "when")}`,
      `Website: ${val(form, "website")}`,
      `Submitter email: ${val(form, "submitter_email")}`,
      "",
      "Notes:",
      val(form, "notes") || "(none)",
    ];
    return lines.join("\n");
  }

  function requireFields(form) {
    const name = val(form, "name");
    const type = val(form, "type");
    const email = val(form, "submitter_email");
    if (!name || !type || !email) {
      return "Please fill in listing name, type, and your email.";
    }
    return "";
  }

  function openMailto(form) {
    const to = form.getAttribute("data-email") || "";
    const listingName = val(form, "name") || "listing";
    const subject = `Folk Directory listing: ${listingName}`;
    const body = buildBody(form);
    const href = `mailto:${encodeURIComponent(to)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    window.location.href = href;
  }

  function openGithub(form) {
    const base =
      form.getAttribute("data-github") ||
      "https://github.com/glen-w/folk-directory/issues/new?template=listing.yml";
    const listingName = val(form, "name") || "listing";
    const title = `[Listing] ${listingName}`;
    const body = buildBody(form);
    const url = new URL(base);
    url.searchParams.set("title", title);
    // GitHub issue forms ignore body when template= is set; still pass for markdown templates / fallbacks
    url.searchParams.set("body", body);
    window.open(url.toString(), "_blank", "noopener");
  }

  function init() {
    const form = document.getElementById("listing-submit-form");
    if (!form) return;
    const status = document.getElementById("listing-submit-status");

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const err = requireFields(form);
      if (err) {
        if (status) status.textContent = err;
        return;
      }
      if (status) {
        status.textContent = "Opening your email app… Thanks — moderated before publish.";
      }
      openMailto(form);
    });

    form.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;
      const btn = target.closest("[data-action]");
      if (!btn || btn.getAttribute("data-action") !== "github") return;
      event.preventDefault();
      const err = requireFields(form);
      if (err) {
        if (status) status.textContent = err;
        return;
      }
      if (status) {
        status.textContent = "Opening GitHub… Thanks — moderated before publish.";
      }
      openGithub(form);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
