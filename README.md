# ♟️ P2P Chess

A lightweight peer-to-peer chess game built with Python. Play locally on one machine, over a LAN, or online using a custom signaling server. Once connected, the game runs without a central server.

---

## ⚡ Quick Start (Local Test)

```bash
git clone https://github.com/Deathbringer98/P2P-Chess.git
cd P2P-Chess/Main
pip install -r requirements.txt
python P2Pchess.py
```

That’s it! You're now running P2P Chess in local test mode (no networking required).

---

## 📌 Version

**v0.7 – In Development**
- Bug fixes and UI improvements underway
- LAN multiplayer is stable
- Online multiplayer is functional but requires setup (port forwarding, etc.)
- v0.8 will simplify the connection process significantly

---

## 🚀 Features

- ✅ Peer-to-peer networking (no central server after connection)
- ✅ Host/Join using room codes
- ✅ Offline/local play (same device)
- ✅ LAN play (same Wi-Fi)
- ⚠️ Online play (requires manual setup – see below)
- 🔧 Custom signaling server (Python-based)

---

## 📦 Requirements

- Python **3.10+**
- Git (for cloning the repo)
- Optional but recommended: a Python virtual environment

---

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Deathbringer98/P2P-Chess.git
cd P2P-Chess/Main
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. (Optional) Use a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate       # macOS/Linux
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

---

## 🎮 Running the Game

### ▶️ Mode 1: Local Test (Offline Mode)

Best for testing UI and gameplay with no network setup.

```bash
python P2Pchess.py
```

You'll control both sides from one machine.

---

### 🌐 Mode 2: Multiplayer (LAN / Internet)

#### Step 1: Start the Signaling Server (Host only)

```bash
python signal_server.py
```

You should see:
```
Running on http://0.0.0.0:8080
```

> ✅ Leave this terminal open.  
> ✅ Allow Python through your firewall if prompted.

#### Step 2: Launch the Game

On both host and joiner machines:

```bash
python P2Pchess.py
```

- **Host:** Press `H` to create a room → you’ll get a **room code**.
- **Joiner:** Press `J` to join → enter the host’s IP and room code.

#### Step 3: Share Connection Info

- **Same Wi-Fi / LAN:**
  - Host shares **local IPv4 address**
    - Windows: `ipconfig`
    - Mac/Linux: `ifconfig`

- **Over Internet (different networks):**
  - Host shares **public IP address** (search *"what is my IP"*)
  - Must **port forward TCP port 8080** on router to the host’s local IP

---

## 🧰 Troubleshooting

**“Waiting for peer…” doesn’t go away**
- Ensure the `signal_server.py` is running on host
- Double-check IP and room code
- For internet play: verify port 8080 is open and forwarded

**Game connects but no board appears**
- Restart both game and signaling server
- Test first over LAN to rule out internet issues

**Firewall popup or connection refused**
- Allow Python through both **Private and Public** network firewalls

---

## 🛣️ Roadmap

| Version | Status | Highlights |
|--------|--------|------------|
| **v0.7** | ✅ In development | LAN stable, UI polish, online multiplayer testing |
| **v0.8** | 🔜 Planned | Streamlined connection flow, UX upgrades |
| **Future** | 🧪 Wishlist | `.exe` builds, platform-specific releases, pre-game lobbies & chat |

---

## 📜 License

MIT License – use it, modify it, build on it. Just credit the original author.

---

## 👤 Author

Built by [Matthew Menchinton](https://github.com/Deathbringer98)  
This is part of my portfolio, showcasing real-time peer-to-peer networking and game development in Python.
