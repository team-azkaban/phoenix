import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class EventObservation(Base):
    __tablename__ = "event_observations"

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "thermal_events.event_id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    observation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "thermal_observations.observation_id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )