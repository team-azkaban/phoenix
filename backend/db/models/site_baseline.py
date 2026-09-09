import uuid

from sqlalchemy import Float, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class SiteBaseline(Base):
    __tablename__ = "site_baselines"

    baseline_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    baseline_period: Mapped[str | None] = mapped_column(String)

    observation_count: Mapped[int | None] = mapped_column(Integer)

    mean_frp: Mapped[float | None] = mapped_column(Float)

    median_frp: Mapped[float | None] = mapped_column(Float)

    std_frp: Mapped[float | None] = mapped_column(Float)

    percentile_95_frp: Mapped[float | None] = mapped_column(Float)

    statistics: Mapped[dict | None] = mapped_column(JSONB)