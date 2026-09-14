# uvicorn main:app --reload
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from db.database import get_db

from api.map_replay import router as map_replay_router
from api.map_events import router as map_events_router
from api.facilities import router as facilities_router
from api.alerts import router as alerts_router
app = FastAPI(
    title="Phoenix API",
    description="Phoenix thermal event intelligence API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(map_replay_router)
app.include_router(map_events_router)
app.include_router(facilities_router)
app.include_router(alerts_router)

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "phoenix-api",
    }

@app.get("/health/db")
def database_health(db: Session = Depends(get_db)):
    result = db.execute(
        text("""
            SELECT
                current_database(),
                current_user,
                postgis_full_version()
        """)
    )

    database, user, postgis = result.one()

    return {
        "status": "ok",
        "database": database,
        "user": user,
        "postgis": postgis,
    }


