"""Cross-platform local development runner for ResearchOps.

Team: Spideyx | GATEWAYS 2026
"""

import subprocess
import sys
from pathlib import Path


def main():
    root_dir = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root_dir))
    from backend.app.core.config import settings

    print("=" * 70)
    print(" ResearchOps — Autonomous Healthcare Research Agent")
    print(" Team: Spideyx | GATEWAYS 2026")
    print("=" * 70)
    print(f"Project root: {root_dir}")
    print(f"Python interpreter: {sys.executable}")

    host = settings.API_HOST
    port = settings.API_PORT

    print(f"\n[+] Starting FastAPI backend on http://{host}:{port}")
    print(f"    - Health Check: http://{host}:{port}/api/health")
    print(f"    - API Docs:     http://{host}:{port}/docs")
    print(f"    - Frontend UI:  http://{host}:{port}/ui/")
    print("\nPress Ctrl+C to terminate the development server.\n")

    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.app.main:app",
        "--host",
        host,
        "--port",
        str(port),
    ]
    if settings.DEBUG:
        cmd.append("--reload")

    try:
        subprocess.run(cmd, cwd=str(root_dir), check=False)
    except KeyboardInterrupt:
        print("\n[!] ResearchOps development server stopped.")


if __name__ == "__main__":
    main()
