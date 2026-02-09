const API_BASE = "http://localhost:8000";
let activeSiteId = "";

function parseCSV(value) {
  return value
    .split(",")
    .map((v) => v.trim())
    .filter(Boolean);
}

function buildTimeSlots(start = "08:00", end = "17:00") {
  const slots = [];
  let [h, m] = start.split(":").map(Number);
  const [endH, endM] = end.split(":").map(Number);
  while (h < endH || (h === endH && m < endM)) {
    slots.push(`${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`);
    m += 30;
    if (m >= 60) {
      m = 0;
      h += 1;
    }
  }
  return slots;
}

async function fetchJSON(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) {
    throw new Error(`요청 실패: ${res.status}`);
  }
  return res.json();
}

function renderWorkers(workers) {
  const body = document.getElementById("worker-table-body");
  const checkboxWrap = document.getElementById("worker-checkboxes");
  body.innerHTML = "";
  checkboxWrap.innerHTML = "";

  workers.forEach((name) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${name}</td>`;
    body.appendChild(tr);

    const label = document.createElement("label");
    label.className = "checkbox-item";
    label.innerHTML = `<input type="checkbox" value="${name}" checked /> ${name}`;
    checkboxWrap.appendChild(label);
  });
}

function renderInventory(inventory) {
  const body = document.getElementById("inventory-table-body");
  body.innerHTML = "";
  Object.entries(inventory).forEach(([material, qty]) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${material}</td><td>${qty}</td>`;
    body.appendChild(tr);
  });
}

function renderTimeline(plan) {
  const timeline = document.getElementById("timeline");
  timeline.innerHTML = "";

  const status = document.createElement("p");
  status.className = "scheduler-status";
  status.textContent = `스케줄러 상태: ${plan.scheduler_status} / 모델: ${plan.model || "-"}`;
  timeline.appendChild(status);

  const workers = [...new Set(plan.timeline.map((x) => x.worker))];
  const times = buildTimeSlots();

  const table = document.createElement("table");
  table.className = "plan-grid";

  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");
  headerRow.innerHTML = `<th>시간</th>${workers.map((w) => `<th>${w}</th>`).join("")}`;
  thead.appendChild(headerRow);

  const tbody = document.createElement("tbody");
  times.forEach((time) => {
    const tr = document.createElement("tr");
    const cells = [`<td class="time-cell">${time}</td>`];
    workers.forEach((worker) => {
      const block = plan.timeline.find((x) => x.worker === worker && x.start === time);
      cells.push(
        `<td class="task-cell" contenteditable="true">${block ? `${block.area} / ${block.task}` : ""}</td>`,
      );
    });
    tr.innerHTML = cells.join("");
    tbody.appendChild(tr);
  });

  table.appendChild(thead);
  table.appendChild(tbody);
  timeline.appendChild(table);
}

async function loadSites() {
  const siteSelect = document.getElementById("site-select");
  const data = await fetchJSON(`${API_BASE}/api/usecase1/sites`);
  siteSelect.innerHTML = "";

  const sites = data.sites.length ? data.sites : ["default-site"];
  sites.forEach((siteId) => {
    const option = document.createElement("option");
    option.value = siteId;
    option.textContent = siteId;
    siteSelect.appendChild(option);
  });

  activeSiteId = sites[0];
  siteSelect.value = activeSiteId;
  await loadSiteStatus(activeSiteId);
}

async function loadMaterialOptions() {
  const data = await fetchJSON(`${API_BASE}/api/usecase1/material-options`);
  const select = document.getElementById("material-select");
  select.innerHTML = "";

  data.materials.forEach((name) => {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name;
    select.appendChild(option);
  });

  const customOption = document.createElement("option");
  customOption.value = "custom";
  customOption.textContent = "직접입력";
  select.appendChild(customOption);
}

async function loadSiteStatus(siteId) {
  const data = await fetchJSON(`${API_BASE}/api/usecase1/site/${siteId}`);
  activeSiteId = data.site_id;
  renderWorkers(data.workers);
  renderInventory(data.inventory);
  document.getElementById("active-site-text").textContent = `선택 현장: ${activeSiteId}`;
  if (data.priority_areas?.length) {
    document.getElementById("areas").value = data.priority_areas.join(",");
  }
}

document.getElementById("site-select").addEventListener("change", async (e) => {
  await loadSiteStatus(e.target.value);
});

document.getElementById("create-site-btn").addEventListener("click", async () => {
  const newSite = document.getElementById("new-site-id").value.trim();
  if (!newSite) {
    alert("현장 ID를 입력하세요.");
    return;
  }

  await fetchJSON(`${API_BASE}/api/usecase1/setup?site_id=${encodeURIComponent(newSite)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ workers: [], inventory: {}, priority_areas: [] }),
  });

  await loadSites();
  document.getElementById("site-select").value = newSite;
  await loadSiteStatus(newSite);
  document.getElementById("new-site-id").value = "";
});

document.getElementById("add-worker-btn").addEventListener("click", async () => {
  const name = document.getElementById("worker-name").value.trim();
  if (!name || !activeSiteId) {
    alert("현장과 이름을 확인하세요.");
    return;
  }

  const data = await fetchJSON(`${API_BASE}/api/usecase1/workers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ site_id: activeSiteId, worker_name: name }),
  });

  renderWorkers(data.workers);
  document.getElementById("worker-name").value = "";
});

document.getElementById("material-select").addEventListener("change", (e) => {
  document.getElementById("custom-material").disabled = e.target.value !== "custom";
});

document.getElementById("add-inventory-btn").addEventListener("click", async () => {
  const materialSelect = document.getElementById("material-select").value;
  const customMaterial = document.getElementById("custom-material").value.trim();
  const qty = Number(document.getElementById("material-qty").value || "0");

  const materialName = materialSelect === "custom" ? customMaterial : materialSelect;
  if (!materialName || qty <= 0 || !activeSiteId) {
    alert("자재명/수량/현장을 확인하세요.");
    return;
  }

  const data = await fetchJSON(`${API_BASE}/api/usecase1/inventory`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      site_id: activeSiteId,
      material_name: materialName,
      quantity: qty,
    }),
  });

  renderInventory(data.inventory);
  document.getElementById("material-qty").value = "";
  document.getElementById("custom-material").value = "";
});

document.getElementById("go-usecase2-btn").addEventListener("click", async () => {
  if (!activeSiteId) {
    alert("현장을 먼저 선택하세요.");
    return;
  }
  await loadSiteStatus(activeSiteId);
  document.getElementById("usecase2-section").classList.remove("hidden");
  document.getElementById("usecase2-section").scrollIntoView({ behavior: "smooth" });
});

document.getElementById("plan-form").addEventListener("submit", async (e) => {
  e.preventDefault();

  const selectedWorkers = [...document.querySelectorAll('#worker-checkboxes input:checked')].map(
    (input) => input.value,
  );

  if (!selectedWorkers.length) {
    alert("오늘 작업 인력을 최소 1명 선택하세요.");
    return;
  }

  const payload = {
    site_id: activeSiteId,
    selected_workers: selectedWorkers,
    incoming_materials: {},
    priority_areas: parseCSV(document.getElementById("areas").value),
    weather_summary: document.getElementById("weather").value.trim() || null,
  };

  const data = await fetchJSON(`${API_BASE}/api/usecase2/plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  renderTimeline(data.plan);
});

loadMaterialOptions()
  .then(loadSites)
  .catch(() => alert("초기 데이터 로딩 실패"));
