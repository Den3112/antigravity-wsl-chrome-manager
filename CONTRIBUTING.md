# Contributing Guidelines

Thank you for considering contributing to Antigravity WSL Chrome Manager! 🎉

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)

## 📜 Code of Conduct

This project follows a simple code of conduct:
- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and improve

## 🤝 How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues. When creating a bug report, include:

- **Clear title and description**
- **Steps to reproduce**
- **Expected vs actual behavior**
- **Environment details:**
  - WSL version (`wsl --version`)
  - Chrome version
  - Which solution (1 or 2)
  - Logs (if applicable)

### Suggesting Enhancements

Enhancement suggestions are welcome! Please include:
- **Use case:** Why is this needed?
- **Proposed solution:** How should it work?
- **Alternatives:** Other approaches considered?

### Code Contributions

We welcome PRs for:
- 🐛 Bug fixes
- ✨ New features
- 📚 Documentation improvements
- 🧪 Test coverage
- ♻️ Code refactoring

## 🔧 Development Setup

```bash
# Fork and clone
git clone https://github.com/Den3112/antigravity-wsl-chrome-manager.git
cd antigravity-wsl-chrome-manager

# Test Solution 1
cd solution-1-native-chrome
chmod +x setup.sh
./setup.sh

# Test Solution 2
cd ../solution-2-windows-bridge
chmod +x setup.sh
./setup.sh
```

## 📝 Pull Request Process

1. **Fork the repository**

2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**
   - Follow coding standards (see below)
   - Test thoroughly
   - Update documentation

4. **Commit with clear messages**
   ```bash
   git commit -m "feat: add support for custom Chrome flags"
   git commit -m "fix: watchdog not detecting Chrome crashes"
   git commit -m "docs: improve installation instructions"
   ```

   Use conventional commits:
   - `feat:` new feature
   - `fix:` bug fix
   - `docs:` documentation
   - `refactor:` code refactoring
   - `test:` testing
   - `chore:` maintenance

5. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **PR Review**
   - Maintainers will review your PR
   - Address any feedback
   - Once approved, it will be merged!

## 🎨 Coding Standards

### Shell Scripts

```bash
#!/bin/bash
set -e  # Exit on error

# Use descriptive variable names
CHROME_PORT=9222
USER_DATA_DIR="/path/to/dir"

# Add comments for complex logic
# This function checks if Chrome is running
check_chrome() {
    curl -s "http://127.0.0.1:$CHROME_PORT/json/version" > /dev/null 2>&1
}

# Use proper error handling
if ! check_chrome; then
    echo "❌ Chrome not running"
    exit 1
fi
```

### Python Scripts

```python
"""Module docstring explaining purpose."""

import sys
import socket

# Constants in UPPER_CASE
LISTEN_PORT = 9223
BUFFER_SIZE = 65536

def function_name(param: str) -> bool:
    """Function docstring.
    
    Args:
        param: Description
        
    Returns:
        Description
    """
    pass
```

### Documentation

- Use clear, concise language
- Include code examples
- Add emoji for visual scanning (sparingly)
- Keep line length < 100 characters
- Use proper markdown formatting

## 🧪 Testing

Before submitting:

```bash
# Test Solution 1
cd solution-1-native-chrome
./setup.sh
# Verify Chrome starts
curl http://127.0.0.1:9222/json/version
# Test watchdog
~/chrome-ctl status

# Test Solution 2
cd solution-2-windows-bridge
./setup.sh
# Test shim
google-chrome --version
# Test bridge
./wsl/start_bridge.sh
```

## 📚 Documentation Requirements

When adding features, update:
- Solution-specific README
- Main README (if affects both)
- FAQ (if answering common question)
- TROUBLESHOOTING (if adds new issue/solution)

## 🔒 Security Policy

See [SECURITY.md](SECURITY.md) for:
- Reporting vulnerabilities
- Security best practices
- Response timeline

## ❓ Questions?

- 💬 [GitHub Discussions](https://github.com/Den3112/antigravity-wsl-chrome-manager/discussions)
- 🐛 [Issues](https://github.com/Den3112/antigravity-wsl-chrome-manager/issues)

## 🌟 Recognition

Contributors will be:
- Listed in README
- Mentioned in release notes
- Appreciated endlessly! 🎉

---

Thank you for contributing! 🚀
