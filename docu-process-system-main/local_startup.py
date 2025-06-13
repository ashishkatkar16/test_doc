#!/usr/bin/env python3
"""
Local startup script to run all services without Docker
"""

import subprocess
import time
import os
import sys
import socket
from pathlib import Path
from urllib.parse import urlparse


def check_service_cli(service_name: str, command: str) -> bool:
    """Run a shell command and return True if it exits 0."""
    try:
        return subprocess.run(command, shell=True).returncode == 0
    except Exception:
        return False


def port_is_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """Return True if we can open a TCP socket to (host, port)."""
    try:
        with socket.create_connection((host, port), timeout):
            return True
    except Exception:
        return False


def start_service_in_background(
    name: str,
    command: str,
    port: int = None,
    wait_seconds: float = 5.0
):
    """Start a service in the background, streaming its logs, and optionally check its TCP port."""
    print(f"\n🚀 Starting {name!r} → `{command}`")
    try:
        proc = subprocess.Popen(
            command,
            shell=True,
            cwd=os.getcwd(),
            stdout=sys.stdout,
            stderr=sys.stderr,
            preexec_fn=os.setsid if os.name != 'nt' else None
        )
    except Exception as e:
        print(f"❌ Failed to launch {name}: {e}")
        return None

    if port is not None:
        time.sleep(wait_seconds)
        if port_is_open("localhost", port):
            print(f"✅ {name} is now listening on port {port}")
        else:
            print(f"⚠️  {name} did NOT open port {port} (see above logs)")
    else:
        time.sleep(2)
        print(f"✅ {name} launched")

    return proc


def main():
    # 1) cd into project root (where local_startup.py lives)
    project_root = Path(__file__).parent.resolve()
    os.chdir(project_root)
    sys.path.insert(0, str(project_root))

    print("\n" + "🚀 Document Processing System (Local Mode)".center(60, "=") + "\n")

    # 2) Create directories
    os.makedirs("robot_folder", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    print("📁 Created `robot_folder/` and `logs/`")

    # 3) Virtualenv check
    if not getattr(sys, "real_prefix", None) and (getattr(sys, "base_prefix", None) == sys.prefix):
        print("⚠️  Virtual environment not detected. Activate: source venv/bin/activate")

    # 4) Load .env
    from dotenv import load_dotenv
    load_dotenv()

    # 5) Parse DATABASE_URL for host/port
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/docuprocess"
    )
    parsed = urlparse(db_url)
    db_host = parsed.hostname or "localhost"
    db_port = parsed.port or 5432

    # 6) Prerequisite checks
    print("\n🔍 Checking prerequisites…")
    if not port_is_open(db_host, db_port):
        print(f"❌ PostgreSQL not listening on {db_host}:{db_port}")
        print("   • On macOS/Homebrew: brew services start postgresql@16")
        return False

    if not check_service_cli("Redis", "redis-cli ping"):
        print("❌ Redis not running. Start it with: brew services start redis")
        return False

    print("✅ Prerequisites OK (Postgres & Redis up)\n")

    # 7) Verify we can import app.main
    print("🔍 Verifying `app.main` can be imported…")
    try:
        __import__("app.main")
        print("✅ app.main imported successfully")
    except Exception as e:
        print(f"❌ Failed to import app.main: {e}")
        print("   Fix the import error above and try again.")
        return False

    # 8) Launch all services
    processes = []
    py = sys.executable  # ensures we use the venv’s Python

    # Main API (give it a bit longer)
    main_port = int(os.getenv("MAIN_API_PORT", "8000"))
    cmd_main = f"{py} -m uvicorn app.main:app --host 0.0.0.0 --port {main_port} --reload"
    p = start_service_in_background("Main API", cmd_main, main_port, wait_seconds=8)
    if p:
        processes.append(("Main API", p))

    # Analysis Service
    analysis_port = int(os.getenv("ANALYSIS_API_PORT", "8001"))
    cmd_analysis = f"{py} -m uvicorn services.analysis_service:app --host 0.0.0.0 --port {analysis_port} --reload"
    p = start_service_in_background("Analysis Service", cmd_analysis, analysis_port)
    if p:
        processes.append(("Analysis Service", p))

    # Email Service
    email_port = int(os.getenv("EMAIL_API_PORT", "8002"))
    cmd_email = f"{py} -m uvicorn services.email_service:app --host 0.0.0.0 --port {email_port} --reload"
    p = start_service_in_background("Email Service", cmd_email, email_port)
    if p:
        processes.append(("Email Service", p))

    # RPA Service
    rpa_port = int(os.getenv("RPA_API_PORT", "8003"))
    cmd_rpa = f"{py} -m uvicorn services.rpa_service:app --host 0.0.0.0 --port {rpa_port} --reload"
    p = start_service_in_background("RPA Service", cmd_rpa, rpa_port)
    if p:
        processes.append(("RPA Service", p))

    # Celery Worker
    cmd_celery = f"{py} -m celery -A workers.tasks.celery_app worker --loglevel=info"
    p = start_service_in_background("Celery Worker", cmd_celery)
    if p:
        processes.append(("Celery Worker", p))

    # 9) Summary & keep-alive
    print("\n🎉 All services have been launched! 🎉\n")
    print("📍 Service URLs:")
    print(f"  • Main API:      http://localhost:{main_port}")
    print(f"  • Analysis API:  http://localhost:{analysis_port}")
    print(f"  • Email API:     http://localhost:{email_port}")
    print(f"  • RPA API:       http://localhost:{rpa_port}")
    print("\n⌨️  Press Ctrl+C to stop all services\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down services…")
        for name, proc in processes:
            print(f"Stopping {name}…")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        print("✅ All services stopped")
    return True


if __name__ == "__main__":
    if not main():
        print("\n💡 If you still see failures:")
        print(" 1. Check the error message above.")
        print(" 2. Ensure `app/main.py` and the `app/` folder live alongside this script.")
        print(" 3. Try manually:")
        print("     source venv/bin/activate")
        print("     uvicorn app.main:app --reload")
        sys.exit(1)