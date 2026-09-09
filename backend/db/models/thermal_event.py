import uuid
from datetime import datetime

from geoalchemy2 import Geography
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class ThermalEvent(Base):
    __tablename__ = "thermal_events"

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    last_seen: Mapped[datetime] = mapped_column(
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

    geometry: Mapped[object | None] = mapped_column(
        Geography(
            geometry_type="POINT",
            srid=4326,
            spatial_index=True,
        ),
        nullable=True,
    )

    observation_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )

    facility_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "facilities.facility_id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    facility_distance_m: Mapped[float | None] = mapped_column(Float)

    facility_type: Mapped[str | None] = mapped_column(String)

    landcover_class: Mapped[str | None] = mapped_column(String)

    built_up_fraction: Mapped[float | None] = mapped_column(Float)

    forest_fraction: Mapped[float | None] = mapped_column(Float)

    cropland_fraction: Mapped[float | None] = mapped_column(Float)

    current_frp: Mapped[float | None] = mapped_column(Float)

    max_frp: Mapped[float | None] = mapped_column(Float)

    mean_frp: Mapped[float | None] = mapped_column(Float)

    frp_growth: Mapped[float | None] = mapped_column(Float)

    duration: Mapped[float | None] = mapped_column(Float)

    baseline_frp: Mapped[float | None] = mapped_column(Float)

    baseline_deviation: Mapped[float | None] = mapped_column(Float)

    anomaly_state: Mapped[str | None] = mapped_column(String)

    classification: Mapped[str | None] = mapped_column(String)

    classification_confidence: Mapped[float | None] = mapped_column(Float)

    classification_reasons: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    satellite_image_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    image_confirmation: Mapped[str | None] = mapped_column(String)

    image_notes: Mapped[str | None] = mapped_column(Text)

    emissions_estimate: Mapped[float | None] = mapped_column(Float)

    emissions_method: Mapped[str | None] = mapped_column(String)

    population_exposed: Mapped[float | None] = mapped_column(Float)

    wind_speed: Mapped[float | None] = mapped_column(Float)

    wind_direction: Mapped[float | None] = mapped_column(Float)

    spread_geometry: Mapped[object | None] = mapped_column(
        Geography(
            geometry_type="POLYGON",
            srid=4326,
        ),
        nullable=True,
    )

    risk_score: Mapped[float | None] = mapped_column(Float)

    severity: Mapped[str | None] = mapped_column(String)

    risk_reasons: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    alert_status: Mapped[str | None] = mapped_column(String)

    alert_reasons: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
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