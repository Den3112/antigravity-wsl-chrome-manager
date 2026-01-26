# WSL-Chrome-Bridge 🚀

[![Security & Linting](https://github.com/Den3112/antigravity-wsl-chrome-manager/actions/workflows/verify.yml/badge.svg)](https://github.com/Den3112/antigravity-wsl-chrome-manager/actions/workflows/verify.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Bypass Firewall & Antivirus blocks** — Connect WSL 2 to Windows Chrome DevTools Protocol (CDP) seamlessly.

A robust solution to connect WSL 2 applications (**Puppeteer**, **Playwright**, **Selenium**, **AI Browser Agents**) to a Google Chrome instance running on Windows, even when blocked by strict local Firewalls or Antiviruses (like **Bitdefender**, **Kaspersky**, **Norton**, **ESET**, etc.).

## 🎯 Keywords & Use Cases
`WSL2` `Chrome DevTools Protocol` `CDP` `Puppeteer` `Playwright` `Selenium` `Browser Automation` `AI Agents` `ECONNREFUSED` `Bitdefender` `Firewall Bypass` `Port Forwarding`

---

## 📖 The Problem
In WSL 2, connecting to the Windows host's Chrome DevTools Protocol (CDP) port (default `9222`) often fails with:
- `ECONNREFUSED 127.0.0.1:9222`
- `Timeout`
- `Connection reset`

**Why does this happen?**
1. **NAT Networking:** WSL 2 uses NAT by default, meaning `localhost` in WSL is not `localhost` on Windows.
2. **Security Software:** Strict Firewalls and Antiviruses (Bitdefender, Kaspersky, Norton, ESET) block inbound cross-network traffic to Chrome's debugging port.

---

## ✨ The Solution
This bridge uses a **dual-proxy architecture**:

```
┌─────────────────────────────────────────────────────────────┐
│                        WINDOWS                              │
│  Chrome (127.0.0.1:9222) ◄── Python Proxy (0.0.0.0:9223)   │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ TCP
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                          WSL 2                              │
│  Socat (127.0.0.1:9222) ──► Windows IP:9223                │
│  google-chrome shim ──► start_bridge.sh                    │
└─────────────────────────────────────────────────────────────┘
```

- **Windows Python Proxy:** Listens on all interfaces (`0.0.0.0:9223`) and forwards to Chrome's local port (`9222`). Python is trusted by most AVs.
- **WSL Socat Forwarder:** Maps `127.0.0.1:9222` inside WSL to Windows proxy port.
- **Chrome Shim:** A drop-in replacement that tricks Puppeteer/Playwright/Agents into thinking Chrome is running natively in Linux.

---

## 🛠 Installation & Setup

### Prerequisites
- Windows 10/11 with WSL 2 enabled
- Python 3.x installed on Windows
- Google Chrome installed on Windows
- `socat` package in WSL (`sudo apt install socat`)

### 1. Windows Preparation
1. Copy `windows/wsl_chrome_proxy.py` to a location (e.g., `C:\tools\`).
2. Create a batch file to launch Chrome with debugging enabled:
   ```batch
   "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir="C:\temp\chrome-debug"
   ```

### 2. WSL Setup
```bash
git clone https://github.com/Den3112/antigravity-wsl-chrome-manager.git
cd antigravity-wsl-chrome-manager
chmod +x setup.sh
./setup.sh
```

This creates a `google-chrome` command in WSL that automatically manages the bridge.

---

## 🚀 Usage

### Quick Start
```bash
# Verify the bridge is working
google-chrome --version

# Or run manually
./wsl/start_bridge.sh
```

### With Puppeteer
```javascript
const browser = await puppeteer.connect({
  browserURL: 'http://127.0.0.1:9222'
});
```

### With Playwright
```javascript
const browser = await chromium.connectOverCDP('http://127.0.0.1:9222');
```

---

## 🛡️ Security & Transparency

> **This project is 100% open-source and safe.**

| Component | Function | Safe? |
|-----------|----------|-------|
| `wsl_chrome_proxy.py` | TCP forwarder (9223 → 9222) | ✅ No logging, no internet |
| `socat` | Standard Linux networking tool | ✅ Trusted utility |
| `google_chrome_shim` | Bash wrapper script | ✅ Plain text, auditable |

**Why it's safe:**
- **No compiled binaries** — everything is plain-text and auditable
- **No root/admin required** for daily use
- **No data collection** — we don't phone home

---

## 🔍 Troubleshooting

| Issue | Solution |
|-------|----------|
| `ECONNREFUSED` | Ensure Python proxy is running on Windows (port 9223) |
| `Timeout` | Check if your AV is blocking `python.exe` |
| `Path errors` | Update `WINDOWS_PROXY_PATH` in `start_bridge.sh` |

📚 See the [Wiki](https://github.com/Den3112/antigravity-wsl-chrome-manager/wiki) for detailed documentation.

💬 Join the [Discussions](https://github.com/Den3112/antigravity-wsl-chrome-manager/discussions) to ask questions or share your setup!

---

## 🤝 Contributing
Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License
MIT © 2026
