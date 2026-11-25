```
 ____    _    ____  _  __   ___ ____  ____      _    _   _ ___ __  __
|  _ \  / \  |  _ \| |/ /  |_ _| __ )|  _ \    / \  | | | |_ _|  \/  |
| | | |/ _ \ | |_) | ' /    | ||  _ \| |_) |  / _ \ | |_| || || |\/| |
| |_| / ___ \|  _ <| . \    | || |_) |  _ <  / ___ \|  _  || || |  | |
|____/_/   \_\_| \_\_|\_\  |___|____/|_| \_\/_/   \_\_| |_|___|_|  |_|
```

```
Developer : DARK IBRAHIM
Title     : Bug Bounty Hunter & Cyber Security Expert
Facebook  : https://www.facebook.com/profile.php?id=61580661413217
GitHub    : https://github.com/darkibrahim
Telegram  : @Hunter_1B4H14
```

# DARK-IBRAHIM — Local AI Software & APK Builder

Describe a project in plain words and DARK-IBRAHIM plans it, writes the files, checks them,
fixes what it can, and hands you **one clean ZIP**. For web projects it can also wrap the result
into an **Android project / APK**. Everything runs on your own machine with free, open-source tools.

## Features

- **Local AI engine** — uses [Ollama](https://ollama.com); no cloud account, no API keys.
- **Works offline too** — built-in templates (Python CLI, Flask web app, static website, Android web app) are used when Ollama is not installed.
- **Plan → generate → test → debug → ZIP** pipeline with automatic fixes (syntax repair, missing `requirements.txt` entries).
- **Web interface** with live build log, file preview, download button and history.
- **APK generator** — creates a ready Android Studio / Gradle project (WebView app), validates it, and builds + signs an APK when JDK 17, Gradle and the Android SDK are present. A GitHub Actions workflow is included in every Android project so you can build the APK on GitHub without installing anything.
- **Security built in** — path-traversal protection, file-type allow-list, secret scanner, Android permission allow-list (spyware-style permissions are refused), CSP and security headers, localhost-only by default.

## Install

Works on Kali Linux, Debian/Ubuntu, Arch, NetHunter and Termux.

```bash
git clone https://github.com/darkibrahim/DARK-IBRAHIM.git
cd DARK-IBRAHIM
chmod +x scripts/*.sh
./scripts/install.sh
./scripts/run.sh
```

Open **http://127.0.0.1:5000**.

Manual install:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

### Optional: enable the AI engine

```bash
# install Ollama from https://ollama.com, then:
ollama pull qwen2.5-coder:7b
python app.py --check      # shows Ollama / model / Android status
```

Smaller phones and low-RAM PCs can use `qwen2.5-coder:3b`. Pick the model in the web interface or set `DARK_MODEL` in `.env`.

## Usage

1. Type your idea (for example: *"A Flask dashboard that stores notes"*).
2. Choose the project type and engine, or leave both on automatic.
3. Press **Build project**, then **Download ZIP**.
4. For web/Android projects press **Build Android project / APK**.

### Build the APK

| Situation | Result |
|-----------|--------|
| JDK 17 + Gradle 8.2+ + Android SDK installed (`ANDROID_HOME` set) | A debug APK (or a signed release APK) is built and validated. |
| Anything missing (typical on Termux/NetHunter) | You get the **Android project ZIP**. Open it in Android Studio, or push it to GitHub and run the *Build APK* workflow. |

## Configuration

Copy `.env.example` to `.env`:

| Variable | Default | Meaning |
|----------|---------|---------|
| `DARK_HOST` / `DARK_PORT` | `127.0.0.1` / `5000` | Web server address |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Ollama server |
| `DARK_MODEL` | `qwen2.5-coder:7b` | Preferred model |
| `DARK_KEYSTORE_PASSWORD` | random | Password for the APK signing key |

## Project structure

```
app.py                 entry point (web server, --check)
config.py              settings, banner and branding
backend/               REST API, agent, planner, generator, debugger, tester, APK API, job store
ai_engine/             Ollama client, prompts, model manager
project_manager/       workspace, safe file writer, ZIP export
apk_generator/         Android project builder, manifest, Gradle runner, signer, validator, templates
frontend/              web interface (index.html, style.css, app.js)
database/              SQLite history (history.db is created on first run)
security/              validators and Android permission policy
tests/                 unit and API tests
scripts/               install.sh, run.sh
```

## Run the tests

```bash
python -m unittest discover -s tests -t . -v
```

## Security notes

- The server has **no login**. Keep it on `127.0.0.1` unless you are on a trusted network.
- Generated code is **never executed** by the tool; it is only parsed and checked.
- Never commit `.env` or keystores — both are in `.gitignore`.
- Use this tool only for lawful purposes.

## Known limitations

- Quality of AI-written code depends on the local model you choose; always review generated code.
- Tests are static checks (syntax, imports, structure, secrets), not runtime tests of the generated project.
- Generated Android apps are WebView apps for plain HTML/CSS/JS; native Kotlin/Java apps are not generated.
- APK building needs JDK 17+, Gradle 8.2+ and the Android SDK, which are not installable on most phones.

## License

MIT — see [LICENSE](LICENSE).

---

Developer: **DARK IBRAHIM** · Bug Bounty Hunter & Cyber Security Expert · GitHub: https://github.com/darkibrahim · Telegram: @Hunter_1B4H14
