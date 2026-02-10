const API_BASE = "http://localhost:8000";
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
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(`요청 실패: ${res.status}`);
  return res.json();
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
    renderProgress(data.overall_progress || 0, data.area_progress_details || []);
    
    if (data.priority_areas?.length) {
      document.getElementById("areas").value = data.priority_areas.join(",");
    }

    if (data.plan && data.plan.timeline) {
      currentPlan = data.plan;
      renderTimeline(data.plan);
      initWorkChecklist(data.plan.timeline);
      
      const timelineContainer = document.getElementById("timeline-container");
      timelineContainer.classList.remove("hidden");
      timelineContainer.scrollIntoView({ behavior: "smooth" });
    }
    
  } catch (error) {
    console.error(error);
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

// 버튼 클릭 이벤트로 변경
document.getElementById("generate-plan-btn").addEventListener("click", async () => {
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
    };

    const data = await fetchJSON(`${API_BASE}/api/usecase2/plan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    console.log("Plan created:", data); // 디버그용 로그 추가

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

function renderTimeline(plan) {
    if (!plan || !plan.timeline) {
        console.warn("타임라인 렌더링 스킵: 플랜 또는 타임라인 데이터 없음");
        return;
    }

    const timelineDiv = document.getElementById("timeline");
    if (!timelineDiv) return;
    
    timelineDiv.innerHTML = ""; // 이전 내용 지우기

    const timeline = plan.timeline || [];

    // 타임라인 테이블 생성
    const tableHtml = `
        <div class="table-container" style="margin-top: 20px;">
            <table class="plan-table">
                <thead>
                    <tr>
                        <th style="width: 120px;">시간</th>
                        <th style="width: 150px;">구역</th>
                        <th style="width: 150px;">담당 작업자</th>
                        <th>상세 작업 내용</th>
                    </tr>
                </thead>
                <tbody>
                    ${timeline.map(item => {
                        const workerDisplay = Array.isArray(item.workers) ? item.workers.join(", ") : (item.worker || "미정");
                        const timeDisplay = item.time || `${item.start} ~ ${item.end}`;
                        return `
                            <tr>
                                <td class="text-center">${timeDisplay}</td>
                                <td class="text-center"><strong>${item.area || "-"}</strong></td>
                                <td class="text-center">${workerDisplay}</td>
                                <td>${item.task}</td>
                            </tr>
                        `;
                    }).join("")}
                </tbody>
            </table>
        </div>`;

    timelineDiv.innerHTML = tableHtml;
    document.getElementById("timeline-container").classList.remove("hidden");
}

// --- 3. 작업 마감 ---
function initWorkChecklist(timeline) {
  const body = document.getElementById("closing-table-body");
  const editWorkerSelect = document.getElementById("edit-worker");
  if (!body || !editWorkerSelect) return;
  
  body.innerHTML = "";
  workItems = [];

  // 작업자 목록 (추가 작업용)
  const allWorkers = new Set();
  timeline.forEach(item => {
    if (Array.isArray(item.workers)) {
      item.workers.forEach(w => allWorkers.add(w));
    } else if (item.worker) {
      allWorkers.add(item.worker);
    }
  });

  editWorkerSelect.innerHTML = `<option value="">작업자</option>`;
  [...allWorkers].sort().forEach(w => {
    const opt = document.createElement("option");
    opt.value = w;
    opt.textContent = w;
    editWorkerSelect.appendChild(opt);
  });

  timeline.forEach((item, idx) => {
    const id = `work-${idx}`;
    const workerDisplay = Array.isArray(item.workers) ? item.workers.join(", ") : (item.worker || "미정");
    const workItem = {
      id,
      worker: workerDisplay,
      start: item.start || "",
      end: item.end || "",
      area: item.area || "",
      task: item.task || "",
      completed: false,
      note: ""
    };
    workItems.push(workItem);
    addWorkRow(workItem);
  });
}

function addWorkRow(item) {
  const body = document.getElementById("closing-table-body");
  const tr = document.createElement("tr");
  tr.id = `row-${item.id}`;
  tr.innerHTML = `
    <td>${item.worker}</td>
    <td>${item.start}~${item.end}</td>
    <td>${item.area}</td>
    <td>${item.task}</td>
    <td><input type="checkbox" ${item.completed ? "checked" : ""} onchange="updateWorkStatus('${item.id}', this.checked)"></td>
    <td><input type="text" class="small-input" value="${item.note || ""}" onchange="updateWorkNote('${item.id}', this.value)"></td>
    <td><button class="btn-danger btn-sm" onclick="removeWorkItem('${item.id}')">✕</button></td>
  `;
  body.appendChild(tr);
}

window.updateWorkStatus = (id, checked) => {
  const item = workItems.find(i => i.id === id);
  if (item) item.completed = checked;
};

window.updateWorkNote = (id, value) => {
  const item = workItems.find(i => i.id === id);
  if (item) item.note = value;
};

window.removeWorkItem = (id) => {
  workItems = workItems.filter(i => i.id !== id);
  const row = document.getElementById(`row-${id}`);
  if (row) row.remove();
};

document.getElementById("add-work-item-btn").addEventListener("click", () => {
  const worker = document.getElementById("edit-worker").value;
  const start = document.getElementById("edit-start").value || "08:00";
  const end = document.getElementById("edit-end").value || "17:00";
  const area = document.getElementById("edit-area").value;
  const task = document.getElementById("edit-task").value;

  if (!worker || !area || !task) {
    alert("작업자, 구역, 작업내용을 모두 입력하세요.");
    return;
  }

  const id = `extra-${Date.now()}`;
  const newItem = { id, worker, start, end, area, task, completed: true, note: "추가작업" };
  workItems.push(newItem);
  addWorkRow(newItem);

  // 초기화
  document.getElementById("edit-task").value = "";
});

document.getElementById("save-work-result-btn").addEventListener("click", async () => {
  if (!activeSiteId) return;
  
  const payload = {
    site_id: activeSiteId,
    date: new Date().toISOString().split("T")[0],
    actual_work: workItems
  };

  try {
    await fetchJSON(`${API_BASE}/api/usecase3/work-result`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    alert("오늘의 작업 일지가 성공적으로 저장되었습니다.");
  } catch (error) {
    alert("저장 실패: " + error.message);
  }
});

document.getElementById("download-manpower-btn").addEventListener("click", () => {
  if (!activeSiteId) { alert("현장을 먼저 선택하세요."); return; }
  window.location.href = `${API_BASE}/api/usecase3/manpower-log?site_id=${encodeURIComponent(activeSiteId)}`;
});

document.getElementById("download-report-btn").addEventListener("click", () => {
  if (!activeSiteId) { alert("현장을 먼저 선택하세요."); return; }
  const date = new Date().toISOString().split("T")[0];
  window.location.href = `${API_BASE}/api/usecase3/daily-report?site_id=${encodeURIComponent(activeSiteId)}&date=${date}`;
});

function renderProgress(overallProgress, areaDetails) {
  // 전체 진척률 업데이트
  const overallPercent = document.getElementById("overall-percent");
  const overallBar = document.getElementById("overall-bar");
  
  if (overallPercent && overallBar) {
    overallPercent.textContent = `${overallProgress}%`;
    overallBar.style.width = `${overallProgress}%`;
  }

  // 구역별 진척률 업데이트
  const areaList = document.getElementById("area-progress-list");
  if (areaList) {
    areaList.innerHTML = "";
    areaDetails.forEach(area => {
      const item = document.createElement("div");
      item.className = "area-progress-item";
      item.innerHTML = `
        <span class="area-name">${area.name} <span class="progress-percent">${area.progress}%</span></span>
        <div class="area-bar-bg">
          <div class="area-bar-fill" style="width: ${area.progress}%;"></div>
        </div>
      `;
      areaList.appendChild(item);
    });
  }
}

