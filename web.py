from datetime import datetime, timedelta

from flask import Flask, jsonify, render_template

from database import (
    TZ, now_it, get_work_start,
    get_records, current_session_seconds
)

app = Flask(__name__)


def seconds_to_hm(total_seconds):
    total_seconds = max(0, int(total_seconds or 0))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return f"{hours} h {minutes:02d} min"


def parse_record_datetime(data_str, ora_str):
    if not data_str or not ora_str:
        return None
    try:
        return datetime.strptime(f"{data_str} {ora_str}", "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


@app.route("/")
def home():
    return render_template("ore_live.html")


@app.route("/ore-live")
def ore_live():
    return render_template("ore_live.html")


@app.route("/api/status")
def api_status():
    now = now_it()
    today = now.strftime("%Y-%m-%d")
    week_start = (now - timedelta(days=now.weekday())).date()
    month_prefix = now.strftime("%Y-%m")

    work_start = get_work_start()
    records = get_records()

    today_saved_seconds = 0
    week_saved_seconds = 0
    month_saved_seconds = 0

    lavori_oggi = []
    ultimo_lavoro = ""

    entrata_oggi = None
    uscita_oggi = None

    for r in records:
        record_date = r.get("data", "")
        azione = r.get("azione", "")

        if azione == "Sessione lavoro":
            try:
                seconds = int(float(r.get("ore", 0)) * 3600)
            except Exception:
                seconds = 0

            if record_date == today:
                today_saved_seconds += seconds

            try:
                rec_date_obj = datetime.strptime(record_date, "%Y-%m-%d").date()
                if rec_date_obj >= week_start:
                    week_saved_seconds += seconds
            except Exception:
                pass

            if record_date.startswith(month_prefix):
                month_saved_seconds += seconds

        if record_date == today and azione == "Lavoro extra":
            lavoro = r.get("lavoro", "")
            ora = r.get("inizio", "")
            if lavoro:
                lavori_oggi.append({
                    "ora": ora,
                    "testo": lavoro
                })
                ultimo_lavoro = lavoro

        if record_date == today and azione == "Entrata":
            dt = parse_record_datetime(record_date, r.get("inizio", ""))
            if dt and (entrata_oggi is None or dt < entrata_oggi):
                entrata_oggi = dt

        if record_date == today and azione == "Uscita":
            dt = parse_record_datetime(record_date, r.get("fine", ""))
            if dt and (uscita_oggi is None or dt > uscita_oggi):
                uscita_oggi = dt

    live_seconds = current_session_seconds()

    total_today_seconds = today_saved_seconds + live_seconds
    total_week_seconds = week_saved_seconds + live_seconds
    total_month_seconds = month_saved_seconds + live_seconds

    payload = {
        "active": bool(work_start),
        "work_start": work_start,
        "work_start_time": None,
        "work_start_ms": None,

        "server_time": now.strftime("%H:%M:%S"),
        "server_time_ms": int(now.timestamp() * 1000),

        "live_seconds": live_seconds,
        "today_saved_seconds": today_saved_seconds,

        "today_seconds": total_today_seconds,
        "week_seconds": total_week_seconds,
        "month_seconds": total_month_seconds,

        "today_hm": seconds_to_hm(total_today_seconds),
        "week_hm": seconds_to_hm(total_week_seconds),
        "month_hm": seconds_to_hm(total_month_seconds),

        "lavori_oggi_count": len(lavori_oggi),
        "lavori_oggi": lavori_oggi[-8:],
        "ultimo_lavoro": ultimo_lavoro,

        "entrata_oggi": entrata_oggi.strftime("%H:%M:%S") if entrata_oggi else "--:--",
        "uscita_oggi": uscita_oggi.strftime("%H:%M:%S") if uscita_oggi else "--:--",
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
    import os
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
