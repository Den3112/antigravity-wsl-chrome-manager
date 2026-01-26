# Antigravity WSL Chrome Manager (Pro Architecture)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![WSL2](https://img.shields.io/badge/Platform-WSL2-blue.svg)](https://docs.microsoft.com/en-us/windows/wsl/about)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)

Zero-conflict, high-performance solution for running Google Chrome with remote debugging in a WSL 2 environment. Featuring **Smart Socket Activation** and **Automatic GPU Acceleration**.

---

## 🚀 Key Advantages

*   **⚡ Smart Activation:** Chrome launches *instantly* when your tools connect to port 9222. No manual start required.
*   **🎮 GPU Accelerated:** Pre-configured for WSLg/D3D12 hardware acceleration. No lagging UI.
*   **🔋 Resource Efficient:** Background proxy uses `< 15MB` RAM. Chrome closes when you finish.
*   **🛡️ Multi-Instance Safe:** Distributed locking prevents port conflicts and duplicate browser processes.
*   **🧩 Tool Compatibility:** Perfect for Playwright, Puppeteer, Selenium, and IDE Debuggers.

---

## 🏗️ Architecture Overview

The system uses a **Smart Proxy (middleware)** approach. Instead of running Chrome directly, your tools talk to a Python-based listener that manages the browser lifecycle.

| Component | Responsibility |
| :--- | :--- |
| **Smart Proxy** | Listens on port 9222, detects connections, and manages startup. |
| **Launch Script** | Handles Chrome flags, profiles, and GPU environment variables. |
| **chrome-ctl** | CLI utility for monitoring status, logs, and manual control. |

> [!TIP]
> **Why is this better?** Traditional scripts either keep Chrome running forever (wasting RAM) or fail to start when tools connect. Our proxy ensures "It Just Works".

---

## 🛠️ Solutions

We offer two optimized paths depending on your workflow:

### 1. [Native WSL Chrome](./solution-1-native-chrome/) (Recommended)
Chrome runs directly inside Linux. Best for pure Linux performance and seamless file system access.
*   **Setup:** `cd solution-1-native-chrome && ./setup.sh`

### 2. [Windows Bridge](./solution-2-windows-bridge/)
WSL tools communicate with Chrome running in Windows. Best if you prefer to see the browser window outside the WSLg sandbox.
*   **Setup:** `cd solution-2-windows-bridge && ./setup.sh`

---

## 📖 Table of Contents

- [Architecture & Design Details](./docs/wiki/Architecture.md)
- [Deployment Guide](./solution-1-native-chrome/#-quick-installation)
- [Usage & CLI Reference](./solution-1-native-chrome/#manual-control)
- [Troubleshooting & FAQ](./FAQ.md)
- [Contributing Guidelines](./CONTRIBUTING.md)

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.

---

<p align="center">
  Generated with ❤️ by <b>Antigravity</b>
</p>
