import uuid

from geoalchemy2 import Geography
from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class Facility(Base):
    __tablename__ = "facilities"

    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
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

    geometry: Mapped[object] = mapped_column(
        Geography(
            geometry_type="POINT",
            srid=4326,
            spatial_index=True,
        ),
        nullable=False,
    )

    source: Mapped[str | None] = mapped_column(String)

    baseline_stats: Mapped[dict | None] = mapped_column(JSONB)

    historical_event_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    anomalous_event_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    current_risk: Mapped[float | None] = mapped_column(Float)

    cumulative_emissions: Mapped[float | None] = mapped_column(Float)

    last_incident: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True)
    )