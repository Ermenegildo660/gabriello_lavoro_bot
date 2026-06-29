let startTs = null;
let serverOffsetMs = 0;
let savedTodayMs = 0;

function pad(n){ return String(n).padStart(2, "0"); }

function formatClock(ms){
  if (ms < 0) ms = 0;
  const total = Math.floor(ms / 1000);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return `${pad(h)}:${pad(m)}:${pad(s)}`;
}

function formatHM(ms){
  if (ms < 0) ms = 0;
  const totalMin = Math.floor(ms / 60000);
  const h = Math.floor(totalMin / 60);
  const m = totalMin % 60;
  return `${h} h ${pad(m)} min`;
}

function tick(){
  if (!startTs) return;

  const now = Date.now() + serverOffsetMs;
  const liveMs = now - startTs;

  document.getElementById("timer").textContent = formatClock(liveMs);
  document.getElementById("liveHuman").textContent = formatHM(liveMs);
  document.getElementById("today").textContent = formatHM(savedTodayMs + liveMs);
}

function renderWorks(list){
  const box = document.getElementById("worksList");

  if (!list || list.length === 0) {
    box.innerHTML = `<div class="empty">Nessun lavoro registrato oggi</div>`;
    return;
  }

  box.innerHTML = list.slice().reverse().map(item => `
    <div class="work-item">
      <div class="work-time">${item.ora || "--:--"}</div>
      <div class="work-text">${escapeHtml(item.testo || "")}</div>
    </div>
  `).join("");
}

function escapeHtml(str){
  return str
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function loadStatus(manual=false){
  const btn = document.querySelector(".btn");
  if (manual && btn) btn.textContent = "Aggiorno...";

  try {
    const res = await fetch("/api/status", {cache: "no-store"});
    const data = await res.json();

    serverOffsetMs = (data.server_time_ms || Date.now()) - Date.now();

    const badge = document.getElementById("badge");
    const sub = document.getElementById("sub");

    document.getElementById("worksCount").textContent = `${data.lavori_oggi_count || 0} registrati`;
    document.getElementById("exitToday").textContent = `Uscita ${data.uscita_oggi || "--:--"}`;
    document.getElementById("entry").textContent = data.entrata_oggi || "--:--";
    document.getElementById("week").textContent = data.week_hm || "0 h 00 min";
    document.getElementById("month").textContent = data.month_hm || "0 h 00 min";

    renderWorks(data.lavori_oggi || []);

    const liveMsFromServer = (data.live_seconds || 0) * 1000;
    const todayMsFromServer = (data.today_seconds || 0) * 1000;
    savedTodayMs = Math.max(0, todayMsFromServer - liveMsFromServer);

    if (data.active) {
      startTs = data.work_start_ms;
      badge.textContent = "Al lavoro";
      badge.className = "badge";
      sub.textContent = "Cronometro in corso";
      document.getElementById("start").textContent = data.work_start_time || "--:--";
      tick();
    } else {
      startTs = null;
      badge.textContent = "Fermo";
      badge.className = "badge off";
      document.getElementById("timer").textContent = "00:00:00";
      document.getElementById("liveHuman").textContent = "0 h 00 min";
      document.getElementById("today").textContent = data.today_hm || "0 h 00 min";
      document.getElementById("start").textContent = "--:--";
      sub.textContent = "Nessun lavoro in corso";
    }

    document.getElementById("updated").textContent = "Aggiornato: " + (data.server_time || "");

    if (manual && btn) {
      btn.textContent = "Aggiornato ✔";
      setTimeout(() => btn.textContent = "Aggiorna", 1000);
    }
  } catch(e) {
    document.getElementById("sub").textContent = "Errore collegamento mini app";
    if (btn) btn.textContent = "Riprova";
  }
}

loadStatus();
setInterval(tick, 1000);
setInterval(loadStatus, 30000);
