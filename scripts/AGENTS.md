# Local server scripts

`start.sh` and `stop.sh` are for macOS and Linux. `start.ps1` and `stop.ps1` are for Windows PowerShell. They run the FastAPI backend on `127.0.0.1:8000`, store process state and logs in the repository's ignored `.run/` directory, and require `uv` on `PATH`. Build the frontend from `frontend/` before starting the server. The start scripts load the root `.env` into the backend process when the file exists.

Run Unix scripts from any working directory with `sh scripts/start.sh` and `sh scripts/stop.sh`. Run Windows scripts from PowerShell with `.\scripts\start.ps1` and `.\scripts\stop.ps1`.