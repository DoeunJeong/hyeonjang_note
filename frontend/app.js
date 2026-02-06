const API_BASE = "http://localhost:8000";

function parseCSV(value) {
  return value
    .split(",")
    .map((v) => v.trim())
    .filter(Boolean);
}

function renderTimeline(plan) {
  const timeline = document.getElementById("timeline");
  timeline.innerHTML = "";

  const workers = [...new Set(plan.timeline.map((x) => x.worker))];
  const times = [];
  for (let h = 8; h < 17; h++) {
    times.push(`${String(h).padStart(2, "0")}:00`);
    times.push(`${String(h).padStart(2, "0")}:30`);
  }

  workers.forEach((worker) => {
    const row = document.createElement("div");
    row.className = "timeline-row";

    const nameCell = document.createElement("span");
    nameCell.textContent = worker;
    row.appendChild(nameCell);

    times.forEach((time) => {
      const cell = document.createElement("span");
      const block = plan.timeline.find((x) => x.worker === worker && x.start === time);
      if (block) {
        cell.className = "task-cell";
        cell.contentEditable = "true";
        cell.textContent = `${block.area} / ${block.task}`;
      }
      row.appendChild(cell);
    });
    timeline.appendChild(row);
  });
}

document.getElementById("plan-form").addEventListener("submit", async (e) => {
  e.preventDefault();

  let incomingMaterials = {};
  const incomingRaw = document.getElementById("incoming").value.trim();
  if (incomingRaw) {
    try {
      incomingMaterials = JSON.parse(incomingRaw);
    } catch {
      alert("입고 자재 JSON 형식이 올바르지 않습니다.");
      return;
    }
  }

  const payload = {
    selected_workers: parseCSV(document.getElementById("workers").value),
    incoming_materials: incomingMaterials,
    priority_areas: parseCSV(document.getElementById("areas").value),
    weather_summary: document.getElementById("weather").value.trim() || null,
  };

  const res = await fetch(`${API_BASE}/api/usecase2/plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    alert("계획 생성 실패");
    return;
  }

  const data = await res.json();
  renderTimeline(data.plan);
});
