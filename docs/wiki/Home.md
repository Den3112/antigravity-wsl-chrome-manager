# Welcome to the Antigravity WSL Chrome Manager Wiki!

This repository provides robust solutions for running Google Chrome in Windows Subsystem for Linux (WSL), specifically tailored for automation agents like **Antigravity**, **Playwright**, and **Puppeteer**.

## 🌟 Key Features
*   **Zero-Config Start:** Just run the script, and it works.
*   **Smart Socket Activation:** Chrome launches only when you try to use it.
*   **Crash Recovery:** Integrated automatic handling of zombie processes.
*   **High DPI Support:** Optimized for 4K monitors on Windows.

## 📚 Documentation Sections

### [Getting Started](Getting-Started)
Learn how to install and run the bridge in 5 minutes.

### [Architecture & Design](Architecture-and-Design)
Deep dive into the **Smart Proxy** logic, concurrency management, and "Socket Activation" pattern.

### [Troubleshooting](Troubleshooting)
Common error messages (`ECONNREFUSED`, `DevToolsActivePort file doesn't exist`) and how to fix them.

### [Manual vs Automatic](Manual-vs-Automatic)
Understand the difference between controlling Chrome via `chrome-ctl` and relying on the Smart Proxy.
