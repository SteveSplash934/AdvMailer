<p align="center">
  <img src="static/SendoraLiteLogo.png" alt="Sendora Lite Logo" width="320">
</p>

# Sendora Lite

<p align="center">
  <a href="https://github.com/stevesplash934/SendoraLite/stargazers"><img src="https://img.shields.io/github/stars/stevesplash934/SendoraLite?style=flat&logo=github&color=gold" alt="Stars"></a>
  <a href="https://github.com/stevesplash934/SendoraLite/network/members"><img src="https://img.shields.io/github/forks/stevesplash934/SendoraLite?style=flat&logo=github&color=blue" alt="Forks"></a>
  <a href="https://github.com/stevesplash934/SendoraLite/releases"><img src="https://img.shields.io/github/downloads/stevesplash934/SendoraLite/total?style=flat&logo=github&color=green" alt="Downloads"></a>
  <a href="https://github.com/stevesplash934/SendoraLite/issues"><img src="https://img.shields.io/github/issues/stevesplash934/SendoraLite?style=flat&logo=github&color=orange" alt="Issues"></a>
  <a href="https://github.com/stevesplash934/SendoraLite/blob/main/LICENSE"><img src="https://img.shields.io/github/license/stevesplash934/SendoraLite?style=flat&logo=github&color=purple" alt="License"></a>
</p>

Sendora Lite is an asynchronous bulk email dispatch engine built with Python, Flask, and `aiosmtplib`. We designed it for high performance and ease of use, featuring a dark-themed control panel, a full-screen template manager with an integrated Ace Code Editor, and live WYSIWYG previews. The entire project is managed natively using `uv` for fast, isolated execution.

---

## Key Features

* **Asynchronous Dispatch Engine:** Uses `aiosmtplib` and Python `asyncio` semaphores to handle concurrent, multi-threaded email transmission without blocking.
* **Mailer Settings Panel:** A dedicated section to manage SMTP connection parameters, sender identities, and safely toggle passwords. Includes a "TEST SMTP" function to verify connections before dispatch.
* **Template Control Panel & Workspace:**
  * Gallery view for managing saved HTML and plain text email templates.
  * Full-screen workspace overlay for a distraction-free editing environment.
  * Integrated **Ace Code Editor** for real-time HTML syntax highlighting.
  * Single-canvas view switcher to toggle between **Code View** and **Live Preview**.
  * **Visual WYSIWYG Editing:** Click and edit text directly inside the interactive live preview frame—changes synchronize to the source code automatically.
  * Active template toggling with clear status indicators.
* **Selective Email Attachments:** A multi-file workspace where you can check or uncheck individual uploaded files to include in specific email runs.
* **Smart Recipient Management:** Drag-and-drop CSV and TXT importer. It automatically handles deduplication, validates syntax via `email-validator`, and provides dynamic state views of your lists.
* **Real-time Monitoring & History:** Track live delivery counts (Sent vs. Failed), view job history logs, and monitor live-scrolling terminal outputs directly in the UI.
* **Danger Zone Maintenance:** Utilities for safe configuration resets and full "Clean Slate" database/disk wipes, protected by confirmation overlays.
* **`uv` Package Management:** Fully integrated with Astral's `uv` for strict environment isolation, deterministic locking, and fast execution.

