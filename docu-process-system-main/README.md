# Document Processing System

This repository contains a set of FastAPI services and a Celery worker for processing documents locally with and without Docker.

## Prerequisites

* **Python 3.10+** (tested on 3.11)
* **PostgreSQL 16+** running on `localhost:5432`
* **Redis** running on `localhost:6379`
* `pip` and `virtualenv`

### Installing PostgreSQL

* **macOS (Homebrew)**

  ```bash
  brew install postgresql@16
  brew services start postgresql@16
  ```
* **Windows**

  1. Download the installer from [https://www.postgresql.org/download/windows/](https://www.postgresql.org/download/windows/)
  2. Run the MSI and follow the setup prompts.
  3. Ensure the **postgresql** service is running via the Windows Services panel.

### Installing Redis

* **macOS (Homebrew)**

  ```bash
  brew install redis
  brew services start redis
  ```
* **Windows**

  1. Download the latest release from [https://github.com/microsoftarchive/redis/releases](https://github.com/microsoftarchive/redis/releases)
  2. Extract and install the service with:

     ```powershell
     redis-server --service-install redis.windows.conf --loglevel verbose
     ```
  3. Start the Redis service:

     ```powershell
     redis-cli ping
     ```

     should return **PONG**.

## Repository Layout

```
├── app/                      # Main API service (FastAPI)
├── services/                 # Analysis, Email, RPA service modules
├── workers/                  # Celery tasks
├── local_startup.py          # Top-level script to launch all services
├── requirements.txt          # Python dependencies
└── README.md                 # You are here
```

## Setup

1. **Clone the repo**

   ```bash
   git clone https://github.com/vivekr1982/docu-process-system.git
   cd docu-process-system
   ```

2. **Create & activate a virtual environment**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**

   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Ensure environment variables are set**

   * Your `.env` is already in place; confirm the following keys are defined:

     ```dotenv
     DATABASE_URL=postgresql://<user>:<password>@localhost:5432/docuprocess
     REDIS_URL=redis://localhost:6379/0

     # Optional overrides (defaults work if running locally)
     MAIN_API_PORT=8000
     ANALYSIS_API_PORT=8001
     EMAIL_API_PORT=8002
     RPA_API_PORT=8003
     ```

## Running Locally

Simply run the helper script to launch all services and the Celery worker:

```bash
python local_startup.py
```

You should see output like:

```
🚀 Document Processing System (Local Mode)
🔍 Checking prerequisites… ✅ OK
🚀 Starting 'Main API' → `python -m uvicorn app.main:app --reload`
✅ Main API is now listening on port 8000
🚀 Starting 'Analysis Service' → …
✅ Analysis Service is now listening on port 8001
…
🎉 All services have been launched!
📍 Service URLs:
  • Main API:      http://localhost:8000
  • Analysis API:  http://localhost:8001
  • Email API:     http://localhost:8002
  • RPA API:       http://localhost:8003
⌨️  Press Ctrl+C to stop all services
```

## Running with Docker

If you prefer Docker Compose, you can start all services using the provided `run.py` script:

1. Ensure you have Docker and Docker Compose installed.
2. From the project root, build and start containers:

   ```bash
   python run.py
   ```
3. This will create the necessary folders (`robot_folder`, `logs`) and run:

   ```bash
   docker-compose up -d
   ```
4. Once complete, access services at:

   * Main API:            [http://localhost:8000](http://localhost:8000)
   * Analysis Service:    [http://localhost:8001](http://localhost:8001)
   * Email Service:       [http://localhost:8002](http://localhost:8002)
   * RPA Service:         [http://localhost:8003](http://localhost:8003)

## Stopping Services

Press **Ctrl+C** in the terminal where `local_startup.py` is running. All subprocesses (APIs & Celery) will be terminated gracefully.

## Troubleshooting

* **PostgreSQL not listening**:
  Ensure the database is running:

  ```bash
  # macOS/Homebrew
  brew services start postgresql@16
  # Ubuntu/Linux
  sudo systemctl start postgresql
  ```
* **Redis not running**:

  ```bash
  # macOS/Homebrew
  brew services start redis
  # Ubuntu/Linux
  sudo systemctl start redis-server
  ```
* **Import errors**:
  Make sure your working directory contains `app/main.py` and the `app/` folder.
  Run `uvicorn app.main:app --reload` manually to see stack traces.
* **Ports in use**:
  If ports `8000`–`8003` are occupied, override in `.env`:

  ```dotenv
  MAIN_API_PORT=9000
  ```

---
