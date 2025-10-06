from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum
from pathlib import Path

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..session import Base


class SettingMediaType(str, PyEnum):
    image = "image"
    video = "video"


class SettingMedia(Base):
    __tablename__ = "setting_media"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    setting_key: Mapped[str] = mapped_column(
        String(64), ForeignKey("settings.key", ondelete="CASCADE"), nullable=False
    )
    file_path: Mapped[str] = mapped_column(String(255), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    media_type: Mapped[SettingMediaType] = mapped_column(Enum(SettingMediaType), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    setting = relationship("Setting", back_populates="media", lazy="joined")

    @property
    def path(self) -> Path:
        return Path(self.file_path)
