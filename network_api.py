import eventlet
eventlet.monkey_patch()

from flask import Flask
from flask_socketio import SocketIO
import psutil
import datetime
from collections import deque


app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")


# ==============================
# CONFIG
# ==============================
REFRESH_SECONDS = 1
HISTORY_MINUTES = 30
MAX_POINTS = int((HISTORY_MINUTES * 60) / REFRESH_SECONDS)

COLOR_DOWN = "#00e5ff"
COLOR_UP = "#ffcc00"


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
# HISTORY
# ==============================
down_hist = deque(maxlen=MAX_POINTS)
up_hist = deque(maxlen=MAX_POINTS)
time_hist = deque(maxlen=MAX_POINTS)

last = psutil.net_io_counters(pernic=True)[INTERFACE]


# ==============================
# SPEED CALC
# ==============================
def get_speed():
    global last

    current = psutil.net_io_counters(pernic=True)[INTERFACE]

    down_bytes = current.bytes_recv - last.bytes_recv
    up_bytes = current.bytes_sent - last.bytes_sent

    last = current

    down = (down_bytes * 8) / (1024 * 1024) / REFRESH_SECONDS
    up = (up_bytes * 8) / (1024 * 1024) / REFRESH_SECONDS

    return round(down, 2), round(up, 2)


# ==============================
# SEND FULL HISTORY ON CONNECT
# ==============================
@socketio.on("connect")
def send_history():
    socketio.emit("history", {
        "times": list(time_hist),
        "down": list(down_hist),
        "up": list(up_hist)
    })


# ==============================
# BACKGROUND STREAM LOOP
# ==============================
def background_thread():
    while True:
        down, up = get_speed()
        now = datetime.datetime.now().strftime("%H:%M")

        down_hist.append(down)
        up_hist.append(up)
        time_hist.append(now)

        socketio.emit("net_update", {
            "down": down,
            "up": up,
            "time": now,
            "peak_down": max(down_hist),
            "peak_up": max(up_hist),
        })

        socketio.sleep(REFRESH_SECONDS)


# ==============================
# ROUTE
# ==============================
@app.route("/")
def index():
    return f"""
<html>
<head>

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
    opacity:0.8;
    margin-bottom:6px;
    line-height: 1.4em;
}}

canvas {{
    width:100% !important;
    height:260px !important;
}}

/* Hover overlay */
.overlay {{
    position: absolute;
    pointer-events: none;
    background: rgba(20,20,20,0.9);
    border: 1px solid rgba(255,255,255,0.1);
    padding: 6px 10px;
    border-radius: 8px;
    font-size: 12px;
    color: #fff;
    display: none;
    backdrop-filter: blur(6px);
}}
</style>

</head>
<body>

<div class="header" id="stats">
Interface: {INTERFACE}<br>
Waiting for data...
</div>

<div id="overlay" class="overlay"></div>

<canvas id="chart"></canvas>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>

<script>
const MAX_POINTS = {MAX_POINTS};

const labels = [];
const downData = [];
const upData = [];

const overlay = document.getElementById("overlay");

const ctx = document.getElementById('chart');

const chart = new Chart(ctx, {{
  type: 'line',
  data: {{
    labels: labels,
    datasets: [
      {{
        label: 'Download',
        data: downData,
        borderColor: '{COLOR_DOWN}',
        backgroundColor: '{COLOR_DOWN}22',
        fill: true,
        tension: 0.35,
        pointRadius: 0
      }},
      {{
        label: 'Upload',
        data: upData,
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
    animation: false,
    interaction: {{
      mode: 'index',
      intersect: false
    }},
    plugins: {{
      tooltip: {{ enabled: false }}
    }},
    onHover: (e, elements) => {{
        if (!elements.length) {{
            overlay.style.display = "none";
            return;
        }}

        const i = elements[0].index;

        overlay.style.display = "block";
        overlay.style.left = (e.x + 15) + "px";
        overlay.style.top = (e.y + 15) + "px";

        overlay.innerHTML =
            `Time: ${{labels[i]}}<br>` +
            `↓ ${{downData[i]}} Mbps<br>` +
            `↑ ${{upData[i]}} Mbps`;
    }},
    scales: {{
      x: {{
        ticks: {{ maxTicksLimit: 8 }}
      }},
      y: {{
        beginAtZero: true
      }}
    }}
  }}
}});


// ==============================
// SOCKET
// ==============================
const socket = io();

socket.on("history", data => {{
    labels.push(...data.times);
    downData.push(...data.down);
    upData.push(...data.up);
    chart.update();
}});

socket.on("net_update", (data) => {{

    labels.push(data.time);
    downData.push(data.down);
    upData.push(data.up);

    if (labels.length > MAX_POINTS) {{
        labels.shift();
        downData.shift();
        upData.shift();
    }}

    document.getElementById("stats").innerHTML =
        `Interface: {INTERFACE}<br>` +
        `↓ ${{data.down}} Mbps (peak ${{data.peak_down}}) &nbsp;&nbsp; ↑ ${{data.up}} Mbps (peak ${{data.peak_up}})`;

    chart.update();
}});
</script>

</body>
</html>
"""


# ==============================
# MAIN
# ==============================
if __name__ == "__main__":
    socketio.start_background_task(background_thread)

    print(f"Starting network monitor on http://0.0.0.0:2016  (iface={INTERFACE})")

    socketio.run(app, host="0.0.0.0", port=2016)
