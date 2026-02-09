from flask import Flask
import psutil
import time
from collections import deque
import datetime

app = Flask(__name__)

# ==============================
# CONFIG
# ==============================
REFRESH_SECONDS = 5
HISTORY_MINUTES = 60  # 1 hour
MAX_POINTS = int((HISTORY_MINUTES * 60) / REFRESH_SECONDS)

# Dashy-friendly colors
COLOR_DOWN = "#00e5ff"   # cyan
COLOR_UP = "#ffcc00"     # yellow


# ==============================
# AUTO DETECT INTERFACE
# ==============================
def detect_interface():
    stats = psutil.net_if_stats()
    for name, s in stats.items():
        if s.isup and not name.startswith(("lo", "docker", "veth", "br-", "tun")):
            return name
    return list(stats.keys())[0]


INTERFACE = detect_interface()


# ==============================
# HISTORY BUFFERS
# ==============================
down_hist = deque(maxlen=MAX_POINTS)
up_hist = deque(maxlen=MAX_POINTS)
time_hist = deque(maxlen=MAX_POINTS)

last = psutil.net_io_counters(pernic=True)[INTERFACE]


# ==============================
# SPEED CALC (Mbps)
# ==============================
def get_speed():
    global last

    current = psutil.net_io_counters(pernic=True)[INTERFACE]

    down_bytes = current.bytes_recv - last.bytes_recv
    up_bytes = current.bytes_sent - last.bytes_sent

    last = current

    # convert → Mbps
    down = (down_bytes * 8) / (1024 * 1024) / REFRESH_SECONDS
    up = (up_bytes * 8) / (1024 * 1024) / REFRESH_SECONDS

    return round(down, 2), round(up, 2)


# ==============================
# ROUTE
# ==============================
@app.route("/")
def index():
    down, up = get_speed()

    now = datetime.datetime.now().strftime("%H:%M")

    down_hist.append(down)
    up_hist.append(up)
    time_hist.append(now)

    peak_down = max(down_hist) if down_hist else 0
    peak_up = max(up_hist) if up_hist else 0

    return f"""
<html>
<head>
<meta http-equiv="refresh" content="{REFRESH_SECONDS}">

<style>
body {{
    background: transparent;
    color: #eee;
    font-family: system-ui, sans-serif;
    margin: 0;
    padding: 8px;
}}

.header {{
    text-align:center;
    font-size:13px;
    opacity:0.75;
    margin-bottom:6px;
}}

canvas {{
    width: 100% !important;
    height: 260px !important;
}}
</style>
</head>

<body>

<div class="header">
Interface: {INTERFACE} &nbsp;&nbsp;
↓ {down} Mbps (peak {peak_down}) &nbsp;&nbsp;
↑ {up} Mbps (peak {peak_up})
</div>

<canvas id="chart"></canvas>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<script>
const ctx = document.getElementById('chart');

new Chart(ctx, {{
  type: 'line',
  data: {{
    labels: {list(time_hist)},
    datasets: [
      {{
        label: 'Download (Mbps)',
        data: {list(down_hist)},
        borderColor: '{COLOR_DOWN}',
        backgroundColor: '{COLOR_DOWN}22',
        fill: true,
        tension: 0.35,
        pointRadius: 0
      }},
      {{
        label: 'Upload (Mbps)',
        data: {list(up_hist)},
        borderColor: '{COLOR_UP}',
        backgroundColor: '{COLOR_UP}22',
        fill: true,
        tension: 0.35,
        pointRadius: 0
      }}
    ]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,

    interaction: {{
      mode: 'index',
      intersect: false
    }},

    plugins: {{
      legend: {{
        labels: {{
          color: '#aaa'
        }}
      }},
      tooltip: {{
        enabled: true
      }}
    }},

    scales: {{
      x: {{
        ticks: {{
          color: '#777',
          maxTicksLimit: 8
        }},
        grid: {{
          color: 'rgba(255,255,255,0.05)'
        }}
      }},
      y: {{
        beginAtZero: true,
        ticks: {{
          color: '#aaa'
        }},
        grid: {{
          color: 'rgba(255,255,255,0.08)'
        }}
      }}
    }}
  }}
}});
</script>

</body>
</html>
"""


# ==============================
# MAIN
# ==============================
if __name__ == "__main__":
    print(f"Starting network monitor on http://0.0.0.0:2015  (iface={INTERFACE})")
    app.run(host="0.0.0.0", port=2016)
