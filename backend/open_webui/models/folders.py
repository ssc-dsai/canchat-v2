import logging
import time
import uuid

from open_webui.internal.db import get_async_db
from open_webui.models.chats import Chats
from open_webui.models.base import Base

from open_webui.env import SRC_LOG_LEVELS
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, JSON, select, Text
from sqlalchemy.orm import Mapped, mapped_column

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


####################
# Folder DB Schema
####################


class Folder(Base):
    __tablename__ = "folder"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    parent_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    items: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_expanded: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[int] = mapped_column(BigInteger)
    updated_at: Mapped[int] = mapped_column(BigInteger)


class FolderModel(BaseModel):
    id: str
    parent_id: str | None = None
    user_id: str
    name: str
    items: dict | None = None
    meta: dict | None = None
    is_expanded: bool = False
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class FolderForm(BaseModel):
    name: str
    model_config = ConfigDict(extra="allow")


class FolderTable:
    async def insert_new_folder(
        self, user_id: str, name: str, parent_id: str | None = None
    ) -> FolderModel | None:
        async with get_async_db() as db:
            id = str(uuid.uuid4())
            folder = FolderModel(
                **{
                    "id": id,
                    "user_id": user_id,
                    "name": name,
                    "parent_id": parent_id,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            try:
                result = Folder(**folder.model_dump())
                db.add(result)
                await db.commit()
                await db.refresh(result)
                if result:
                    return FolderModel.model_validate(result)
                else:
                    return None
            except Exception as e:
                print(e)
                return None

    async def get_folder_by_id_and_user_id(
        self, id: str, user_id: str
    ) -> FolderModel | None:
        try:
            async with get_async_db() as db:
                folder = await db.scalar(
                    select(Folder).where(Folder.id == id, Folder.user_id == user_id)
                )

                if not folder:
                    return None

                return FolderModel.model_validate(folder)
        except Exception:
            return None

    async def get_children_folders_by_id_and_user_id(
        self, id: str, user_id: str
    ) -> list[FolderModel]:
        try:
            async with get_async_db() as db:
                folders: list[FolderModel] = []

                async def get_children(folder: Folder | FolderModel):
                    children = await self.get_folders_by_parent_id_and_user_id(
                        folder.id, user_id
                    )
                    for child in children:
                        await get_children(child)
                        folders.append(child)

                folder = await db.scalar(
                    select(Folder).where(Folder.id == id, Folder.user_id == user_id)
                )
                if not folder:
                    return []

                await get_children(folder)
                return folders
        except Exception:
            return []

    async def get_folders_by_user_id(self, user_id: str) -> list[FolderModel]:
        async with get_async_db() as db:
            folders = await db.scalars(select(Folder).where(Folder.user_id == user_id))
            return [FolderModel.model_validate(folder) for folder in folders.all()]

    async def get_folder_by_parent_id_and_user_id_and_name(
        self, parent_id: str | None, user_id: str, name: str
    ) -> FolderModel | None:
        try:
            async with get_async_db() as db:
                # Check if folder exists
                folder = await db.scalar(
                    select(Folder).where(
                        Folder.parent_id == parent_id,
                        Folder.user_id == user_id,
                        Folder.name.ilike(name),
                    )
                )

                if not folder:
                    return None

                return FolderModel.model_validate(folder)
        except Exception as e:
            log.error(f"get_folder_by_parent_id_and_user_id_and_name: {e}")
            return None

    async def get_folders_by_parent_id_and_user_id(
        self, parent_id: str | None, user_id: str
    ) -> list[FolderModel]:
        async with get_async_db() as db:
            folders = await db.scalars(
                select(Folder).where(
                    Folder.parent_id == parent_id, Folder.user_id == user_id
                )
            )
            return [FolderModel.model_validate(folder) for folder in folders.all()]

    async def update_folder_parent_id_by_id_and_user_id(
        self,
        id: str,
        user_id: str,
        parent_id: str,
    ) -> FolderModel | None:
        try:
            async with get_async_db() as db:
                folder = await db.scalar(
                    select(Folder).where(Folder.id == id, Folder.user_id == user_id)
                )

                if not folder:
                    return None

                folder.parent_id = parent_id
                folder.updated_at = int(time.time())

                await db.commit()

                return FolderModel.model_validate(folder)
        except Exception as e:
            log.error(f"update_folder: {e}")
            return

    async def update_folder_name_by_id_and_user_id(
        self, id: str, user_id: str, name: str
    ) -> FolderModel | None:
        try:
            async with get_async_db() as db:
                folder = await db.scalar(
                    select(Folder).where(Folder.id == id, Folder.user_id == user_id)
                )

                if not folder:
                    return None

                existing_folder = await db.scalar(
                    select(Folder).where(
                        Folder.name == name,
                        Folder.parent_id == folder.parent_id,
                        Folder.user_id == user_id,
                    )
                )

                if existing_folder:
                    return None

                folder.name = name
                folder.updated_at = int(time.time())

                await db.commit()

                return FolderModel.model_validate(folder)
        except Exception as e:
            log.error(f"update_folder: {e}")
            return

    async def update_folder_is_expanded_by_id_and_user_id(
        self, id: str, user_id: str, is_expanded: bool
    ) -> FolderModel | None:
        try:
            async with get_async_db() as db:
                folder = await db.scalar(
                    select(Folder).where(Folder.id == id, Folder.user_id == user_id)
                )

                if not folder:
                    return None

                folder.is_expanded = is_expanded
                folder.updated_at = int(time.time())

                await db.commit()

                return FolderModel.model_validate(folder)
        except Exception as e:
            log.error(f"update_folder: {e}")
            return

    async def delete_folder_by_id_and_user_id(self, id: str, user_id: str) -> bool:
        try:
            async with get_async_db() as db:
                folder = await db.scalar(
                    select(Folder).where(Folder.id == id, Folder.user_id == user_id)
                )

                if not folder:
                    return False

                # Delete all chats in the folder
                await Chats.delete_chats_by_user_id_and_folder_id(user_id, folder.id)

                # Delete all children folders
                async def delete_children(folder: Folder | FolderModel):
                    folder_children = await self.get_folders_by_parent_id_and_user_id(
                        folder.id, user_id
                    )
                    for folder_child in folder_children:
                        await Chats.delete_chats_by_user_id_and_folder_id(
                            user_id, folder_child.id
                        )
                        await delete_children(folder_child)

                        folder = await db.scalar(
                            select(Folder).where(Folder.id == folder_child.id)
                        )
                        await db.delete(folder)
                        await db.commit()

                await delete_children(folder)
                await db.delete(folder)
                await db.commit()
                return True
        except Exception as e:
            log.error(f"delete_folder: {e}")
            return False


Folders = FolderTable()
