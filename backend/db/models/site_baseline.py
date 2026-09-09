import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class SiteBaseline(Base):
    __tablename__ = "site_baselines"

    baseline_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "facilities.facility_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        unique=True,
    )

    baseline_frp: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    frp_std: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    typical_active_hours: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    typical_duration: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    seasonal_pattern: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    historical_event_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
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