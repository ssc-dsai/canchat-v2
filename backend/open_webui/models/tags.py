import logging

from open_webui.internal.db import get_async_db
from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.base import Base

from pydantic import BaseModel, ConfigDict
from sqlalchemy import delete, JSON, PrimaryKeyConstraint, select, String
from sqlalchemy.orm import Mapped, mapped_column

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


####################
# Tag DB Schema
####################
class Tag(Base):
    __tablename__ = "tag"
    id: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    user_id: Mapped[str] = mapped_column(String)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Unique constraint ensuring (id, user_id) is unique, not just the `id` column
    __table_args__ = (PrimaryKeyConstraint("id", "user_id", name="pk_id_user_id"),)


class TagModel(BaseModel):
    id: str
    name: str
    user_id: str
    meta: dict | None = None
    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class TagChatIdForm(BaseModel):
    name: str
    chat_id: str


class TagTable:
    async def insert_new_tag(self, name: str, user_id: str) -> TagModel | None:
        async with get_async_db() as db:
            id = name.replace(" ", "_").lower()
            tag = TagModel(**{"id": id, "user_id": user_id, "name": name})
            try:
                result = Tag(**tag.model_dump())
                db.add(result)
                await db.commit()
                await db.refresh(result)
                if result:
                    return TagModel.model_validate(result)
                else:
                    return None
            except Exception as e:
                print(e)
                return None

    async def get_tag_by_name_and_user_id(
        self, name: str, user_id: str
    ) -> TagModel | None:
        try:
            id = name.replace(" ", "_").lower()
            async with get_async_db() as db:
                if tag := await db.scalar(
                    select(Tag).where(Tag.id == id, Tag.user_id == user_id)
                ):
                    return TagModel.model_validate(tag)
                return None
        except Exception:
            return None

    async def get_tags_by_user_id(self, user_id: str) -> list[TagModel]:
        async with get_async_db() as db:
            tags = await db.scalars(select(Tag).where(Tag.user_id == user_id))
            return [TagModel.model_validate(tag) for tag in tags.all()]

    async def get_tags_by_ids_and_user_id(
        self, ids: list[str], user_id: str
    ) -> list[TagModel]:
        async with get_async_db() as db:
            tags = await db.scalars(
                select(Tag).where(Tag.id.in_(ids), Tag.user_id == user_id)
            )
            return [TagModel.model_validate(tag) for tag in tags.all()]

    async def delete_tag_by_name_and_user_id(self, name: str, user_id: str) -> bool:
        try:
            async with get_async_db() as db:
                id = name.replace(" ", "_").lower()
                res = await db.execute(
                    delete(Tag).where(Tag.id == id, Tag.user_id == user_id)
                )
                log.debug(f"res: {res}")
                await db.commit()
                return True
        except Exception as e:
            log.error(f"delete_tag: {e}")
            return False


Tags = TagTable()
