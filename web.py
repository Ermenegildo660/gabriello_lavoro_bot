import os
from datetime import datetime

from flask import Flask, jsonify, render_template

from database import (
    TZ, now_it, get_work_start,
    today_records, current_session_seconds
)

PORT = int(os.getenv("PORT", "8080"))

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("ore_live.html")


@app.route("/ore-live")
def ore_live():
    return render_template("ore_live.html")


@app.route("/api/status")
def api_status():
    now = now_it()
    work_start = get_work_start()
    records_today = today_records()

    total_saved_seconds = 0
    lavori_oggi = 0
    ultimo_lavoro = ""

    for r in records_today:
        if r.get("azione") == "Sessione lavoro":
            try:
                total_saved_seconds += int(float(r.get("ore", 0)) * 3600)
            except Exception:
                pass

        if r.get("azione") == "Lavoro extra":
            lavori_oggi += 1
            ultimo_lavoro = r.get("lavoro", "")

    live_seconds = current_session_seconds()
    total_today_seconds = total_saved_seconds + live_seconds

    payload = {
        "active": bool(work_start),
        "work_start": work_start,
        "work_start_time": None,
        "work_start_ms": None,
        "server_time": now.strftime("%H:%M:%S"),
        "server_time_ms": int(now.timestamp() * 1000),
        "live_seconds": live_seconds,
        "total_today_seconds": total_today_seconds,
        "total_today_hours": round(total_today_seconds / 3600, 2),
        "lavori_oggi": lavori_oggi,
        "ultimo_lavoro": ultimo_lavoro,
    }

    if work_start:
        try:
            naive_dt = datetime.strptime(work_start, "%Y-%m-%d %H:%M:%S")
            start_dt = TZ.localize(naive_dt)
            payload["work_start_time"] = start_dt.strftime("%H:%M:%S")
            payload["work_start_ms"] = int(start_dt.timestamp() * 1000)
        except Exception:
            pass

    return jsonify(payload)


def run_web():
    app.run(host="0.0.0.0", port=PORT)
