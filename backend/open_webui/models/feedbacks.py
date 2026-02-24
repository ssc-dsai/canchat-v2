import logging
import time
import uuid

from open_webui.env import SRC_LOG_LEVELS
from open_webui.internal.db_utils import AsyncDatabaseConnector
from open_webui.models.base import Base
from open_webui.models.users import User
from pydantic import BaseModel, ConfigDict
from sqlalchemy import JSON, BigInteger, Text, delete, func, select
from sqlalchemy.orm import Mapped, mapped_column

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


####################
# Feedback DB Schema
####################


class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(BigInteger, default=0)
    type: Mapped[str] = mapped_column(Text)
    data: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)
    snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)
    created_at: Mapped[int] = mapped_column(BigInteger)
    updated_at: Mapped[int] = mapped_column(BigInteger)


class FeedbackModel(BaseModel):
    id: str
    user_id: str
    version: int
    type: str
    data: dict | None = None
    meta: dict | None = None
    snapshot: dict | None = None
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class FeedbackResponse(BaseModel):
    id: str
    user_id: str
    version: int
    type: str
    data: dict | None = None
    meta: dict | None = None
    snapshot: dict | None = None
    created_at: int
    updated_at: int


class RatingData(BaseModel):
    rating: str | int | None = None
    model_id: str | None = None
    sibling_model_ids: list[str] | None = None
    reason: str | None = None
    comment: str | None = None
    model_config = ConfigDict(extra="allow", protected_namespaces=())


class MetaData(BaseModel):
    arena: bool | None = None
    chat_id: str | None = None
    message_id: str | None = None
    tags: list[str] | None = None
    model_config = ConfigDict(extra="allow")


class SnapshotData(BaseModel):
    chat: dict | None = None
    model_config = ConfigDict(extra="allow")


class FeedbackForm(BaseModel):
    type: str
    data: RatingData | None = None
    meta: dict | None = None
    snapshot: SnapshotData | None = None
    model_config = ConfigDict(extra="allow")


