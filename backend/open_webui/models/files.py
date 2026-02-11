import logging
import time

from open_webui.internal.db import get_async_db
from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.base import Base
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, delete, select, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# Files DB Schema
####################


class File(Base):
    __tablename__ = "file"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String)
    hash: Mapped[str | None] = mapped_column(Text, nullable=True)

    filename: Mapped[str] = mapped_column(Text)
    path: Mapped[str | None] = mapped_column(Text, nullable=True)

    data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    access_control: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[int] = mapped_column(BigInteger)
    updated_at: Mapped[int] = mapped_column(BigInteger)


class FileModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    hash: str | None = None

    filename: str
    path: str | None = None

    data: dict | None = None
    meta: dict | None = None

    access_control: dict | None = None

    created_at: int | None  # timestamp in epoch
    updated_at: int | None  # timestamp in epoch


####################
# Forms
####################


class FileMeta(BaseModel):
    name: str | None = None
    content_type: str | None = None
    size: int | None = None

    model_config = ConfigDict(extra="allow")


class FileModelResponse(BaseModel):
    id: str
    user_id: str
    hash: str | None = None

    filename: str
    data: dict | None = None
    meta: FileMeta

    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch

    model_config = ConfigDict(extra="allow")


class FileMetadataResponse(BaseModel):
    id: str
    meta: dict
    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch


class FileForm(BaseModel):
    id: str
    hash: str | None = None
    filename: str
    path: str
    data: dict = {}
    meta: dict = {}
    access_control: dict | None = None


class FilesTable:
    async def insert_new_file(
        self, user_id: str, form_data: FileForm
    ) -> FileModel | None:
        async with get_async_db() as db:
            file = FileModel(
                **{
                    **form_data.model_dump(),
                    "user_id": user_id,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )

            try:
                result = File(**file.model_dump())
                db.add(result)
                await db.commit()
                await db.refresh(result)
                if result:
                    return FileModel.model_validate(result)
                else:
                    return None
            except Exception as e:
                print(f"Error creating tool: {e}")
                return None

    async def get_file_by_id(self, id: str) -> FileModel | None:
        async with get_async_db() as db:
            try:
                file = await db.get(File, id)
                return FileModel.model_validate(file)
            except Exception:
                return None

    async def get_file_metadata_by_id(self, id: str) -> FileMetadataResponse | None:
        async with get_async_db() as db:
            try:
                file = await db.get(File, id)
                if file:
                    return FileMetadataResponse(
                        id=file.id,
                        meta=file.meta,
                        created_at=file.created_at,
                        updated_at=file.updated_at,
                    )
                return None
            except Exception:
                return None

    async def get_files(self) -> list[FileModel]:
        async with get_async_db() as db:
            files = await db.scalars(select(File))
            return [FileModel.model_validate(file) for file in files.all()]

    async def get_files_by_ids(self, ids: list[str]) -> list[FileModel]:
        async with get_async_db() as db:
            files = await db.scalars(
                select(File).where(File.id.in_(ids)).order_by(File.updated_at.desc())
            )
            return [FileModel.model_validate(file) for file in files.all()]

    async def get_file_metadatas_by_ids(
        self, ids: list[str]
    ) -> list[FileMetadataResponse]:
        async with get_async_db() as db:
            query = (
                select(File.id, File.meta, File.created_at, File.updated_at)
                .where(File.id.in_(ids))
                .order_by(File.updated_at.desc())
            )
            files = await db.execute(query)

            return [
                FileMetadataResponse(
                    id=id,
                    meta=meta,
                    created_at=created_at,
                    updated_at=updated_at,
                )
                for id, meta, created_at, updated_at in files.all()
            ]

    async def get_files_by_user_id(self, user_id: str) -> list[FileModel]:
        async with get_async_db() as db:
            files = await db.scalars(select(File).where(File.user_id == user_id))
            return [FileModel.model_validate(file) for file in files.all()]

    async def update_file_hash_by_id(self, id: str, hash: str) -> FileModel | None:
        async with get_async_db() as db:
            try:
                file = await db.scalar(select(File).where(File.id == id))

                if file:
                    file.hash = hash
                    await db.commit()
                    await db.refresh(file)
                    return FileModel.model_validate(file)
                return None
            except Exception:
                return None

    async def update_file_data_by_id(self, id: str, data: dict) -> FileModel | None:
        async with get_async_db() as db:
            try:
                file = await db.scalar(select(File).where(File.id == id))

                if file:
                    file.data = {**(file.data if file.data else {}), **data}
                    await db.commit()
                    await db.refresh(file)
                    return FileModel.model_validate(file)
                return None
            except Exception:
                return None

    async def update_file_metadata_by_id(self, id: str, meta: dict) -> FileModel | None:
        async with get_async_db() as db:
            try:
                file = await db.scalar(select(File).where(File.id == id))

                if file:
                    file.meta = {**(file.meta if file.meta else {}), **meta}
                    await db.commit()
                    await db.refresh(file)
                    return FileModel.model_validate(file)
                return None
            except Exception:
                return None

    async def delete_file_by_id(self, id: str) -> bool:
        async with get_async_db() as db:
            try:
                _ = await db.execute(delete(File).where(File.id == id))
                await db.commit()
                return True
            except Exception as e:
                log.error(e)
                return False

    async def delete_all_files(self) -> bool:
        async with get_async_db() as db:
            try:
                _ = await db.scalar(delete(File))
                await db.commit()
                return True
            except Exception:
                return False


Files = FilesTable()
