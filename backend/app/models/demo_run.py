from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DemoRun(Base):
    __tablename__ = "demo_runs"

    session_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    scenario: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    cursor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    next_step_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    sandbox: Mapped[dict] = mapped_column(JSONB, nullable=False)
    steps: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
