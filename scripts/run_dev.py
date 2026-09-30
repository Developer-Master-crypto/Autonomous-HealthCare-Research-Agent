"""Cross-platform local development runner for ResearchOps.

Team: Spideyx | GATEWAYS 2026
"""

import sys
import subprocess
from pathlib import Path


def main():
    root_dir = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root_dir))

    print("=" * 70)
    print(" ResearchOps — Autonomous Healthcare Research Agent")
    print(" Team: Spideyx | GATEWAYS 2026")
    print("=" * 70)
    print(f"Project root: {root_dir}")
    print(f"Python interpreter: {sys.executable}")

    host = "127.0.0.1"
    port = 8000

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
        "--reload",
    ]

    try:
        subprocess.run(cmd, cwd=str(root_dir))
    except KeyboardInterrupt:
        print("\n[!] ResearchOps development server stopped.")


if __name__ == "__main__":
    main()
