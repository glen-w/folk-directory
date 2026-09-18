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

  const TYPE_COLORS = {
    "folk-club": "#2e7d5a",
    session: "#3d6e8c",
    festival: "#8a5a2b",
    dance: "#6b5080",
  };
  const MIXED_TYPE = "mixed";

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

  function clusterDensity(count) {
    if (count < 10) return "small";
    if (count < 100) return "medium";
    return "large";
  }

  function dominantClusterType(markers) {
    const counts = Object.create(null);
    markers.forEach((marker) => {
      const key = marker.options && marker.options.eventType;
      if (!key || !TYPE_COLORS[key]) return;
      counts[key] = (counts[key] || 0) + 1;
    });
    let best = MIXED_TYPE;
    let bestCount = 0;
    let tied = false;
    Object.keys(counts).forEach((key) => {
      const n = counts[key];
      if (n > bestCount) {
        best = key;
        bestCount = n;
        tied = false;
      } else if (n === bestCount && n > 0) {
        tied = true;
      }
    });
    return tied || bestCount === 0 ? MIXED_TYPE : best;
  }

  function createClusterIcon(cluster, activeType) {
    const count = cluster.getChildCount();
    const density = clusterDensity(count);
    const type =
      activeType && TYPE_COLORS[activeType]
        ? activeType
        : dominantClusterType(cluster.getAllChildMarkers());
    const size = density === "large" ? 50 : density === "medium" ? 44 : 40;
    return L.divIcon({
      html: `<div><span>${count}</span></div>`,
      className: `marker-cluster marker-cluster-${density} marker-cluster--${type}`,
      iconSize: L.point(size, size),
    });
  }

  // Leaflet LatLngBounds has intersects() but no intersect(); clamp manually.
  function clampBounds(bounds, envelope) {
    if (!bounds || !bounds.isValid()) return envelope;
    if (!envelope.intersects(bounds)) return envelope;
    const sw = bounds.getSouthWest();
    const ne = bounds.getNorthEast();
    const clamped = L.latLngBounds(
      [
        Math.max(sw.lat, envelope.getSouth()),
        Math.max(sw.lng, envelope.getWest()),
      ],
      [
        Math.min(ne.lat, envelope.getNorth()),
        Math.min(ne.lng, envelope.getEast()),
      ]
    );
    return clamped.isValid() ? clamped : envelope;
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
    if (loc.www && window.FolkUtils) {
      const websiteUrl = window.FolkUtils.normalizeWebsiteUrl(loc.www);
      if (websiteUrl) {
        const domain = window.FolkUtils.displayDomain(websiteUrl);
        parts.push(`<a href="${escapeHtml(websiteUrl)}" target="_blank" rel="noopener" style="color:#2e7d5a;font-weight:500;">→ ${escapeHtml(domain)}</a>`);
      }
    }
    return `<div class="folk-map-popup">${parts.join("<br>")}</div>`;
  }

  function wireTypeFilters(applyFilter) {
    const chips = document.querySelectorAll("[data-map-type]");
    if (!chips.length) return;

    chips.forEach((chip) => {
      chip.addEventListener("click", () => {
        const type = chip.getAttribute("data-map-type") || "";
        chips.forEach((other) => {
          const active = other === chip;
          other.classList.toggle("is-active", active);
          other.setAttribute("aria-pressed", active ? "true" : "false");
        });
        applyFilter(type);
      });
    });
  }

  async function init() {
    const el = document.getElementById("folk-map");
    const status = document.getElementById("folk-map-status");
    if (!el || !window.L) return;

    // UK & Ireland envelope (incl. Shetland / Scilly / west Kerry).
    const ukBounds = L.latLngBounds([49.5, -11.0], [61.2, 2.1]);
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

    const listedIcon = createMarkerIcon(TYPE_COLORS["folk-club"]);
    const defunctIcon = createMarkerIcon("#8a8a8a");
    const typeIcons = Object.fromEntries(
      Object.entries(TYPE_COLORS).map(([key, color]) => [key, createMarkerIcon(color)])
    );

    let activeType = "";
    const cluster = L.markerClusterGroup({
      chunkedLoading: true,
      spiderfyOnMaxZoom: true,
      showCoverageOnHover: false,
      zoomToBoundsOnClick: true,
      maxClusterRadius: 50,
      iconCreateFunction(group) {
        return createClusterIcon(group, activeType);
      },
    });
    map.addLayer(cluster);

    try {
      const res = await fetch("/data/listings-map.json", { credentials: "same-origin" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const locations = (data.locations || []).filter((loc) => loc.geocoded && loc.coordinates);
      const entries = locations.map((loc) => {
        const muted = loc.status === "defunct";
        const typeKey = String(loc.event_type || "").toLowerCase();
        const icon = muted
          ? defunctIcon
          : typeIcons[typeKey] || listedIcon;
        const marker = L.marker([loc.coordinates.lat, loc.coordinates.lng], {
          icon,
          eventType: TYPE_COLORS[typeKey] ? typeKey : MIXED_TYPE,
        });
        marker.bindPopup(buildPopup(loc));
        return { marker, typeKey };
      });

      function fitToVisible() {
        if (cluster.getLayers().length) {
          const fitted = cluster.getBounds().pad(0.08);
          map.fitBounds(clampBounds(fitted, ukBounds));
        } else {
          map.fitBounds(ukBounds);
        }
      }

      function applyFilter(type) {
        activeType = type || "";
        cluster.clearLayers();
        const visible = type
          ? entries.filter((entry) => entry.typeKey === type)
          : entries;
        visible.forEach((entry) => cluster.addLayer(entry.marker));
        fitToVisible();
      }

      applyFilter("");
      wireTypeFilters(applyFilter);

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
