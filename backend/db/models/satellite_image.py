import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class SatelliteImage(Base):
    __tablename__ = "satellite_images"

    satellite_image_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    satellite: Mapped[str | None] = mapped_column(String)

    acquisition_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    image_url: Mapped[str | None] = mapped_column(String)

    confirmation: Mapped[str | None] = mapped_column(String)

    notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )