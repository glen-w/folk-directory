(function () {
  "use strict";

  const DEFAULTS = {
    indexUrl: "/listings/index.json",
    enabledFilterIds: ["type", "county"],
    showOptions: [10, 25, 50, 100, "all"],
    defaultShow: 25,
    defaultSort: "title",
  };

  function slugToLabel(value) {
    return String(value || "")
      .split("-")
      .filter(Boolean)
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ");
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  const FILTERS = [
    {
      id: "type",
      param: "type",
      field: "event_types",
      match: "includes",
      control: "select",
      label: "Type",
      emptyLabel: "Any type",
      formatOption: slugToLabel,
    },
    {
      id: "county",
      param: "county",
      field: "county",
      match: "eq",
      control: "select",
      label: "County",
      emptyLabel: "Any county",
    },
    // Future: status, place, q (contains), multi-select type, etc.
  ];

  function matchItem(item, filter, value) {
    if (value === "" || value == null) return true;
    const fieldValue = item[filter.field];

    switch (filter.match) {
      case "includes": {
        const list = Array.isArray(fieldValue)
          ? fieldValue
          : fieldValue
            ? [fieldValue]
            : [];
        return list.map(String).includes(String(value));
      }
      case "contains": {
        const haystacks = (filter.fields || [filter.field]).map((key) =>
          String(item[key] || "").toLowerCase()
        );
        const needle = String(value).toLowerCase();
        return haystacks.some((h) => h.includes(needle));
      }
      case "anyOf": {
        const wanted = Array.isArray(value) ? value : String(value).split(",");
        const list = Array.isArray(fieldValue)
          ? fieldValue.map(String)
          : fieldValue
            ? [String(fieldValue)]
            : [];
        return wanted.some((v) => list.includes(String(v)));
      }
      case "eq":
      default:
        return String(fieldValue ?? "") === String(value);
    }
  }

  function uniqueFieldValues(items, filter) {
    const seen = new Set();
    for (const item of items) {
      const raw = item[filter.field];
      const values = Array.isArray(raw) ? raw : raw ? [raw] : [];
      for (const value of values) {
        const text = String(value ?? "").trim();
        if (text) seen.add(text);
      }
    }
    return Array.from(seen).sort((a, b) =>
      a.localeCompare(b, undefined, { sensitivity: "base" })
    );
  }

  function parseShow(raw, config) {
    if (raw == null || raw === "") return config.defaultShow;
    const lowered = String(raw).toLowerCase();
    if (lowered === "all") return "all";
    const num = Number(raw);
    if (
      Number.isFinite(num) &&
      config.showOptions.some((opt) => opt === num || String(opt) === String(num))
    ) {
      return num;
    }
    return config.defaultShow;
  }

  function parseState(url, config, enabledFilters) {
    const params = new URL(url, window.location.origin).searchParams;
    const filters = {};
    for (const filter of enabledFilters) {
      filters[filter.id] = params.get(filter.param) || "";
    }
    const pageRaw = Number(params.get("page") || "1");
    const page = Number.isFinite(pageRaw) && pageRaw >= 1 ? Math.floor(pageRaw) : 1;
    return {
      filters,
      page,
      show: parseShow(params.get("show"), config),
      sort: params.get("sort") || config.defaultSort,
    };
  }

  function applyFilters(items, state, enabledFilters) {
    return items.filter((item) =>
      enabledFilters.every((filter) =>
        matchItem(item, filter, state.filters[filter.id])
      )
    );
  }

  function sortItems(items, sortKey) {
    const key = sortKey || "title";
    return items.slice().sort((a, b) =>
      String(a[key] || "").localeCompare(String(b[key] || ""), undefined, {
        sensitivity: "base",
      })
    );
  }

  function resolvePageSize(show, filteredCount) {
    if (show === "all") return Math.max(filteredCount, 1);
    const num = Number(show);
    return Number.isFinite(num) && num > 0 ? num : 25;
  }

  function paginate(items, page, pageSize) {
    const total = items.length;
    const totalPages = Math.max(1, Math.ceil(total / pageSize) || 1);
    const safePage = Math.min(Math.max(1, page), totalPages);
    const start = (safePage - 1) * pageSize;
    return {
      page: safePage,
      totalPages,
      total,
      items: items.slice(start, start + pageSize),
    };
  }

  function syncUrl(state, config, enabledFilters) {
    const params = new URLSearchParams();
    for (const filter of enabledFilters) {
      const value = state.filters[filter.id];
      if (value) params.set(filter.param, value);
    }
    if (state.show !== config.defaultShow) {
      params.set("show", String(state.show));
    }
    if (state.sort && state.sort !== config.defaultSort) {
      params.set("sort", state.sort);
    }
    if (state.page > 1 && state.show !== "all") {
      params.set("page", String(state.page));
    }
    const query = params.toString();
    const next = query
      ? `${window.location.pathname}?${query}`
      : window.location.pathname;
    window.history.replaceState({}, "", next);
  }

  function renderFilterControls(root, enabledFilters, facets, state, config) {
    const parts = enabledFilters.map((filter) => {
      const options = (facets[filter.id] || [])
        .map((value) => {
          const label = filter.formatOption
            ? filter.formatOption(value)
            : value;
          const selected =
            String(state.filters[filter.id] || "") === String(value)
              ? " selected"
              : "";
          return `<option value="${escapeHtml(value)}"${selected}>${escapeHtml(label)}</option>`;
        })
        .join("");
      return `
        <label class="listings-filter">
          <span class="listings-filter-label">${escapeHtml(filter.label)}</span>
          <select data-filter="${escapeHtml(filter.id)}" aria-label="${escapeHtml(filter.label)}">
            <option value="">${escapeHtml(filter.emptyLabel || "Any")}</option>
            ${options}
          </select>
        </label>`;
    });

    const showOptions = config.showOptions
      .map((opt) => {
        const value = String(opt);
        const label = value.toLowerCase() === "all" ? "All" : value;
        const selected =
          String(state.show).toLowerCase() === value.toLowerCase()
            ? " selected"
            : "";
        return `<option value="${escapeHtml(value)}"${selected}>${escapeHtml(label)}</option>`;
      })
      .join("");

    parts.push(`
      <label class="listings-filter listings-filter-show">
        <span class="listings-filter-label">Show</span>
        <select data-show aria-label="Show">
          ${showOptions}
        </select>
      </label>`);

    parts.push(`
      <button type="button" class="listings-clear" data-clear>
        Clear
      </button>`);

    root.innerHTML = parts.join("");
  }

  function metaLine(item) {
    const type = Array.isArray(item.event_types) && item.event_types.length
      ? slugToLabel(item.event_types[0])
      : "";
    const bits = [type, item.county, item.when].filter(Boolean);
    if (item.status && String(item.status).toLowerCase() === "defunct") {
      bits.push("Defunct");
    }
    return bits.join(" · ");
  }

  function renderResults(root, items) {
    if (!items.length) {
      root.innerHTML =
        '<p class="listings-empty">No events match these filters.</p>';
      return;
    }
    root.innerHTML = items
      .map((item) => {
        const meta = metaLine(item);
        const summary = item.summary
          ? `<div class="entry-content"><p>${escapeHtml(item.summary)}</p></div>`
          : "";
        const footer = meta
          ? `<footer class="entry-footer"><span class="listings-card-meta">${escapeHtml(meta)}</span></footer>`
          : "";
        return `
          <article class="post-entry listings-card">
            <header class="entry-header">
              <h2 class="entry-hint-parent">${escapeHtml(item.title)}</h2>
            </header>
            ${summary}
            ${footer}
            <a class="entry-link" aria-label="post link to ${escapeHtml(item.title)}" href="${escapeHtml(item.permalink)}"></a>
          </article>`;
      })
      .join("");
  }

  function renderPagination(root, pageInfo, show) {
    if (show === "all" || pageInfo.totalPages <= 1) {
      root.innerHTML = "";
      return;
    }
    const prevDisabled = pageInfo.page <= 1;
    const nextDisabled = pageInfo.page >= pageInfo.totalPages;
    const pageOptions = Array.from({ length: pageInfo.totalPages }, (_, i) => {
      const n = i + 1;
      const selected = n === pageInfo.page ? " selected" : "";
      return `<option value="${n}"${selected}>${n}</option>`;
    }).join("");
    root.innerHTML = `
      <nav class="pagination listings-pagination" aria-label="Pagination">
        <button type="button" class="prev" data-page-delta="-1" ${prevDisabled ? "disabled" : ""}>« Prev</button>
        <label class="listings-page-status">
          Page
          <select class="listings-page-select" data-page-select aria-label="Jump to page">${pageOptions}</select>
          / ${pageInfo.totalPages}
        </label>
        <button type="button" class="next" data-page-delta="1" ${nextDisabled ? "disabled" : ""}>Next »</button>
      </nav>`;
  }

  function renderStatus(root, total, filteredCount) {
    if (!root) return;
    if (filteredCount === total) {
      root.textContent = `${filteredCount} events`;
    } else {
      root.textContent = `${filteredCount} of ${total} events`;
    }
  }

  async function init(userConfig) {
    const config = { ...DEFAULTS, ...(userConfig || {}) };
    const enabledFilters = FILTERS.filter((f) =>
      config.enabledFilterIds.includes(f.id)
    );

    const filtersEl = document.getElementById("listings-filters");
    const resultsEl = document.getElementById("listings-results");
    const paginationEl = document.getElementById("listings-pagination");
    const statusEl = document.getElementById("listings-status");

    if (!filtersEl || !resultsEl || !paginationEl) return;

    let items = [];
    try {
      const res = await fetch(config.indexUrl);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      items = Array.isArray(data.items) ? data.items : [];
    } catch (err) {
      if (statusEl) {
        statusEl.textContent =
          "Could not load events index. Enable JavaScript fallback or try again.";
      }
      return;
    }

    let state = parseState(window.location.href, config, enabledFilters);

    function facetsFrom(candidateItems) {
      const facets = {};
      for (const filter of enabledFilters) {
        facets[filter.id] = uniqueFieldValues(candidateItems, filter);
      }
      return facets;
    }

    function render() {
      const filtered = sortItems(
        applyFilters(items, state, enabledFilters),
        state.sort
      );
      const pageSize = resolvePageSize(state.show, filtered.length);
      const pageInfo = paginate(filtered, state.page, pageSize);
      state.page = pageInfo.page;

      // Facets from full index in v1 (stable option lists)
      renderFilterControls(
        filtersEl,
        enabledFilters,
        facetsFrom(items),
        state,
        config
      );
      renderStatus(statusEl, items.length, filtered.length);
      renderResults(resultsEl, pageInfo.items);
      renderPagination(paginationEl, pageInfo, state.show);
      syncUrl(state, config, enabledFilters);
    }

    filtersEl.addEventListener("change", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLSelectElement)) return;

      if (target.hasAttribute("data-show")) {
        state.show = parseShow(target.value, config);
        state.page = 1;
        render();
        return;
      }

      const filterId = target.getAttribute("data-filter");
      if (!filterId) return;
      state.filters[filterId] = target.value || "";
      state.page = 1;
      render();
    });

    filtersEl.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;
      if (!target.closest("[data-clear]")) return;
      for (const filter of enabledFilters) {
        state.filters[filter.id] = "";
      }
      state.show = config.defaultShow;
      state.page = 1;
      state.sort = config.defaultSort;
      render();
    });

    paginationEl.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;
      const btn = target.closest("[data-page-delta]");
      if (!btn || btn.hasAttribute("disabled")) return;
      const delta = Number(btn.getAttribute("data-page-delta") || "0");
      state.page = Math.max(1, state.page + delta);
      render();
    });

    paginationEl.addEventListener("change", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLSelectElement)) return;
      if (!target.hasAttribute("data-page-select")) return;
      const nextPage = Number(target.value);
      if (!Number.isFinite(nextPage) || nextPage < 1) return;
      state.page = nextPage;
      render();
    });

    window.addEventListener("popstate", () => {
      state = parseState(window.location.href, config, enabledFilters);
      render();
    });

    render();
  }

  window.ListingsBrowse = { init, FILTERS };
})();
