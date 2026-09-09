# uvicorn main:app --reload
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from db.database import get_db
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


