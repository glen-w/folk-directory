(() => {
  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text == null ? "" : String(text);
    return div.innerHTML;
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

  async function init() {
    const el = document.getElementById("folk-map");
    const status = document.getElementById("folk-map-status");
    if (!el || !window.L) return;

    const map = L.map(el).setView([54.5, -3.5], 6);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 18,
    }).addTo(map);

    const listedIcon = createMarkerIcon("#2e7d5a");
    const defunctIcon = createMarkerIcon("#8a8a8a");

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
        const marker = L.marker([loc.coordinates.lat, loc.coordinates.lng], {
          icon: muted ? defunctIcon : listedIcon,
        });
        const href = loc.permalink || "#";
        const popup = `<div class="folk-map-popup"><strong><a href="${escapeHtml(href)}">${escapeHtml(loc.title || "Listing")}</a></strong><br>${escapeHtml(loc.event_type || "")}<br>${escapeHtml(loc.address || "")}</div>`;
        marker.bindPopup(popup);
        cluster.addLayer(marker);
      });
      if (locations.length) {
        map.fitBounds(cluster.getBounds().pad(0.08));
      }
      const meta = data.metadata || {};
      if (status) {
        status.textContent = `${locations.length} mapped listings` +
          (meta.total ? ` (${meta.geocoded || locations.length}/${meta.total} geocoded)` : "");
      }
    } catch (err) {
      console.error(err);
      if (status) status.textContent = "Could not load map data.";
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();
