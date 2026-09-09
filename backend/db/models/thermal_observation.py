import uuid
from datetime import datetime

from geoalchemy2 import Geography
from sqlalchemy import DateTime, Float, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class ThermalObservation(Base):
    __tablename__ = "thermal_observations"

    observation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    latitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    longitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    sensor: Mapped[str | None] = mapped_column(String)

    satellite: Mapped[str | None] = mapped_column(String)

    frp: Mapped[float | None] = mapped_column(Float)

    brightness_temperature: Mapped[float | None] = mapped_column(Float)

    confidence: Mapped[str | None] = mapped_column(String)

    day_night: Mapped[str | None] = mapped_column(String)

    source: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    source_record_id: Mapped[str | None] = mapped_column(String)

    geometry: Mapped[object] = mapped_column(
        Geography(
            geometry_type="POINT",
            srid=4326,
            spatial_index=True,
        ),
        nullable=False,
    )