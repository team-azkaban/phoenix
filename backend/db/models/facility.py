import uuid
from datetime import datetime

from geoalchemy2 import Geography
from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class Facility(Base):
    __tablename__ = "facilities"

    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    operator: Mapped[str | None] = mapped_column(String)

    facility_type: Mapped[str | None] = mapped_column(String)

    latitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    longitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    geometry: Mapped[object | None] = mapped_column(
        Geography(
            geometry_type="POINT",
            srid=4326,
            spatial_index=True,
        ),
        nullable=True,
    )

    source: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    baseline_stats: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    historical_event_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )

    anomalous_event_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )

    current_risk: Mapped[float | None] = mapped_column(Float)

    cumulative_emissions: Mapped[float | None] = mapped_column(Float)

    last_incident: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )