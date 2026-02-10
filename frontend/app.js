
const API_BASE = "";  // 같은 서버에서 서빙되므로 상대경로 사용
let activeSiteId = "";
let currentPlan = null;
let workItems = [];

// --- 유틸리티 ---
function parseCSV(value) {
  return value.split(",").map((v) => v.trim()).filter(Boolean);
}

function buildTimeSlots(start = "08:00", end = "17:00") {
  const slots = [];
  let [h, m] = start.split(":").map(Number);
  const [endH, endM] = end.split(":").map(Number);
  while (h < endH || (h === endH && m < endM)) {
    slots.push(`${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`);
    m += 30;
    if (m >= 60) { m = 0; h += 1; }
  }
  return slots;
}

async function fetchJSON(url, options = {}) {
  const controller = new AbortController();
  const timeout = options.timeout || 120000; // 기본 타임아웃 120초 (AI 호출 고려)
  const timer = setTimeout(() => controller.abort(), timeout);
  
  try {
    const res = await fetch(url, { ...options, signal: controller.signal });
    clearTimeout(timer);
    if (!res.ok) throw new Error(`요청 실패: ${res.status}`);
    return res.json();
  } catch (err) {
    clearTimeout(timer);
    if (err.name === 'AbortError') {
      throw new Error('서버 응답 시간 초과 (120초). 다시 시도해주세요.');
    }
    throw err;
  }
}

// --- 네비게이션 ---
function switchView(viewId) {
  // 모든 뷰 숨김
  document.querySelectorAll(".view").forEach(el => el.classList.remove("active"));
  document.querySelectorAll(".nav-item").forEach(el => el.classList.remove("active"));
  
  // 선택된 뷰 표시
  document.getElementById(viewId).classList.add("active");
  const navItem = document.querySelector(`.nav-item[data-target="${viewId}"]`);
  if (navItem) navItem.classList.add("active");
}

document.querySelectorAll(".nav-item").forEach(item => {
  item.addEventListener("click", () => {
    switchView(item.dataset.target);
  });
});

document.getElementById("go-planning-btn").addEventListener("click", () => {
  if (!activeSiteId) {
    alert("먼저 현장을 선택해주세요.");
    return;
  }
  switchView("planning-view");
});

document.getElementById("go-closing-btn").addEventListener("click", () => {
  if (!activeSiteId) {
    alert("현장이 선택되지 않았습니다.");
    return;
  }
  switchView("closing-view");
});

// --- 1. 현장 설정 ---
async function loadSites() {
  const siteSelect = document.getElementById("site-select");
  try {
    const data = await fetchJSON(`${API_BASE}/api/usecase1/sites`);
    siteSelect.innerHTML = `<option value="">현장 선택</option>`; // 기본값 추가

    if (data.sites && data.sites.length > 0) {
      data.sites.forEach((siteId) => {
        const option = document.createElement("option");
        option.value = siteId;
        option.textContent = siteId;
        siteSelect.appendChild(option);
      });
      
      // 기존에 선택된 현장이 있다면 유지, 없다면 첫 번째 선택
      if (activeSiteId && data.sites.includes(activeSiteId)) {
        siteSelect.value = activeSiteId;
      } else {
        activeSiteId = data.sites[0];
        siteSelect.value = activeSiteId;
      }
      
      // 상태 로딩은 선택된 값에 대해 수행
      await loadSiteStatus(activeSiteId);
    } else {
        // 현장이 없는 경우 처리
        siteSelect.innerHTML += `<option value="" disabled>등록된 현장 없음</option>`;
    }
  } catch (error) {
    console.error("현장 목록 로딩 실패:", error);
    siteSelect.innerHTML = `<option value="">로딩 실패</option>`;
  }
}

async function loadSiteStatus(siteId) {
  if (!siteId) return; // siteId가 없으면 중단
  try {
    const data = await fetchJSON(`${API_BASE}/api/usecase1/site/${encodeURIComponent(siteId)}`); // URL 인코딩 추가
    activeSiteId = data.site_id;
    document.getElementById("active-site-display").textContent = `📍 ${activeSiteId}`;
    
    renderWorkers(data.workers || []);
    renderInventory(data.inventory || {});
    renderAreaProgress(data.area_progress || {}, data.overall_progress || 0);
    
    if (data.priority_areas?.length) {
      document.getElementById("areas").value = data.priority_areas.join(",");
    }

    // 타임라인은 AI 계획 생성 버튼을 눌러야 표시됨
    document.getElementById("timeline-container").classList.add("hidden");
    
  } catch (error) {
    console.error("현장 상태 로딩 실패:", error);
  }
}

function renderWorkers(workers) {
  const body = document.getElementById("worker-table-body");
  const checkboxWrap = document.getElementById("worker-checkboxes");
  body.innerHTML = "";
  checkboxWrap.innerHTML = "";

  workers.forEach((name) => {
    // 테이블
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${name}</td>`;
    body.appendChild(tr);

    // 체크박스 (계획 수립용)
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

function renderAreaProgress(areaProgress, overallProgress) {
  const pct = Math.round(overallProgress || 0);
  document.getElementById("overall-percent").textContent = `${pct}%`;
  document.getElementById("overall-bar").style.width = `${pct}%`;

  const container = document.getElementById("area-progress-list");
  container.innerHTML = "";

  Object.entries(areaProgress).forEach(([area, progress]) => {
    const p = Math.round(progress);
    const div = document.createElement("div");
    div.className = "area-progress-item";
    div.innerHTML = `
      <div class="progress-label">
        <span class="area-name">${area}</span>
        <span class="progress-percent">${p}%</span>
      </div>
      <div class="area-bar-bg">
        <div class="area-bar-fill" style="width: ${p}%;"></div>
      </div>
    `;
    container.appendChild(div);
  });
}

function renderTimeline(plan) {
  const container = document.getElementById("timeline");
  container.innerHTML = "";

  if (!plan.timeline || !plan.timeline.length) {
    container.innerHTML = "<p>\ud0c0\uc784\ub77c\uc778 \ub370\uc774\ud130\uac00 \uc5c6\uc2b5\ub2c8\ub2e4.</p>";
    return;
  }

  if (plan.overview) {
    const overview = document.createElement("div");
    overview.style.cssText = "margin-bottom:15px; padding:12px; background:#e8eaf6; border-radius:8px;";
    overview.innerHTML = `<strong>\ud83d\udccb \uc791\uc5c5 \uac1c\uc694:</strong> ${plan.overview}`;
    container.appendChild(overview);
  }

  const table = document.createElement("table");
  table.innerHTML = `
    <thead>
      <tr>
        <th style="width:120px;">\uc2dc\uac04</th>
        <th style="width:80px;">\uc791\uc5c5\uc790</th>
        <th style="width:100px;">\uad6c\uc5ed</th>
        <th>\uc791\uc5c5 \ub0b4\uc6a9</th>
      </tr>
    </thead>
  `;
  const tbody = document.createElement("tbody");
  plan.timeline.forEach(item => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${item.start} - ${item.end}</td>
      <td>${item.worker}</td>
      <td>${item.area}</td>
      <td>${item.task}</td>
    `;
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  container.appendChild(table);

  if (plan.weather && plan.weather.description) {
    const weather = document.createElement("div");
    weather.style.cssText = "margin-top:10px; padding:10px; background:#fff3e0; border-radius:8px; font-size:0.9rem;";
    weather.innerHTML = `<strong>\ud83c\udf24\ufe0f \ub0a0\uc528:</strong> ${plan.weather.description}`;
    container.appendChild(weather);
  }

  if (plan.notes && plan.notes.length) {
    const notes = document.createElement("div");
    notes.style.cssText = "margin-top:10px; padding:10px; background:#fce4ec; border-radius:8px; font-size:0.9rem;";
    notes.innerHTML = `<strong>\ud83d\udccc \ucc38\uace0\uc0ac\ud56d:</strong><ul style="margin:5px 0 0 15px;">${plan.notes.map(n => '<li>' + n + '</li>').join("")}</ul>`;
    container.appendChild(notes);
  }
}

function initWorkChecklist(timeline) {
  const tbody = document.getElementById("closing-table-body");
  tbody.innerHTML = "";
  workItems = [];

  const workerSelect = document.getElementById("edit-worker");
  const existingWorkers = new Set();

  timeline.forEach((item, idx) => {
    existingWorkers.add(item.worker);
    workItems.push({ ...item, completed: false, note: "" });

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${item.worker}</td>
      <td>${item.start} - ${item.end}</td>
      <td>${item.area}</td>
      <td>${item.task}</td>
      <td><input type="checkbox" data-idx="${idx}" class="work-check"></td>
      <td><input type="text" data-idx="${idx}" class="work-note" placeholder="\ube44\uace0" style="width:100%;"></td>
      <td><button type="button" class="btn-small btn-danger work-delete" data-idx="${idx}">\uc0ad\uc81c</button></td>
    `;
    tbody.appendChild(tr);
  });

  workerSelect.innerHTML = '<option value="">\uc791\uc5c5\uc790</option>';
  existingWorkers.forEach(name => {
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = name;
    workerSelect.appendChild(opt);
  });
}

document.getElementById("site-select").addEventListener("change", async (e) => {
  await loadSiteStatus(e.target.value);
});

document.getElementById("create-site-btn").addEventListener("click", async () => {
  const newSite = document.getElementById("new-site-id").value.trim();
  if (!newSite) { alert("현장명을 입력하세요."); return; }

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
  if (!name) { alert("이름을 입력하세요."); return; }

  const data = await fetchJSON(`${API_BASE}/api/usecase1/workers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ site_id: activeSiteId, worker_name: name }),
  });

  renderWorkers(data.workers);
  document.getElementById("worker-name").value = "";
});

