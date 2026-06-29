let startTs = null;
let serverOffsetMs = 0;
let totalSavedTodayMs = 0;

function pad(n){ return String(n).padStart(2, "0"); }

function formatDuration(ms){
  if (ms < 0) ms = 0;
  const total = Math.floor(ms / 1000);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return `${pad(h)}:${pad(m)}:${pad(s)}`;
}

function tick(){
  if (!startTs) return;

  const now = Date.now() + serverOffsetMs;
  const liveDiff = now - startTs;

  document.getElementById("timer").textContent = formatDuration(liveDiff);
  document.getElementById("decimal").textContent = (liveDiff / 3600000).toFixed(2) + " h";
  document.getElementById("today").textContent = ((totalSavedTodayMs + liveDiff) / 3600000).toFixed(2) + " h";
}

async function loadStatus(){
  try {
    const res = await fetch("/api/status", {cache: "no-store"});
    const data = await res.json();

    serverOffsetMs = (data.server_time_ms || Date.now()) - Date.now();

    const badge = document.getElementById("badge");
    const sub = document.getElementById("sub");

    totalSavedTodayMs = Math.max(0, ((data.total_today_seconds || 0) - (data.live_seconds || 0)) * 1000);

    document.getElementById("works").textContent = data.lavori_oggi || 0;
    document.getElementById("lastWork").textContent = data.ultimo_lavoro || "—";

    if (data.active) {
      startTs = data.work_start_ms;
      badge.textContent = "Al lavoro";
      badge.className = "badge";
      sub.textContent = "Cronometro in corso";
      document.getElementById("start").textContent = data.work_start_time || "--:--:--";
      tick();
    } else {
      startTs = null;
      badge.textContent = "Fermo";
      badge.className = "badge off";
      document.getElementById("timer").textContent = "00:00:00";
      document.getElementById("decimal").textContent = "0.00 h";
      document.getElementById("today").textContent = (data.total_today_hours || 0).toFixed(2) + " h";
      document.getElementById("start").textContent = "--:--:--";
      sub.textContent = "Nessun lavoro in corso";
    }

    document.getElementById("updated").textContent = "Aggiornato: " + (data.server_time || "");
  } catch(e) {
    document.getElementById("sub").textContent = "Errore collegamento mini app";
  }
}

loadStatus();
setInterval(tick, 1000);
setInterval(loadStatus, 30000);
