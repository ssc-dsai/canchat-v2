import logging
import time
import uuid

from open_webui.env import SRC_LOG_LEVELS
from open_webui.internal.db_utils import AsyncDatabaseConnector
from open_webui.models.base import Base
from open_webui.models.files import FileMetadataResponse
from open_webui.models.users import UserResponse, UsersTable
from pydantic import BaseModel, ConfigDict
from sqlalchemy import JSON, BigInteger, Text, delete, select
from sqlalchemy.orm import Mapped, mapped_column

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# Knowledge DB Schema
####################


class Knowledge(Base):
    __tablename__ = "knowledge"

    id: Mapped[str] = mapped_column(Text, unique=True, primary_key=True)
    user_id: Mapped[str] = mapped_column(Text)

    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)

    data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    access_control: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )  # Controls data access levels.
    # Defines access control rules for this entry.
    # - `None`: Public access, available to all users with the "user" role.
    # - `{}`: Private access, restricted exclusively to the owner.
    # - Custom permissions: Specific access control for reading and writing;
    #   Can specify group or user-level restrictions:
    #   {
    #      "read": {
    #          "group_ids": ["group_id1", "group_id2"],
    #          "user_ids":  ["user_id1", "user_id2"]
    #      },
    #      "write": {
    #          "group_ids": ["group_id1", "group_id2"],
    #          "user_ids":  ["user_id1", "user_id2"]
    #      }
    #   }

    created_at: Mapped[int] = mapped_column(BigInteger)
    updated_at: Mapped[int] = mapped_column(BigInteger)


class KnowledgeModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str

    name: str
    description: str

    data: dict | None = None
    meta: dict | None = None

    access_control: dict | None = None

    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch


####################
# Forms
####################


class KnowledgeUserModel(KnowledgeModel):
    user: UserResponse | None = None


class KnowledgeResponse(KnowledgeModel):
    files: list[FileMetadataResponse | dict | None] = None


class KnowledgeUserResponse(KnowledgeUserModel):
    files: list[FileMetadataResponse | dict | None] = None


class KnowledgeForm(BaseModel):
    name: str
    description: str
    data: dict | None = None
    access_control: dict | None = None


class KnowledgeTable:

    __db: AsyncDatabaseConnector
    __users: UsersTable

    def __init__(
        self, db_connector: AsyncDatabaseConnector, users_table: UsersTable
    ) -> None:
        self.__db = db_connector
        self.__users = users_table

    async def insert_new_knowledge(
        self, user_id: str, form_data: KnowledgeForm
    ) -> KnowledgeModel | None:
        async with self.__db.get_async_db() as db:
            knowledge = KnowledgeModel(
                **{
                    **form_data.model_dump(),
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )

            try:
                result = Knowledge(**knowledge.model_dump())
                db.add(result)
                await db.commit()
                await db.refresh(result)
                if result:
                    return KnowledgeModel.model_validate(result)
                else:
                    return None
            except Exception:
                return None

    async def get_knowledge_bases(self) -> list[KnowledgeUserModel]:
        async with self.__db.get_async_db() as db:
            knowledge_bases: list[KnowledgeUserModel] = []
            for knowledge in (
                await db.scalars(
                    select(Knowledge).order_by(Knowledge.updated_at.desc())
                )
            ).all():
                user = await self.__users.get_user_by_id(knowledge.user_id)
                knowledge_bases.append(
                    KnowledgeUserModel.model_validate(
                        {
                            **KnowledgeModel.model_validate(knowledge).model_dump(),
                            "user": user.model_dump() if user else None,
                        }
                    )
                )
            return knowledge_bases

    async def get_knowledge_bases_by_user_id(
        self, user_id: str, permission: str = "write"
    ) -> list[KnowledgeUserModel]:
        from open_webui.utils.access_control import has_access

        knowledge_bases = await self.get_knowledge_bases()
        return [
            knowledge_base
            for knowledge_base in knowledge_bases
            if knowledge_base.user_id == user_id
            or await has_access(user_id, permission, knowledge_base.access_control)
        ]

    async def get_knowledge_by_id(self, id: str) -> KnowledgeModel | None:
        try:
            async with self.__db.get_async_db() as db:
                knowledge = await db.scalar(select(Knowledge).where(Knowledge.id == id))
                return KnowledgeModel.model_validate(knowledge) if knowledge else None
        except Exception:
            return None

    async def update_knowledge_by_id(
        self, id: str, form_data: KnowledgeForm, overwrite: bool = False
    ) -> KnowledgeModel | None:
        try:
            async with self.__db.get_async_db() as db:
                if knowledge := await db.scalar(
                    select(Knowledge).where(Knowledge.id == id)
                ):
                    knowledge.name = form_data.name
                    knowledge.description = form_data.description
                    knowledge.data = form_data.data
                    knowledge.access_control = form_data.access_control

                    await db.commit()
                    await db.refresh(knowledge)
                return KnowledgeModel.model_validate(knowledge) if knowledge else None
        except Exception as e:
            log.exception(e)
            return None

    async def update_knowledge_data_by_id(
        self, id: str, data: dict
    ) -> KnowledgeModel | None:
        try:
            async with self.__db.get_async_db() as db:
                if knowledge := await db.scalar(
                    select(Knowledge).where(Knowledge.id == id)
                ):
                    knowledge.data = data
                    knowledge.updated_at = int(time.time())

                    await db.commit()
                    await db.refresh(knowledge)
                return KnowledgeModel.model_validate(knowledge) if knowledge else None
        except Exception as e:
            log.exception(e)
            return None

    async def delete_knowledge_by_id(self, id: str) -> bool:
        try:
            async with self.__db.get_async_db() as db:
                _ = await db.execute(delete(Knowledge).where(Knowledge.id == id))
                await db.commit()
                return True
        except Exception:
            return False

    async def delete_all_knowledge(self) -> bool:
        try:
            async with self.__db.get_async_db() as db:
                _ = await db.execute(delete(Knowledge))
                await db.commit()
                return True
        except Exception:
            return False