// --- 2. 계획 수립 ---
// 기존 submit 이벤트 리스너 제거 또는 변경
// document.getElementById("plan-form").addEventListener("submit", ... ) -> 이 부분 수정 필요

// 폼 기본 제출 차단
document.getElementById("plan-form").addEventListener("submit", (e) => { e.preventDefault(); });

// 버튼 클릭 이벤트로 변경
document.getElementById("generate-plan-btn").addEventListener("click", async (e) => {
  e.preventDefault();
  const submitBtn = document.getElementById("generate-plan-btn");
  const originalText = submitBtn.textContent;

  const selectedWorkers = [...document.querySelectorAll('#worker-checkboxes input:checked')].map(i => i.value);
  if (!selectedWorkers.length) { alert("인력을 최소 1명 선택하세요."); return; }

  submitBtn.disabled = true;
  submitBtn.textContent = "AI가 계획을 분석 중입니다... ⏳";

  try {
    const payload = {
      site_id: activeSiteId,
      selected_workers: selectedWorkers,
      incoming_materials: {},
      priority_areas: parseCSV(document.getElementById("areas").value),
      floor_start: parseInt(document.getElementById("floor-start").value) || null,
      floor_end: parseInt(document.getElementById("floor-end").value) || null,
    };

    const data = await fetchJSON(`${API_BASE}/api/usecase2/plan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    console.log("Plan created:", JSON.stringify(data).substring(0, 300)); // 디버그용 로그 추가
    console.log("[DEBUG] data.plan exists:", !!data.plan, "data.plan.timeline exists:", !!(data.plan && data.plan.timeline));

    currentPlan = data.plan;
    
    if (!data.plan || !data.plan.timeline) {
        throw new Error("서버 응답에 타임라인 데이터가 없습니다.");
    }

    renderTimeline(data.plan);
    initWorkChecklist(data.plan.timeline);
    
    const timelineContainer = document.getElementById("timeline-container");
    timelineContainer.classList.remove("hidden");
    timelineContainer.scrollIntoView({ behavior: "smooth" });
    
  } catch (error) {
    console.error("Plan Error:", error);
    alert(`계획 생성 실패: ${error.message || error}`);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = originalText;
  }
});

// --- 3. 작업 마감 뷰 이벤트 핸들러 ---

// 체크리스트 체크/노트 이벤트 위임
document.getElementById("closing-table-body").addEventListener("change", (e) => {
  const idx = Number(e.target.dataset.idx);
  if (e.target.classList.contains("work-check") && workItems[idx]) {
    workItems[idx].completed = e.target.checked;
  }
  if (e.target.classList.contains("work-note") && workItems[idx]) {
    workItems[idx].note = e.target.value;
  }
});

// 삭제 버튼 이벤트 위임
document.getElementById("closing-table-body").addEventListener("click", (e) => {
  if (e.target.classList.contains("work-delete")) {
    const idx = Number(e.target.dataset.idx);
    workItems.splice(idx, 1);
    initWorkChecklist(workItems);
  }
});

// 추가 작업 등록
document.getElementById("add-work-item-btn").addEventListener("click", () => {
  const worker = document.getElementById("edit-worker").value;
  const start = document.getElementById("edit-start").value || "08:00";
  const end = document.getElementById("edit-end").value || "17:00";
  const area = document.getElementById("edit-area").value;
  const task = document.getElementById("edit-task").value.trim();

  if (!worker || !task) { alert("작업자와 작업 내용을 입력하세요."); return; }

  workItems.push({ worker, start, end, area, task, completed: false, note: "" });
  initWorkChecklist(workItems);

  document.getElementById("edit-task").value = "";
});

// 작업 일지 저장
document.getElementById("save-work-result-btn").addEventListener("click", async () => {
  if (!activeSiteId) { alert("현장이 선택되지 않았습니다."); return; }
  if (!workItems.length) { alert("저장할 작업 내역이 없습니다."); return; }

  try {
    await fetchJSON(`${API_BASE}/api/usecase3/save-work`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ site_id: activeSiteId, work_items: workItems }),
    });
    alert("작업 일지가 저장되었습니다.");
  } catch (err) {
    alert("저장 실패: " + (err.message || err));
  }
});

// 작업일지 양식 다운로드 (Excel)
document.getElementById("download-report-btn").addEventListener("click", () => {
  if (!activeSiteId) { alert("현장이 선택되지 않았습니다."); return; }
  window.open(`${API_BASE}/api/usecase3/work-report?site_id=${encodeURIComponent(activeSiteId)}`, "_blank");
});

// 노무대장 엑셀 다운로드
document.getElementById("download-manpower-btn").addEventListener("click", () => {
  if (!activeSiteId) { alert("현장이 선택되지 않았습니다."); return; }
  window.open(`${API_BASE}/api/usecase3/manpower-log?site_id=${encodeURIComponent(activeSiteId)}`, "_blank");
});

// 초기 로딩
// 독립적으로 실행하여 하나가 실패해도 멈추지 않도록 함
loadMaterialOptions().catch(e => console.error("Materials init failed", e));
loadSites().catch(e => console.error("Sites init failed", e));

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

document.getElementById("material-select").addEventListener("change", (e) => {
  document.getElementById("custom-material").disabled = e.target.value !== "custom";
});

document.getElementById("add-inventory-btn").addEventListener("click", async () => {
  const materialSelect = document.getElementById("material-select").value;
  const customMaterial = document.getElementById("custom-material").value.trim();
  const qty = Number(document.getElementById("material-qty").value || "0");
  const materialName = materialSelect === "custom" ? customMaterial : materialSelect;

  if (!materialName || qty <= 0) { alert("자재명과 수량을 확인하세요."); return; }

  const data = await fetchJSON(`${API_BASE}/api/usecase1/inventory`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ site_id: activeSiteId, material_name: materialName, quantity: qty }),
  });

  renderInventory(data.inventory);
  document.getElementById("material-qty").value = "";
  document.getElementById("custom-material").value = "";
});
