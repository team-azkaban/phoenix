# Phoenix Setup Guide

Since your virtual environment is named `venv`, use `venv` everywhere instead of `.venv`.

# Phoenix

Phoenix is a thermal event intelligence platform that turns satellite thermal detections into explainable, facility-aware insights.

## Local Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- npm

### 1. Clone the repository

```bash
git clone <repository-url>
cd phoenix
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv
```

**Activate the virtual environment (Windows PowerShell):**

```powershell
.\venv\Scripts\Activate.ps1
```

**Install dependencies:**

```bash
pip install -r requirements.txt
```

**Start the backend:**

```bash
uvicorn main:app --reload
```

Backend runs at:

```text
http://localhost:8000
```

API docs:

```text
http://localhost:8000/docs
```

### 3. Frontend Setup

Open a new terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at:

```text
http://localhost:5173
```

## Development

Run both applications simultaneously:

```text
Frontend → http://localhost:5173
Backend  → http://localhost:8000
```

The frontend communicates with the backend through the FastAPI API.


---

## Project Structure

````text
phoenix/
├── backend/
│   ├── venv/
│   ├── api/
│   ├── services/
│   ├── models/
│   ├── schemas/
│   ├── ingestion/
│   ├── geo/
│   ├── ml/
│   ├── db/
│   ├── tests/
│   ├── main.py
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   ├── package.json
│   └── ...
│
└── README.md
````