class FeedbackTable:
    __db: AsyncDatabaseConnector

    def __init__(self, db_connector: AsyncDatabaseConnector) -> None:
        self.__db = db_connector

    async def insert_new_feedback(
        self, user_id: str, form_data: FeedbackForm
    ) -> FeedbackModel | None:
        async with self.__db.get_async_db() as db:
            id = str(uuid.uuid4())
            feedback = FeedbackModel(
                **{
                    "id": id,
                    "user_id": user_id,
                    "version": 0,
                    **form_data.model_dump(),
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            try:
                result = Feedback(**feedback.model_dump())
                db.add(result)
                await db.commit()
                await db.refresh(result)
                if result:
                    return FeedbackModel.model_validate(result)
                else:
                    return None
            except Exception as e:
                print(e)
                await db.rollback()
                return None

    async def get_feedback_by_id(self, id: str) -> FeedbackModel | None:
        try:
            async with self.__db.get_async_db() as db:
                feedback = await db.scalar(select(Feedback).where(Feedback.id == id))
                if not feedback:
                    return None
                return FeedbackModel.model_validate(feedback)
        except Exception:
            return None

    async def get_feedback_by_id_and_user_id(
        self, id: str, user_id: str
    ) -> FeedbackModel | None:
        try:
            async with self.__db.get_async_db() as db:
                feedback = await db.scalar(
                    select(Feedback).where(
                        Feedback.id == id, Feedback.user_id == user_id
                    )
                )
                if not feedback:
                    return None
                return FeedbackModel.model_validate(feedback)
        except Exception:
            return None

    async def get_all_feedbacks(self) -> list[FeedbackModel]:
        async with self.__db.get_async_db() as db:
            feedbacks = await db.scalars(
                select(Feedback).order_by(Feedback.updated_at.desc())
            )
            return [
                FeedbackModel.model_validate(feedback) for feedback in feedbacks.all()
            ]

    async def get_all_feedbacks_paginated(
        self, page: int = 1, limit: int = 10, search: str | None = None
    ) -> list[FeedbackModel]:
        """Get paginated feedbacks with optional search"""
        async with self.__db.get_async_db() as db:
            # Join with users table to enable username search
            query = select(Feedback).outerjoin(User, Feedback.user_id == User.id)

            # Apply search filter if provided
            if search and search.strip():
                search_term = f"%{search.strip().lower()}%"
                # Search in multiple fields:
                # 1. JSON data fields: model_id, reason, comment
                # 2. JSON data tags array (using JSON path)
                # 3. User name and email
                # 4. Feedback type
                query = query.where(
                    # Search in data JSON fields
                    Feedback.data.op("->>")("model_id").ilike(search_term)
                    | Feedback.data.op("->>")("reason").ilike(search_term)
                    | Feedback.data.op("->>")("comment").ilike(search_term)
                    # Search in tags array (convert to string and search)
                    | Feedback.data.op("->>")("tags").cast(Text).ilike(search_term)
                    # Search in user info
                    | User.name.ilike(search_term)
                    | User.email.ilike(search_term)
                    # Search in feedback type
                    | Feedback.type.ilike(search_term)
                    # Search in meta JSON fields (chat_id, message_id)
                    | Feedback.meta.op("->>")("chat_id").ilike(search_term)
                    | Feedback.meta.op("->>")("message_id").ilike(search_term)
                )

            # Apply pagination
            offset = (page - 1) * limit
            query = (
                query.order_by(Feedback.updated_at.desc()).offset(offset).limit(limit)
            )
            feedbacks = await db.scalars(query)

            return [
                FeedbackModel.model_validate(feedback) for feedback in feedbacks.all()
            ]

    async def get_feedbacks_count(self, search: str = None) -> int:
        """Get total count of feedbacks with optional search filter"""
        async with self.__db.get_async_db() as db:
            # Join with users table to enable username search
            query = (
                select(func.count())
                .select_from(Feedback)
                .outerjoin(User, Feedback.user_id == User.id)
            )

            # Apply search filter if provided
            if search and search.strip():
                search_term = f"%{search.strip().lower()}%"
                # Use same comprehensive search as paginated query
                query = query.where(
                    # Search in data JSON fields
                    Feedback.data.op("->>")("model_id").ilike(search_term)
                    | Feedback.data.op("->>")("reason").ilike(search_term)
                    | Feedback.data.op("->>")("comment").ilike(search_term)
                    # Search in tags array
                    | Feedback.data.op("->>")("tags").cast(Text).ilike(search_term)
                    # Search in user info
                    | User.name.ilike(search_term)
                    | User.email.ilike(search_term)
                    # Search in feedback type
                    | Feedback.type.ilike(search_term)
                    # Search in meta JSON fields
                    | Feedback.meta.op("->>")("chat_id").ilike(search_term)
                    | Feedback.meta.op("->>")("message_id").ilike(search_term)
                )

            count = await db.scalar(query)
            return count if count else 0

    async def get_feedbacks_by_type(self, type: str) -> list[FeedbackModel]:
        async with self.__db.get_async_db() as db:
            feedbacks = await db.scalars(
                select(Feedback)
                .where(Feedback.type == type)
                .order_by(Feedback.updated_at.desc())
            )
            return [
                FeedbackModel.model_validate(feedback) for feedback in feedbacks.all()
            ]

    async def get_feedbacks_by_user_id(self, user_id: str) -> list[FeedbackModel]:
        async with self.__db.get_async_db() as db:
            feedbacks = await db.scalars(
                select(Feedback)
                .filter_by(type=type)
                .order_by(Feedback.updated_at.desc())
            )
            return [
                FeedbackModel.model_validate(feedback) for feedback in feedbacks.all()
            ]

    async def update_feedback_by_id(
        self, id: str, form_data: FeedbackForm
    ) -> FeedbackModel | None:
        async with self.__db.get_async_db() as db:
            feedback = await db.scalar(select(Feedback).where(Feedback.id == id))
            if not feedback:
                return None

            if form_data.data:
                feedback.data = form_data.data.model_dump()
            if form_data.meta:
                feedback.meta = form_data.meta
            if form_data.snapshot:
                feedback.snapshot = form_data.snapshot.model_dump()

            feedback.updated_at = int(time.time())

            await db.commit()
            return FeedbackModel.model_validate(feedback)

    async def update_feedback_by_id_and_user_id(
        self, id: str, user_id: str, form_data: FeedbackForm
    ) -> FeedbackModel | None:
        async with self.__db.get_async_db() as db:
            feedback = await db.scalar(
                select(Feedback).where(Feedback.id == id, Feedback.user_id == user_id)
            )
            if not feedback:
                return None

            if form_data.data:
                feedback.data = form_data.data.model_dump()
            if form_data.meta:
                feedback.meta = form_data.meta
            if form_data.snapshot:
                feedback.snapshot = form_data.snapshot.model_dump()

            feedback.updated_at = int(time.time())

            await db.commit()
            return FeedbackModel.model_validate(feedback)

    async def delete_feedback_by_id(self, id: str) -> bool:
        async with self.__db.get_async_db() as db:
            feedback = await db.scalar(select(Feedback).where(Feedback.id == id))
            if not feedback:
                return False
            await db.delete(feedback)
            await db.commit()
            return True

    async def delete_feedback_by_id_and_user_id(self, id: str, user_id: str) -> bool:
        async with self.__db.get_async_db() as db:
            feedback = await db.scalar(
                select(Feedback).where(Feedback.id == id, Feedback.user_id == user_id)
            )
            if not feedback:
                return False
            await db.delete(feedback)
            await db.commit()
            return True

    async def delete_feedbacks_by_user_id(self, user_id: str) -> bool:
        async with self.__db.get_async_db() as db:
            _ = await db.execute(delete(Feedback).where(Feedback.user_id == user_id))
            await db.commit()
            return True

    async def delete_all_feedbacks(self) -> bool:
        async with self.__db.get_async_db() as db:
            _ = await db.execute(delete(Feedback))
            await db.commit()
            return True
