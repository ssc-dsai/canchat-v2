import time
from typing import Optional
import uuid
from pydantic import BaseModel
from sqlalchemy import BigInteger, Integer, select, Text
from sqlalchemy.orm import Mapped, mapped_column

from open_webui.internal.db import get_async_db
from open_webui.models.base import Base
from logging import getLogger

logger = getLogger(__name__)


class ExportLog(Base):
    __tablename__ = "export_logs"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str] = mapped_column(Text)
    email_domain: Mapped[str] = mapped_column(Text)
    export_timestamp: Mapped[int] = mapped_column(BigInteger)
    file_size: Mapped[int] = mapped_column(BigInteger)
    row_count: Mapped[int] = mapped_column(Integer)
    date_range_start: Mapped[int] = mapped_column(BigInteger)
    date_range_end: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[int] = mapped_column(BigInteger)


class ExportLogModel(BaseModel):
    id: str
    user_id: str
    email_domain: str
    export_timestamp: int
    file_size: int
    row_count: int
    date_range_start: int
    date_range_end: int
    created_at: int


class ExportLogForm(BaseModel):
    user_id: str
    email_domain: str
    file_size: int
    row_count: int
    date_range_start: int
    date_range_end: int


class ExportLogsTable:
    async def insert_new_export_log(
        self, form_data: ExportLogForm
    ) -> Optional[ExportLogModel]:
        async with get_async_db() as db:
            try:
                id = str(uuid.uuid4())
                export_timestamp = int(time.time())
                created_at = int(time.time())

                export_log = ExportLog(
                    id=id,
                    user_id=form_data.user_id,
                    email_domain=form_data.email_domain,
                    export_timestamp=export_timestamp,
                    file_size=form_data.file_size,
                    row_count=form_data.row_count,
                    date_range_start=form_data.date_range_start,
                    date_range_end=form_data.date_range_end,
                    created_at=created_at,
                )

                db.add(export_log)
                await db.commit()
                await db.refresh(export_log)

                return ExportLogModel.model_validate(export_log)
            except Exception as e:
                logger.error(f"Error inserting export log: {e}")
                return None

    async def get_export_logs_by_user(self, user_id: str) -> list[ExportLogModel]:
        async with get_async_db() as db:
            try:
                export_logs = await db.scalars(
                    select(ExportLog).where(ExportLog.user_id == user_id)
                )
                return [ExportLogModel.model_validate(log) for log in export_logs.all()]
            except Exception as e:
                logger.error(f"Error getting export logs for user {user_id}: {e}")
                return []

    async def get_all_export_logs(self) -> list[ExportLogModel]:
        async with get_async_db() as db:
            try:
                export_logs = await db.scalars(select(ExportLog))
                return [ExportLogModel.model_validate(log) for log in export_logs.all()]
            except Exception as e:
                logger.error(f"Error getting all export logs: {e}")
                return []


ExportLogs = ExportLogsTable()
