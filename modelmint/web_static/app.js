const state = {
  snapshot: null,
  selectedModelId: null,
  filters: {
    search: "",
    status: "All",
    category: "All",
  },
};

const els = {
  runIntake: document.querySelector("#run-intake"),
  search: document.querySelector("#search"),
  statusFilter: document.querySelector("#status-filter"),
  categoryFilter: document.querySelector("#category-filter"),
  modelList: document.querySelector("#model-list"),
  detailPanel: document.querySelector("#detail-panel"),
  recordSummary: document.querySelector("#record-summary"),
  rulesList: document.querySelector("#rules-list"),
  resultCount: document.querySelector("#result-count"),
  toast: document.querySelector("#toast"),
  stats: {
    models: document.querySelector("#stat-models"),
    review: document.querySelector("#stat-review"),
    creators: document.querySelector("#stat-creators"),
    assets: document.querySelector("#stat-assets"),
  },
  libraryStatusList: document.querySelector("#library-status-list"),
};

async function loadCatalog() {
  const [catalogResponse, libraryResponse] = await Promise.all([
    fetch("/api/catalog"),
    fetch("/api/library-status"),
  ]);
  state.snapshot = await catalogResponse.json();
  state.libraryStatus = await libraryResponse.json();
  if (!state.selectedModelId && state.snapshot.models.length > 0) {
    state.selectedModelId = state.snapshot.models[0].model_id;
  }
  render();
}

function assetUrl(asset) {
  return `/asset?path=${encodeURIComponent(asset.file_path)}`;
}

function previewImage(asset, fallbackText) {
  if (!asset) return fallbackText;
  return `<img src="${assetUrl(asset)}" alt="" onerror="this.parentElement.textContent='${fallbackText}'; this.remove();">`;
}

function statusClass(status) {
  if (status === "Needs Review" || status === "Needs Test Print") return "review";
  if (status === "Approved" || status === "Published") return "approved";
  if (status === "Rejected" || status === "Archived") return "rejected";
  return "";
}

function render() {
  if (!state.snapshot) return;
  renderStats();
  renderFilters();
  renderModelList();
  renderDetail();
  renderRecords();
  renderLibraryStatus();
  renderRules();
}

function renderStats() {
  const stats = state.snapshot.stats;
  els.stats.models.textContent = stats.models;
  els.stats.review.textContent = stats.needs_review;
  els.stats.creators.textContent = stats.creators;
  els.stats.assets.textContent = stats.assets;
}

function renderFilters() {
  const statuses = ["All", ...state.snapshot.allowed_statuses];
  const categories = [
    "All",
    ...new Set(state.snapshot.models.map((model) => model.category || "Unreviewed").sort()),
  ];
  syncOptions(els.statusFilter, statuses, state.filters.status);
  syncOptions(els.categoryFilter, categories, state.filters.category);
}

function syncOptions(select, values, selected) {
  const current = Array.from(select.options).map((option) => option.value).join("|");
  if (current === values.join("|")) {
    select.value = selected;
    return;
  }
  select.replaceChildren(
    ...values.map((value) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value;
      return option;
    }),
  );
  select.value = selected;
}

function filteredModels() {
  const search = state.filters.search.trim().toLowerCase();
  return state.snapshot.models.filter((model) => {
    const haystack = [
      model.model_name,
      model.creator_name,
      model.release_name,
      model.category,
      model.model_type,
      model.primary_file_path,
    ]
      .join(" ")
      .toLowerCase();
    const matchesSearch = !search || haystack.includes(search);
    const matchesStatus = state.filters.status === "All" || model.status === state.filters.status;
    const matchesCategory = state.filters.category === "All" || model.category === state.filters.category;
    return matchesSearch && matchesStatus && matchesCategory;
  });
}

function renderModelList() {
  const models = filteredModels();
  els.resultCount.textContent = `${models.length} shown`;

  if (models.length === 0) {
    els.modelList.innerHTML = `<div class="model-card"><div></div><div><h4 class="model-title">No matching models</h4><p class="model-meta">Adjust the filters or run intake.</p></div></div>`;
    return;
  }

  els.modelList.replaceChildren(
    ...models.map((model) => {
      const button = document.createElement("button");
      button.className = `model-card${model.model_id === state.selectedModelId ? " selected" : ""}`;
      button.type = "button";
      button.dataset.modelId = model.model_id;

      const preview = model.preview_assets[0];
      button.innerHTML = `
        <div class="thumb">${previewImage(preview, "3D")}</div>
        <div>
          <h4 class="model-title">${escapeHtml(model.model_name)}</h4>
          <div class="model-meta">${escapeHtml(model.creator_name)} · ${escapeHtml(model.category || "Unreviewed")}</div>
          <div class="model-meta">${escapeHtml(model.release_name)}</div>
        </div>
        <span class="badge ${statusClass(model.status)}">${escapeHtml(model.status)}</span>
      `;
      button.addEventListener("click", () => {
        state.selectedModelId = model.model_id;
        render();
      });
      return button;
    }),
  );
}

