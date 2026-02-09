# 🌡️ Speedforce Temp API

A lightweight Flask API that bridges network data to Dashy widgets.

## 📋 Prerequisites
Ensure your Linux environment has the necessary tools:
* **Python 3 & Pip**

## 🚀 Quick Start
1. **Install Dependencies**:
   ```bash
    sudo apt update && sudo apt install python3-venv -y

1. **Create the environment (folder named 'venv')**:
   ```bash
    python3 -m venv venv
   ````

1. **Activate the environment**:
   ```bash
    source venv/bin/activate
   ````

1. **Install flask**:
   ```bash
    pip install psutil
   ````

1. **Run the app**:
   ```bash
    python3 network_api.py
   ````

1. **Access it from**:
   ```bash
    http://192.168.1.20:2016
   ````

## ⚙️ Deployment (Systemd)
To ensure the API runs 24/7 and starts on boot:

1. Create `network_api.service` in `/etc/systemd/system/`:
    ````bash
    sudo nano /etc/systemd/system/network_api.service
    ````

2. Add
    ````bash
    [Unit]
    Description=Speedforce Network API for Dashy
    After=network.target
 
    [Service]
    User=kikchan
    WorkingDirectory=/home/kikchan/Metalforce/net-api
    ExecStart=/home/kikchan/Metalforce/net-api/venv/bin/python network_api.py
    Restart=always
    RestartSec=5
 
    [Install]
    WantedBy=multi-user.target
    ````

3. Run:
    ````bash
    sudo systemctl daemon-reload
    sudo systemctl enable network_api.service
    sudo systemctl start network_api.service
    ````

## 📊 Dashy Config
Add this to your `conf.yml`:
````bash
  - name: Network
    icon: fas fa-network-wired
    widgets:
      - type: embed
        options:
          html: |
            <p align="center">
                <iframe src="http://192.168.1.20:2016" 
                 frameborder='0' 
                 scrolling="no" 
                 style="overflow: hidden; height: 320px; width: 100%"
                />
            </p>
        id: 0_746_embed
    displayData:
      sortBy: default
      rows: 1
      cols: 4
      collapsed: false
      hideForGuests: false
````