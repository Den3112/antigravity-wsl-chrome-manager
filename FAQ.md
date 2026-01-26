# Frequently Asked Questions (FAQ)

## General Questions

### Q: Which solution should I use?

**A:** Here's a quick decision tree:

```
Do you have strict firewall/antivirus (Bitdefender, Kaspersky, Norton)?
├─ YES → Use Solution 2 (Windows Bridge)
└─ NO  → Do you prefer simplicity?
    ├─ YES → Use Solution 1 (Native Chrome) ⭐ Recommended
    └─ NO  → Use Solution 2 if you want Windows Chrome
```

### Q: Can I use both solutions?

**A:** Not simultaneously (they both use port 9222). However, you can:
1. Install both
2. Switch between them as needed
3. Stop one before starting the other

### Q: Do these work with tools other than Antigravity?

**A:** Yes! Both solutions work with:
- ✅ Antigravity
- ✅ Playwright
- ✅ Puppeteer
- ✅ Selenium
- ✅ Any tool that uses Chrome DevTools Protocol (CDP)

### Q: Is this safe?

**A:** Yes, both solutions are 100% open-source:
- ✅ No compiled binaries
- ✅ No data collection
- ✅ No phone-home functionality
- ✅ Fully auditable code

---

## Solution 1 (Native Chrome) Questions

### Q: Why does Chrome run with `--no-sandbox`?

**A:** WSL doesn't support Chrome's sandboxing. This is safe in WSL because:
- WSL itself is sandboxed
- You're not exposing Chrome to the internet
- This is standard practice for Chrome in Docker/WSL

### Q: How much memory does this use?

**A:** 
- Chrome: ~200-500MB (similar to normal Chrome)
- Watchdog: ~5MB (minimal bash script)

### Q: Can I disable the watchdog?

**A:** Yes:
```bash
# Stop watchdog
~/chrome-ctl stop

# Remove from .bashrc
# Comment out the "Antigravity Chrome Auto-start" section
```

### Q: Will this start Chrome on every terminal window?

**A:** No, the watchdog only starts ONE instance:
- Uses PID file to prevent duplicates
- Multiple terminals share the same watchdog
- Safe to open many terminals

### Q: Can I use a different Chrome port?

**A:** Yes, but you'll need to edit:
- `ensure_chrome_running.sh` (change PORT=9222)
- `chrome_watchdog.sh` (change PORT=9222)
- Your automation tools (connect to new port)

### Q: What if I already have Chrome running?

**A:** The scripts detect existing Chrome instances:
- If Chrome on :9222 is responsive → uses it
- If not → starts new instance

---

## Solution 2 (Windows Bridge) Questions

### Q: Why do I need Python on Windows?

**A:** Python is trusted by most AVs and firewalls:
- Acts as a "middleman" proxy
- AVs don't block Python's network activity
- More reliable than direct port forwarding

### Q: Can I use Python 2?

**A:** No, Python 3.x is required (Python 2 is deprecated)

### Q: Do I need to keep the Python window open?

**A:** The script launches it in hidden mode:
- Runs in background
- No window shown
- Can be stopped via Task Manager if needed

### Q: What if my Windows IP changes?

**A:** The bridge auto-detects Windows IP:
- Reads from `/etc/resolv.conf`
- Updates automatically
- No manual configuration needed

### Q: Can I use a different proxy port?

**A:** Yes, edit both:
- Windows: `wsl_chrome_proxy.py` (LISTEN_PORT)
- WSL: `start_bridge.sh` (port 9223 references)

### Q: Why socat instead of netcat?

**A:** Socat is more robust:
- Better connection handling
- Supports bidirectional streaming
- More reliable for WebSocket (CDP)

---

## Performance Questions

### Q: Which solution is faster?

**A:** Solution 1 (Native) is typically faster:
| Metric | Solution 1 | Solution 2 |
|--------|-----------|-----------|
| Latency | 0ms overhead | ~1-2ms proxy overhead |
| Throughput | Full speed | 99% of full speed |

