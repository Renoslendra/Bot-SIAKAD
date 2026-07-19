<div align="center">

# 🏎️ BOT-SIAKAD

### ⚡ Auto Course Selection System ⚡

**SIAKAD Universitas Trunojoyo Madura**

*Engineered with Precision — BMW-M Design Language*

<br/>

<table>
<tr>
<td>

![Python](https://img.shields.io/badge/Python-3.14+-000000?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0.0-000000?style=for-the-badge&logo=flask&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-Automation-000000?style=for-the-badge&logo=playwright&logoColor=white)

</td>
<td>

![Status](https://img.shields.io/badge/Status-Production_Ready-0fa336?style=for-the-badge&logo=rocket&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-38_Passed-1c69d4?style=for-the-badge&logo=pytest&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-000000?style=for-the-badge)

</td>
</tr>
</table>

<br/>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

</div>

## 🎯 Overview

**BOT-SIAKAD** is an intelligent automation system designed to streamline course selection at SIAKAD Universitas Trunojoyo Madura. Built with cutting-edge technology and a premium BMW-M inspired dark interface, this bot handles everything from login to course submission with military-grade precision.

### ✨ Key Features

<table>
<tr>
<td width="50%">

🤖 **Smart Automation**
- Auto-login to SIAKAD
- Intelligent course scraping
- Conflict-free schedule selection
- Priority-based course allocation

</td>
<td width="50%">

🛡️ **Safety First**
- Multi-layer safety locks
- Dry-run mode for testing
- Configurable submit controls
- Comprehensive error handling

</td>
</tr>
<tr>
<td>

🎨 **Premium UI/UX**
- BMW-M dark aesthetic
- Real-time monitoring dashboard
- Live console output
- Responsive design

</td>
<td>

📊 **Advanced Reporting**
- Detailed session logs
- Success rate tracking
- Error analytics
- Export capabilities (CSV/JSON)

</td>
</tr>
</table>

<br/>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🚀 Quick Start

<div align="center">

### Get up and running in **60 seconds**

</div>

```bash
# 1️⃣ Clone the repository
git clone https://github.com/yourusername/Bot-SIAKAD.git
cd Bot-SIAKAD

# 2️⃣ Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows
# source .venv/bin/activate   # Linux/Mac

# 3️⃣ Install dependencies
pip install -r requirements.txt
playwright install chromium

# 4️⃣ Configure environment
copy .env.example .env
# Edit .env with your SIAKAD credentials

# 5️⃣ Run your first dry-run
python main.py --dry-run
```

<br/>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 📁 Project Structure

```
Bot-SIAKAD/
│
├── 🤖 bot/                          # Core automation package
│   ├── cli.py                       # Command-line interface
│   ├── config.py                    # Configuration management
│   ├── login.py                     # SIAKAD authentication
│   ├── scraper.py                   # Data extraction engine
│   ├── selector.py                  # Course selection logic
│   ├── submitter.py                 # KRS submission handler
│   ├── reporter.py                  # Report generation
│   └── utils.py                     # Utility functions
│
├── 🎨 ui/                           # BMW-M Dashboard Interface
│   ├── server.py                    # Flask web server
│   ├── templates/                   # HTML templates
│   │   ├── base.html               # Base layout
│   │   ├── dashboard.html          # Main dashboard
│   │   ├── konfigurasi.html        # Settings page
│   │   ├── mata_kuliah.html        # Course management
│   │   ├── monitoring.html         # Real-time monitoring
│   │   └── riwayat.html            # History & reports
│   └── static/
│       ├── css/style.css           # BMW-M design system
│       └── js/app.js               # Interactive features
│
├── ⚙️ config/
│   ├── selectors.example.json      # Template configuration
│   └── selectors.json              # Active config (gitignored)
│
├── 📝 docs/                         # Documentation
│   ├── PRD.md                      # Product requirements
│   ├── Task.md                     # Task breakdown
│   ├── Guideline.md                # Development guidelines
│   ├── PREFLIGHT.md                # Pre-launch checklist
│   └── flowchart.html              # System flowchart
│
├── 🔧 scripts/                      # Utility scripts
│   ├── recon.py                    # Site reconnaissance
│   └── check_semester5.py          # Semester 5 validator
│
├── 🧪 tests/                        # Test suite (38 tests)
├── 📋 logs/                         # Runtime logs (gitignored)
├── 🎯 hermes-skill/                 # Hermes integration
│
├── 📄 main.py                       # CLI entrypoint
├── 📦 requirements.txt              # Python dependencies
├── 🔐 .env.example                  # Environment template
└── 📖 README.md                     # This file
```

<br/>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🎮 Usage

### CLI Commands

<table>
<thead>
<tr>
<th>Command</th>
<th>Description</th>
<th>Example</th>
</tr>
</thead>
<tbody>
<tr>
<td><code>--dry-run</code></td>
<td>Test run without submission</td>
<td><code>python main.py --dry-run</code></td>
</tr>
<tr>
<td><code>--status</code></td>
<td>Show last report</td>
<td><code>python main.py --status</code></td>
</tr>
<tr>
<td><code>--run</code></td>
<td>Full pipeline with submit</td>
<td><code>python main.py --run</code></td>
</tr>
<tr>
<td><code>--auto-confirm</code></td>
<td>Skip confirmation prompts</td>
<td><code>python main.py --run --auto-confirm</code></td>
</tr>
<tr>
<td><code>--headless</code></td>
<td>Run browser in background</td>
<td><code>python main.py --dry-run --headless</code></td>
</tr>
<tr>
<td><code>--headed</code></td>
<td>Show browser window</td>
<td><code>python main.py --dry-run --headed</code></td>
</tr>
</tbody>
</table>

### Web Dashboard

Launch the BMW-M inspired dashboard:

```bash
cd ui
python server.py
```

Access at: **http://localhost:5000**

<div align="center">

**Features:**
🎯 Real-time bot control • 📊 Live monitoring • ⚙️ Configuration management • 📚 Course priority setup • 📈 Analytics & reports

</div>

<br/>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🛡️ Safety Protocol

<div align="center">

### ⚠️ CRITICAL: Read Before Production Use

</div>

<table>
<tr>
<td width="100%">

**Default Safety Settings:**

```env
ALLOW_SUBMIT=false      # 🔒 Submission disabled by default
USE_FALLBACK=false      # 🔒 Fallback courses disabled
```

</td>
</tr>
</table>

### Safety Checklist

- [ ] **Step 1:** Run `--dry-run` to verify configuration
- [ ] **Step 2:** Review `logs/selection_report.json`
- [ ] **Step 3:** Confirm all courses are correct
- [ ] **Step 4:** Set `ALLOW_SUBMIT=true` ONLY when ready
- [ ] **Step 5:** Run with `--run --auto-confirm`
- [ ] **Step 6:** Verify on SIAKAD website
- [ ] **Step 7:** **IMMEDIATELY** set `ALLOW_SUBMIT=false`

<br/>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🎨 BMW-M Design System

The UI follows the prestigious **BMW M Design Language**:

<table>
<tr>
<td width="33%">

### 🎨 Color Palette

```css
Canvas:        #000000
Surface:       #1a1a1a
M Blue Light:  #0066b1
M Blue Dark:   #1c69d4
M Red:         #e22718
```

</td>
<td width="33%">

### 📐 Design Principles

- **Zero border-radius** (industrial precision)
- **Uppercase typography** (bold statements)
- **M Tricolor accents** (brand signature)
- **Dark premium aesthetic** (motorsport heritage)

</td>
<td width="33%">

### ⚡ Features

- Real-time status updates
- Live console monitoring
- Responsive design
- Toast notifications
- Modal interactions

</td>
</tr>
</table>

<br/>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 📊 System Status

<table>
<thead>
<tr>
<th>Component</th>
<th>Status</th>
<th>Details</th>
</tr>
</thead>
<tbody>
<tr>
<td>Core Package</td>
<td>✅ <strong>Ready</strong></td>
<td>38 tests passed</td>
</tr>
<tr>
<td>Login Module</td>
<td>✅ <strong>Ready</strong></td>
<td>Authenticated scraping</td>
</tr>
<tr>
<td>Selection Engine</td>
<td>✅ <strong>Ready</strong></td>
<td>Priority-based allocation</td>
</tr>
<tr>
<td>Submit Module</td>
<td>✅ <strong>Ready</strong></td>
<td>Safety-locked by default</td>
</tr>
<tr>
<td>Web Dashboard</td>
<td>✅ <strong>Ready</strong></td>
<td>BMW-M design complete</td>
</tr>
<tr>
<td>Semester 5 List</td>
<td>⚠️ <strong>Partial</strong></td>
<td>Run check script</td>
</tr>
<tr>
<td>Production Submit</td>
<td>🔒 <strong>Locked</strong></td>
<td>Until KRS period opens</td>
</tr>
</tbody>
</table>

<br/>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🔧 Configuration

### Environment Variables

```env
# SIAKAD Credentials
SIAKAD_USERNAME=your_nim_here
SIAKAD_PASSWORD=your_password_here

# Safety Controls
ALLOW_SUBMIT=false
USE_FALLBACK=false

# Browser Settings
HEADLESS=true
TIMEOUT=30000
```

### Course Priority Setup

Edit `config/selectors.json`:

```json
{
  "priority_courses": [
    {"code": "CS5001", "name": "Algoritma & Pemrograman", "sks": 3},
    {"code": "CS5002", "name": "Struktur Data", "sks": 4},
    {"code": "CS5003", "name": "Basis Data", "sks": 3}
  ],
  "fallback_courses": [
    {"code": "CS5009", "name": "Matematika Diskrit", "sks": 3}
  ],
  "target_sks": 23
}
```

<br/>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=bot --cov-report=html

# Run specific test file
pytest tests/test_selector.py -v
```

**Test Coverage:**
- ✅ Login authentication
- ✅ Course scraping
- ✅ Schedule conflict detection
- ✅ Priority selection
- ✅ Safety mechanisms
- ✅ Error handling

<br/>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 📚 Documentation

<div align="center">

<table>
<tr>
<td>

### 📋 [PRD.md](docs/PRD.md)
Product Requirements Document

</td>
<td>

### 🎯 [Task.md](docs/Task.md)
Task Breakdown & Progress

</td>
</tr>
<tr>
<td>

### 📖 [Guideline.md](docs/Guideline.md)
Development Guidelines

</td>
<td>

### ✅ [PREFLIGHT.md](docs/PREFLIGHT.md)
Pre-Launch Checklist

</td>
</tr>
</table>

### 🔄 [flowchart.html](docs/flowchart.html)
Interactive System Flowchart

</div>

<br/>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🤝 Contributing

Contributions are welcome! Here's how:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/AmazingFeature`)
3. **Commit** your changes (`git commit -m 'Add AmazingFeature'`)
4. **Push** to the branch (`git push origin feature/AmazingFeature`)
5. **Open** a Pull Request

### Development Setup

```bash
# Install dev dependencies
pip install -r requirements.txt
pip install pytest pytest-cov black flake8

# Run code quality checks
black bot/ ui/
flake8 bot/ ui/
pytest tests/ -v
```

<br/>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 📝 Changelog

### v1.0.0 (2026-01-19)

- ✅ Complete BMW-M dashboard UI
- ✅ Real-time monitoring system
- ✅ Course priority management
- ✅ Session history & analytics
- ✅ CSV/JSON export functionality
- ✅ Enhanced security (CSRF, rate limiting, password hashing)
- ✅ Responsive mobile design
- ✅ 38 passing tests

### v0.9.0 (2026-01-18)

- ✅ Core automation engine
- ✅ SIAKAD login module
- ✅ Course scraper
- ✅ Conflict-free selector
- ✅ Safety-locked submitter

<br/>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🐛 Troubleshooting

<details>
<summary><strong>Login fails with "Invalid credentials"</strong></summary>

- Verify credentials in `.env`
- Check SIAKAD website is accessible
- Ensure no CAPTCHA is required
- Review `logs/console.json` for details

</details>

<details>
<summary><strong>No courses found during scraping</strong></summary>

- Run `python scripts/recon.py` to update selectors
- Verify semester is active on SIAKAD
- Check `config/selectors.json` is up to date

</details>

<details>
<summary><strong>Dashboard shows "IDLE" status</strong></summary>

- Start the bot: `python main.py --dry-run`
- Check if server is running: `cd ui && python server.py`
- Verify API endpoint: `http://localhost:5000/api/status`

</details>

<details>
<summary><strong>Course selection fails with conflicts</strong></summary>

- Review schedule in `logs/selection_report.json`
- Adjust priority in `config/selectors.json`
- Enable fallback courses if needed

</details>

<br/>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

<br/>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<div align="center">

### 🏎️ Built with Precision. Engineered for Excellence.

**BOT-SIAKAD** — Where Automation Meets Art

<br/>

<table>
<tr>
<td>

**Made with ❤️ by**

Renos

</td>
<td>

**Powered by**

🐍 Python • 🌶️ Flask • 🎭 Playwright

</td>
<td>

**Designed with**

🏎️ BMW-M Aesthetic

</td>
</tr>
</table>

<br/>

**⭐ Star this repo if you find it useful! ⭐**

<br/>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<sub>© 2026 Bot-SIAKAD | Universitas Trunojoyo Madura</sub>

</div>