*By the way, this is only a toy version of the tool! If you’d like to see the real, much more advanced version, check it out here: [Sendora](https://github.com/SteveSplash934/sendora)*

---

## Project Structure

```text
├── app.py                     # Main Flask web application and API endpoints
├── run_prod.py                # Cross-platform production WSGI launcher (Gunicorn / Waitress)
├── Dockerfile                 # Multi-stage production container build configuration
├── .dockerignore              # Excluded files for Docker build context
├── pyproject.toml             # Project manifest & dependency configuration
├── uv.lock                    # Deterministic dependency lockfile
├── .python-version            # Python version specification (3.13.3)
├── config.ini.example         # Template configuration file
├── mailer/
│   ├── __init__.py
│   ├── config_manager.py      # SQLite database manager & configuration state
│   ├── parser.py              # CSV / TXT recipient parser & validation
│   └── sender.py              # Asynchronous SMTP dispatch engine
├── static/
│   └── SendoraLiteLogo.png    # Application logo asset
├── templates/
│   └── index.html             # Application single-page interface (Tailwind CSS, Ace Editor)
├── uploads/
│   ├── attachments/           # Stored email attachments
│   └── templates/             # Stored email template files
└── logs/
    └── mailer_live.log        # Real-time application log output
```

---

## Setup & Installation

### Prerequisites

* Python **3.10+** (Python **3.13.3** is recommended)
* **`uv`** package manager (or Docker for containerized deployment).

If you don't have `uv` installed, you can run this to setup `uv`:

**On macOS / Linux**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**On Windows (PowerShell or Command Prompt)**
```batch
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Installation Steps

1. **Clone the Repository**:
```bash
git clone https://github.com/stevesplash934/SendoraLite.git
cd SendoraLite
```

2. **Initialize and Sync Environment**:
Run `uv sync` to set up the virtual environment (`.venv`) and install the required packages defined in `pyproject.toml`.
```bash
uv sync
```

3. **Launch the Application**:

* **Development Mode**:
  ```bash
  uv run app.py
  ```

* **Cross-Platform Production WSGI Mode (Recommended if you are on VPS/RDP)**:
  Automatically detects host OS to launch **Gunicorn** on Linux/macOS or **Waitress** on Windows:
  ```bash
  uv run run_prod.py
  ```

4. **Access the Application**:
Open your browser and navigate to:
```text
http://127.0.0.1:5000
```

---

### Docker Deployment

You can also run Sendora Lite in a containerized production environment:

1. **Build Container Image**:
   ```bash
   docker build -t sendoralite:latest .
   ```

2. **Run Container**:
   ```bash
   docker run -d -p 5000:5000 --name sendoralite sendoralite:latest
   ```

---

### Firewall & Security Configuration

If you are hosting Sendora Lite on a VPS, cloud provider, or Windows Server, ensure port `5000` is open to accept incoming web traffic.

* **Ubuntu / Debian (UFW)**:
  ```bash
  sudo ufw allow 5000/tcp
  sudo ufw reload
  ```

* **CentOS / RHEL / Fedora (firewalld)**:
  ```bash
  sudo firewall-cmd --add-port=5000/tcp --permanent
  sudo firewall-cmd --reload
  ```

* **Windows Server / Windows 10/11 (PowerShell as Administrator)**:
  ```powershell
  New-NetFirewallRule -DisplayName "Sendora Lite Inbound Port 5000" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow
  ```

* **Cloud Provider Security Groups (AWS / DigitalOcean / Hetzner / Linode)**:
  In your cloud management portal, go to **Networking / Security Groups / Firewalls** and add an **Inbound Rule**:
  * **Protocol**: `TCP`
  * **Port**: `5000`
  * **Source**: `0.0.0.0/0` (Anywhere)

*Once this is successful, you can now access the service on your VPS/RDP `http://<ip>:<service_port>` (e.g, `http://123.123.123.123:5000`)*

---

## Usage Workflow

1. **Configure Mailer Settings**:
* Go to **Mailer Settings** in the sidebar.
* Input your SMTP server details (Host, Port, Username, Password).
* Click **TEST SMTP** to verify the credentials, then click **SAVE SETTINGS**.

2. **Manage Email Templates**:
* Navigate to **Email Template**.
* Click **Create New** or upload an existing template (`.html` or `.txt`).
* Click **Edit** to open the workspace. You can switch between **Code View** and **Live Preview** (where you can edit text visually).
* Click **Set Active** on a template card to select it for your next dispatch.

3. **Select Attachments**:
* Navigate to **Email Attachment**.
* Upload files and use the checkboxes to include/exclude them from the dispatch.

4. **Import Recipients**:
* Go to **Recipients**.
* Drag and drop a `.csv` or `.txt` file containing your email list. The app will validate and deduplicate them automatically.

5. **Start Dispatch**:
* Click **START DISPATCH** in the top-right corner.
* Monitor your delivery progress in real-time on the **Dashboard** or **Logs** page.