### Q: Will this slow down my automation?

**A:** No significant performance impact:
- CDP uses minimal bandwidth
- Both solutions are plenty fast for automation
- Real bottleneck is usually your automation code

### Q: Does the watchdog use significant CPU?

**A:** No:
- Checks every 30 seconds (not constantly)
- Single `curl` command
- Sleeps between checks
- <0.1% CPU usage

---

## Security Questions

### Q: Is remote debugging secure?

**A:** Both solutions bind to localhost only:
- Not accessible from network
- Only your WSL can connect
- Standard practice for local development

### Q: What data does Chrome expose on :9222?

**A:** Chrome DevTools Protocol provides:
- Access to tabs
- DOM inspection
- JavaScript execution
- **Important:** This is intentional for automation

### Q: Can malware use this?

**A:** Only if malware is already running in your WSL:
- Port 9222 is localhost-only
- Not exposed to network
- Same risk as running Chrome normally

### Q: Should I use this in production?

**A:** These solutions are for **development only**:
- Not designed for production servers
- Use headless Chrome servers for production
- Or cloud browser automation services

---

## Compatibility Questions

### Q: Does this work on WSL 1?

**A:** 
- Solution 1: ✅ Yes
- Solution 2: ⚠️ May have networking issues (WSL 1 networking differs)

### Q: What about macOS or native Linux?

**A:**
- Solution 1: ✅ Works on native Linux (skip watchdog part if systemd available)
- Solution 2: ❌ WSL-specific (uses Windows ↔ WSL bridge)
- macOS: Use Chrome normally (no special setup needed)

### Q: Does this work with Chrome Beta/Canary?

**A:** Yes, edit the Chrome binary path:
- Solution 1: Edit `CHROME_BIN` in scripts
- Solution 2: Update Windows batch file

### Q: What about Chromium instead of Chrome?

**A:** Yes! Replace google-chrome with chromium in scripts

---

## Troubleshooting Questions

### Q: I get "port already in use" errors

**A:** 
```bash
# Check what's using port 9222
lsof -i :9222

# Option 1: Kill it
pkill -f "9222"

# Option 2: Use different port (see above)
```

### Q: Watchdog keeps restarting Chrome

**A:** Check logs for why Chrome is dying:
```bash
tail -50 /tmp/antigravity_chrome.log
```

### Q: Windows Bridge can't connect

**A:** Check in order:
1. Windows Chrome running with `--remote-debugging-port=9222`?
2. Python proxy running?
3. Firewall not blocking port 9223?
4. Socat running in WSL?

---

## Advanced Questions

### Q: Can I customize Chrome launch flags?

**A:** Yes, edit `ensure_chrome_running.sh`:
```bash
# Add your flags here:
--disable-notifications \
--disable-popup-blocking \
--start-maximized
```

### Q: Can I use this with Docker in WSL?

**A:** Yes:
- Solution 1: Map port 9222 to container
- Solution 2: Same Docker setup

### Q: How do I uninstall?

**Solution 1:**
```bash
# Stop watchdog
~/chrome-ctl stop

# Remove scripts
rm ~/ensure_chrome_running.sh ~/chrome_watchdog.sh ~/start_chrome_watchdog.sh ~/chrome-ctl ~/chrome_shim

# Remove from .bashrc (delete Antigravity Chrome section)
nano ~/.bashrc
```

**Solution 2:**
```bash
# Remove shim
sudo rm /usr/bin/google-chrome

# Restore backup (if exists)
sudo mv /usr/bin/google-chrome.bak /usr/bin/google-chrome

# Stop processes
pkill socat
# Stop Windows Python proxy
```

---

## Still have questions?

- 🐛 Bug reports: [GitHub Issues](https://github.com/Den3112/antigravity-wsl-chrome-manager/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/Den3112/antigravity-wsl-chrome-manager/discussions)
- 📖 Documentation: [README.md](README.md)
