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

  // 작업자 목록 (세로축)
  const workers = [...new Set(plan.timeline.map((x) => x.worker))];
  if (workers.length === 0) {
    // 만약 timeline에 작업자가 없으면(Fallback 등), worker_reg에서 가져오거나 해야 함
    // 하지만 보통 fallback이라도 timeline은 있으므로 넘어감
  }
  
  // 시간 슬롯 (가로축 헤더) - 백엔드와 동일하게 08:00 ~ 16:30 (30분 단위)
  const times = buildTimeSlots("08:00", "17:00"); 

  const tableContainer = document.createElement("div");
  tableContainer.className = "table-container"; // 스크롤 가능하게
  
  const table = document.createElement("table");
  table.className = "plan-grid";

  // 헤더: 시간 표시
  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");
  headerRow.innerHTML = `<th>작업자</th>${times.map((t) => `<th>${t}</th>`).join("")}`;
  thead.appendChild(headerRow);

  // 바디: 작업자별 행
  const tbody = document.createElement("tbody");
  
  // 만약 timeline에 없는 작업자라도 입력된 작업자라면 표시하고 싶다면? 
  // 일단 plan.timeline에 있는 작업자 기준.
  workers.forEach((worker) => {
    const tr = document.createElement("tr");
    const cells = [`<td style="font-weight:bold;">${worker}</td>`];
    
    times.forEach((time) => {
      // 해당 작업자 & 해당 시간의 작업 찾기 (범위 포함)
      // 시간 문자열 비교 (예: "08:30" >= "08:00" && "08:30" < "11:00")
      const block = plan.timeline.find((x) => x.worker === worker && time >= x.start && time < x.end);
      
      if (block) {
        // 시작 시간인 경우에만 텍스트 표시 (또는 매번 표시하되 스타일 조정)
        const isStart = time === block.start;
        const cellContent = isStart 
          ? `<strong>${block.area}</strong><br><span style="font-size:0.8em">${block.task}</span>` 
          : `<span style="color:#aaa; font-size:0.7em;">(계속)</span>`;
          
        cells.push(
          `<td class="task-cell" contenteditable="true" title="${block.task} (${block.start}~${block.end})">${cellContent}</td>`
        );
      } else {
        cells.push(`<td class="empty-cell" contenteditable="true"></td>`);
      }
    });
    tr.innerHTML = cells.join("");
    tbody.appendChild(tr);
  });

  table.appendChild(thead);
  table.appendChild(tbody);
  tableContainer.appendChild(table);
  timeline.appendChild(tableContainer);

  // 디버그 정보 표시
  renderDebugInfo(plan);
}

function renderDebugInfo(plan) {
  const debugContent = document.getElementById("rag-debug-content");
  if (!debugContent) return;
  
  // 중요 정보만 추출하거나 전체 표시
  const debugData = {
    scheduler_status: plan.scheduler_status,
    model: plan.model,
    rag_context: plan.rag_context, // 여기에 검색된 문서 등이 포함됨
    full_timeline: plan.timeline
  };
  
  debugContent.textContent = JSON.stringify(debugData, null, 2);
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

  // 이전 진행도 표시
  if (data.area_progress && Object.keys(data.area_progress).length > 0) {
    const progressSummary = document.getElementById("progress-summary");
    const progressDetails = document.getElementById("progress-details");
    progressDetails.innerHTML = "";

    Object.entries(data.area_progress).forEach(([area, progress]) => {
      const progressBar = document.createElement("div");
      progressBar.style.marginBottom = "8px";
      progressBar.innerHTML = `
        <div style="display:flex; justify-content: space-between; font-size: 0.9em; margin-bottom: 3px;">
          <span><strong>${area}</strong></span>
          <span>${progress}% 완료</span>
        </div>
        <div style="background:#e0e0e0; height:20px; border-radius:3px; overflow:hidden;">
          <div style="background:#4CAF50; height:100%; width:${progress}%; transition:width 0.3s;"></div>
        </div>
      `;
      progressDetails.appendChild(progressBar);
    });

    progressSummary.style.display = "block";
  } else {
    document.getElementById("progress-summary").style.display = "none";
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

  try {
    await loadSiteStatus(activeSiteId);
  } catch (error) {
    console.error("현장 정보 로딩 실패:", error);
    // 에러가 나더라도 다음 단계로 이동은 허용 (필요한 데이터가 없을 수 있음을 감안)
  }

  const section = document.getElementById("usecase2-section");
  section.classList.remove("hidden");
  section.scrollIntoView({ behavior: "smooth" });
});

document.getElementById("plan-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const submitBtn = e.target.querySelector('button[type="submit"]');
  const originalText = submitBtn.textContent;

  const selectedWorkers = [...document.querySelectorAll('#worker-checkboxes input:checked')].map(
    (input) => input.value,
  );

  if (!selectedWorkers.length) {
    alert("오늘 작업 인력을 최소 1명 선택하세요.");
    return;
  }

  // 로딩 상태 표시
  submitBtn.disabled = true;
  submitBtn.textContent = "계획 생성 중... (AI 분석 중) ⏳";

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

    renderTimeline(data.plan);

    // 작업 종료 UI 표시 로직
    const usecase3Section = document.getElementById("usecase3-section");
    const progressInputs = document.getElementById("progress-inputs");
    progressInputs.innerHTML = ""; // 이전 내용 초기화

    // 계획 생성 시 참고했던 area_progress와 전체 구역 목록을 가져옴
    const currentProgress = data.plan.rag_context.area_progress_rag || {};
    const allAreas = data.plan.rag_context.all_areas_rag || [];

    if (allAreas.length > 0) {
      allAreas.forEach(area => {
        const currentVal = Math.round(currentProgress[area] || 0);
        const div = document.createElement("div");
        // 각 구역별로 진행도를 입력할 수 있는 input 필드 생성
        div.innerHTML = `
        <label for="progress-${area}" style="display: inline-block; width: 120px;">${area}</label>
        <input type="number" id="progress-${area}" value="${currentVal}" min="0" max="100" step="1" style="width: 80px;">
        <span>%</span>
      `;
        progressInputs.appendChild(div);
      });

      // Usecase 3 섹션을 화면에 표시하고 스크롤
      usecase3Section.classList.remove("hidden");
      usecase3Section.scrollIntoView({ behavior: "smooth" });
    }
  } catch (error) {
    console.error("Plan creation failed:", error);
    alert("계획 생성에 실패했습니다. 다시 시도해주세요.");
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = originalText;
  }
});

// "최종 진행도 저장" 버튼 이벤트 리스너
document.getElementById("progress-update-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const progressInputsDiv = document.getElementById("progress-inputs");
  const inputs = progressInputsDiv.querySelectorAll('input[type="number"]');
  const areaProgress = {};

  // 각 input 필드에서 수정된 진행도 값을 읽어 areaProgress 객체 생성
  inputs.forEach(input => {
    const area = input.id.replace("progress-", "");
    areaProgress[area] = parseFloat(input.value);
  });

  // 백엔드에 area_progress 업데이트 요청
  await fetchJSON(`${API_BASE}/api/usecase3/progress`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      site_id: activeSiteId,
      area_progress: areaProgress,
    }),
  });

  alert("오늘의 최종 작업 진행도를 성공적으로 저장했습니다! 이제 내일 계획 수립 시 이 데이터가 사용됩니다.");
  document.getElementById("usecase3-section").classList.add("hidden"); // UI 숨김
});

loadMaterialOptions()
  .then(loadSites)
  .catch(() => alert("초기 데이터 로딩 실패"));