function renderDetail() {
  const model = state.snapshot.models.find((item) => item.model_id === state.selectedModelId);
  if (!model) {
    els.detailPanel.innerHTML = `
      <div class="empty-state">
        <h3>Select a model</h3>
        <p>Review files, status, colors, and production notes.</p>
      </div>
    `;
    return;
  }

  const preview = model.preview_assets[0];
  const files = model.model_assets
    .map((asset) => `<li><code>${escapeHtml(asset.file_path)}</code></li>`)
    .join("");
  const colorProfile = model.color_profile
    ? `<p class="color-note">${model.color_profile.color_slot_count} slot profile · ${escapeHtml(model.color_profile.finish_notes)}</p>`
    : `<p class="color-note">No color profile yet.</p>`;

  els.detailPanel.innerHTML = `
    <div class="detail-header">
      <span class="badge ${statusClass(model.status)}">${escapeHtml(model.status)}</span>
      <h3>${escapeHtml(model.model_name)}</h3>
      <div class="model-meta">${escapeHtml(model.creator_name)} · ${escapeHtml(model.release_name)}</div>
    </div>
    <div class="preview-large">${previewImage(preview, "No preview image")}</div>
    <form class="detail-form" id="detail-form">
      <div class="two-col">
        <label>Status
          <select name="status">${statusOptions(model.status)}</select>
        </label>
        <label>Review Status
          <select name="review_status">${statusOptions(model.review_status)}</select>
        </label>
      </div>
      <div class="two-col">
        <label>Category
          <input name="category" value="${escapeAttribute(model.category || "")}">
        </label>
        <label>Type
          <input name="model_type" value="${escapeAttribute(model.model_type || "")}">
        </label>
      </div>
      <div class="two-col">
        <label>License
          <input name="license_status" value="${escapeAttribute(model.license_status || "")}">
        </label>
        <label>Complexity
          <input name="estimated_complexity" value="${escapeAttribute(model.estimated_complexity || "")}">
        </label>
      </div>
      <label>Production Notes
        <textarea name="production_notes">${escapeHtml(model.production_notes || "")}</textarea>
      </label>
      <label>Artisan Notes
        <textarea name="artisan_notes">${escapeHtml(model.artisan_notes || "")}</textarea>
      </label>
      <div>
        <strong>Model files</strong>
        <ul class="file-list">${files}</ul>
      </div>
      <div>
        <strong>Color profile</strong>
        ${colorProfile}
      </div>
      <button class="primary-button" type="submit">Save Review</button>
    </form>
  `;

  document.querySelector("#detail-form").addEventListener("submit", saveDetail);
}

function renderRecords() {
  const catalog = state.snapshot.catalog;
  const records = [
    ["Creators", catalog.creators.length],
    ["Releases", catalog.releases.length],
    ["Models", catalog.models.length],
    ["Assets", catalog.assets.length],
    ["Color Profiles", catalog.color_profiles.length],
    ["Finish Rules", catalog.material_finish_rules.length],
    ["Custom Orders", catalog.custom_orders.length],
    ["Schema", `v${catalog.schema_version}`],
  ];

  els.recordSummary.replaceChildren(
    ...records.map(([label, value]) => {
      const card = document.createElement("article");
      card.className = "record-card";
      card.innerHTML = `<strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)}</span>`;
      return card;
    }),
  );
}

function renderRules() {
  const rules = state.snapshot.catalog.material_finish_rules;
  if (!rules.length) {
    els.rulesList.innerHTML = `<article class="rule-card"><h4>No finish rules</h4><p>Add rules before customer-facing finish options are enabled.</p></article>`;
    return;
  }

  els.rulesList.replaceChildren(
    ...rules.map((rule) => {
      const card = document.createElement("article");
      card.className = "rule-card";
      const blocked = rule.blocked_finishes.length
        ? rule.blocked_finishes.map((finish) => `<span>${escapeHtml(finish)}</span>`).join("")
        : "<span>none blocked</span>";
      card.innerHTML = `
        <h4>${escapeHtml(rule.product_category)}</h4>
        <p>${escapeHtml(rule.reason)}</p>
        <div class="rule-tags">${blocked}</div>
      `;
      return card;
    }),
  );
}

