(() => {
  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text == null ? "" : String(text);
    return div.innerHTML;
  }

  function locationLabel(loc) {
    const venue = String(loc.venue || "").trim();
    const place = String(loc.place || "").trim();
    if (venue && place && venue.toLowerCase() !== place.toLowerCase()) {
      return `${venue}, ${place}`;
    }
    return venue || place || "";
  }

  function truncateText(text, max = 140) {
    const s = String(text || "")
      .trim()
      .replace(/\s+/g, " ");
    if (!s) return "";
    if (s.length <= max) return s;
    const cut = s.slice(0, max);
    const lastSpace = cut.lastIndexOf(" ");
    const base = lastSpace > max * 0.6 ? cut.slice(0, lastSpace) : cut;
    return `${base.replace(/[.,;:!?-]+$/u, "")}…`;
  }

  function createMarkerIcon(color) {
    const size = 25;
    const html = `<div style="background-color:${color};width:${size}px;height:${size}px;border-radius:50% 50% 50% 0;transform:rotate(-45deg);border:3px solid white;box-shadow:0 2px 4px rgba(0,0,0,0.3);"></div>`;
    return L.divIcon({
      html,
      className: "custom-marker",
      iconSize: [size, size],
      iconAnchor: [size / 2, size],
    });
  }

  function buildPopup(loc) {
    const href = loc.permalink || "#";
    const parts = [
      `<strong><a href="${escapeHtml(href)}">${escapeHtml(loc.title || "Listing")}</a></strong>`,
    ];
    if (loc.event_type) {
      parts.push(escapeHtml(loc.event_type));
    }
    const where = locationLabel(loc);
    if (where) {
      parts.push(escapeHtml(where));
    }
    const summary = truncateText(loc.description);
    if (summary) {
      parts.push(`<span class="folk-map-popup-desc">${escapeHtml(summary)}</span>`);
    }
    return `<div class="folk-map-popup">${parts.join("<br>")}</div>`;
  }

  async function init() {
    const el = document.getElementById("folk-map");
    const status = document.getElementById("folk-map-status");
    if (!el || !window.L) return;

    // Rough UK envelope (incl. Shetland / Scilly); blocks panning abroad.
    const ukBounds = L.latLngBounds([49.5, -8.8], [61.2, 2.1]);
    const map = L.map(el, {
      maxBounds: ukBounds.pad(0.08),
      maxBoundsViscosity: 1.0,
      minZoom: 5,
    }).setView([54.5, -3.5], 6);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 18,
    }).addTo(map);

    const listedIcon = createMarkerIcon("#2e7d5a");
    const defunctIcon = createMarkerIcon("#8a8a8a");
    const typeIcons = {
      "folk-club": createMarkerIcon("#2e7d5a"),
      session: createMarkerIcon("#3d6e8c"),
      festival: createMarkerIcon("#8a5a2b"),
      dance: createMarkerIcon("#6b5080"),
    };

    const cluster = L.markerClusterGroup({
      chunkedLoading: true,
      spiderfyOnMaxZoom: true,
      showCoverageOnHover: false,
      zoomToBoundsOnClick: true,
      maxClusterRadius: 50,
    });
    map.addLayer(cluster);

    try {
      const res = await fetch("/data/listings-map.json", { credentials: "same-origin" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const locations = (data.locations || []).filter((loc) => loc.geocoded && loc.coordinates);
      locations.forEach((loc) => {
        const muted = loc.status === "defunct";
        const typeKey = String(loc.event_type || "").toLowerCase();
        const icon = muted
          ? defunctIcon
          : typeIcons[typeKey] || listedIcon;
        const marker = L.marker([loc.coordinates.lat, loc.coordinates.lng], {
          icon,
        });
        marker.bindPopup(buildPopup(loc));
        cluster.addLayer(marker);
      });
      if (locations.length) {
        const fitted = cluster.getBounds().pad(0.08);
        map.fitBounds(ukBounds.intersects(fitted) ? fitted.intersect(ukBounds) : ukBounds);
      } else {
        map.fitBounds(ukBounds);
      }
      if (status) {
        status.textContent = "";
        status.hidden = true;
      }
    } catch (err) {
      console.error(err);
      if (status) {
        status.hidden = false;
        status.textContent = "Could not load map data.";
      }
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();
