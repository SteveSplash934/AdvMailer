import os
import sys
import subprocess

def main():
    host = os.getenv("HOST", "0.0.0.0")
    port = os.getenv("PORT", "5000")

    if os.name == "nt":
        # Windows OS: Use Waitress WSGI
        print(f"[*] Launching Waitress Production Server on {host}:{port} (Windows)...")
        from waitress import serve
        from app import app
        serve(app, host=host, port=int(port))
    else:
        # Linux / macOS / POSIX OS: Use Gunicorn WSGI
        print(f"[*] Launching Gunicorn Production Server on {host}:{port} (Linux/POSIX)...")
        workers = os.getenv("WORKERS", "4")
        cmd = [
            "gunicorn",
            "app:app",
            f"--bind={host}:{port}",
            f"--workers={workers}",
            "--timeout=120",
            "--access-logfile=-",
            "--error-logfile=-"
        ]
        subprocess.run(cmd)

if __name__ == "__main__":
    main()