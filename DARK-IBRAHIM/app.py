#!/usr/bin/env python3
# ----------------------------------------------------------------------
# DARK-IBRAHIM - Local AI Software & APK Builder
# Developer : DARK IBRAHIM
# Title     : Bug Bounty Hunter & Cyber Security Expert
# Facebook  : https://www.facebook.com/profile.php?id=61580661413217
# GitHub    : https://github.com/darkibrahim
# Telegram  : @Hunter_1B4H14
# ----------------------------------------------------------------------
"""DARK-IBRAHIM entry point.

    python app.py            start the web interface
    python app.py --check    print a quick environment report
"""
import argparse
import sys

import config


def print_banner() -> None:
    print(f"\033[36m{config.BANNER}\033[0m")
    print(f"\n{config.APP_NAME} v{config.VERSION} - {config.APP_TAGLINE}\n")
    print(config.brand_block() + "\n")


def run_check() -> int:
    from ai_engine.model_manager import ModelManager
    from apk_generator.gradle_manager import check_environment

    overview = ModelManager().overview()
    print(f"Ollama   : {'online' if overview['ollama_available'] else 'offline'} ({overview['host']})")
    print(f"Models   : {', '.join(overview['installed']) or 'none installed'}")
    env = check_environment()
    print(f"Android  : {'ready' if env['ready'] else 'not ready - ' + ' '.join(env['problems'])}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=config.APP_TAGLINE)
    parser.add_argument("--host", default=config.HOST)
    parser.add_argument("--port", type=int, default=config.PORT)
    parser.add_argument("--check", action="store_true", help="show environment status and exit")
    args = parser.parse_args()

    print_banner()
    if args.check:
        return run_check()

    from backend.api import create_app

    config.setup_logging()
    app = create_app()
    if args.host not in ("127.0.0.1", "localhost", "::1"):
        print("WARNING: the server is reachable from other devices and has no login. "
              "Use it only on a trusted network.\n")
    print(f"Open http://{args.host}:{args.port} in your browser (Ctrl+C to stop)\n")
    app.run(host=args.host, port=args.port, threaded=True, debug=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