function renderLibraryStatus() {
  if (!state.libraryStatus) return;
  const scanner = state.libraryStatus.scanner || {};
  const setup = state.libraryStatus.ok
    ? `<article class="rule-card"><h4>Library setup ready</h4><p>All configured local synced paths currently exist.</p></article>`
    : `<article class="rule-card"><h4>Setup needed</h4><p>Create or sync the missing paths below before relying on intake from the cloud library.</p><ul>${state.libraryStatus.instructions.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></article>`;

  const scannerCard = document.createElement("article");
  scannerCard.className = "rule-card";
  const errors = (scanner.recent_errors || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  scannerCard.innerHTML = `
    <h4>Scanner</h4>
    <p>${escapeHtml(scanner.last_scan_result || "Never run")}</p>
    <dl class="scanner-status">
      <div><dt>Last scan</dt><dd>${escapeHtml(scanner.last_scan_time || "not yet")}</dd></div>
      <div><dt>Interval</dt><dd>${escapeHtml(scanner.scan_interval_minutes || state.libraryStatus.scanner_config.scan_interval_minutes)} minutes</dd></div>
      <div><dt>Auto scan</dt><dd>${scanner.auto_scan_enabled ? "enabled" : "disabled"}</dd></div>
      <div><dt>New releases</dt><dd>${escapeHtml(scanner.new_releases || 0)}</dd></div>
      <div><dt>New models</dt><dd>${escapeHtml(scanner.new_models || 0)}</dd></div>
      <div><dt>New assets</dt><dd>${escapeHtml(scanner.new_assets || 0)}</dd></div>
    </dl>
    ${errors ? `<strong>Recent errors</strong><ul>${errors}</ul>` : ""}
  `;

  const cards = state.libraryStatus.paths.map((item) => {
    const card = document.createElement("article");
    card.className = "rule-card";
    card.innerHTML = `
      <h4>${escapeHtml(item.label)}</h4>
      <p><code>${escapeHtml(item.path)}</code></p>
      <div class="rule-tags">
        <span>${escapeHtml(item.env_name)}</span>
        <span>${item.exists ? "exists" : "missing"}</span>
        <span>${escapeHtml(item.expected_type)}</span>
      </div>
    `;
    return card;
  });

  els.libraryStatusList.innerHTML = setup;
  els.libraryStatusList.append(scannerCard, ...cards);
}

function statusOptions(selected) {
  return state.snapshot.allowed_statuses
    .map((status) => `<option value="${escapeAttribute(status)}"${status === selected ? " selected" : ""}>${escapeHtml(status)}</option>`)
    .join("");
}

async function saveDetail(event) {
  event.preventDefault();
  const modelId = state.selectedModelId;
  const form = new FormData(event.currentTarget);
  const payload = Object.fromEntries(form.entries());
  const response = await fetch(`/api/models/${encodeURIComponent(modelId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    showToast("Save failed.");
    return;
  }

  const result = await response.json();
  state.snapshot = result.snapshot;
  showToast("Review saved.");
  render();
}

async function runIntake() {
  els.runIntake.disabled = true;
  els.runIntake.textContent = "Scanning...";
  const response = await fetch("/api/scanner/run", { method: "POST" });
  els.runIntake.disabled = false;
  els.runIntake.textContent = "Run Scan Now";

  if (!response.ok) {
    showToast("Intake failed.");
    return;
  }

  const result = await response.json();
  state.snapshot = result.snapshot;
  state.libraryStatus.scanner = result.scanner;
  showToast(`Scan complete: ${result.scanner.new_models} new models.`);
  render();
}

function showToast(message) {
  els.toast.textContent = message;
  els.toast.classList.add("visible");
  setTimeout(() => els.toast.classList.remove("visible"), 2200);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttribute(value) {
  return escapeHtml(value).replaceAll("`", "&#096;");
}

els.search.addEventListener("input", (event) => {
  state.filters.search = event.target.value;
  renderModelList();
});

els.statusFilter.addEventListener("change", (event) => {
  state.filters.status = event.target.value;
  renderModelList();
});

els.categoryFilter.addEventListener("change", (event) => {
  state.filters.category = event.target.value;
  renderModelList();
});

els.runIntake.addEventListener("click", runIntake);

loadCatalog().catch((error) => {
  console.error("Could not load catalog.", error);
  showToast("Could not load catalog.");
});
