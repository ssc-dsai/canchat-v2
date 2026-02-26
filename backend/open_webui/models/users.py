import time
from logging import getLogger

from open_webui.internal.db_utils import AsyncDatabaseConnector, JSONField
from open_webui.models.base import Base
from open_webui.models.chats import ChatTable
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, String, Text, delete, func, select
from sqlalchemy.orm import Mapped, mapped_column

# Add logger for the users module
logger = getLogger(__name__)

####################
# User DB Schema
####################


class UserSettings(BaseModel):
    ui: dict | None = {}
    model_config = ConfigDict(extra="allow")
    pass


class User(Base):
    __tablename__ = "user"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String)
    profile_image_url: Mapped[str] = mapped_column(Text)
    domain: Mapped[str] = mapped_column(String)

    last_active_at: Mapped[int] = mapped_column(BigInteger)
    updated_at: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[int] = mapped_column(BigInteger)

    api_key: Mapped[str] = mapped_column(String, nullable=True, unique=True)
    settings: Mapped[dict | None] = mapped_column(JSONField, nullable=True)
    info: Mapped[dict | None] = mapped_column(JSONField, nullable=True)

    oauth_sub: Mapped[str] = mapped_column(Text, unique=True)


class UserModel(BaseModel):
    id: str
    name: str
    email: str
    role: str = "pending"
    profile_image_url: str
    domain: str = "*"

    last_active_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch

    api_key: str | None = None
    settings: UserSettings | None = None
    info: dict | None = None

    oauth_sub: str | None = None

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    profile_image_url: str


class UserNameResponse(BaseModel):
    id: str
    name: str
    role: str
    profile_image_url: str


class UserRoleUpdateForm(BaseModel):
    id: str
    role: str


class UserUpdateForm(BaseModel):
    name: str
    email: str
    profile_image_url: str
    password: str | None = None


class UsersTable:

    __db: AsyncDatabaseConnector
    __chats: ChatTable

    def __init__(
        self,
        db_connector: AsyncDatabaseConnector,
        chats: ChatTable,
    ) -> None:
        self.__db = db_connector
        self.__chats = chats

    async def insert_new_user(
        self,
        id: str,
        name: str,
        email: str,
        profile_image_url: str = "/user.png",
        role: str = "pending",
        oauth_sub: str | None = None,
        domain: str = "*",
    ) -> UserModel | None:
        async with self.__db.get_async_db() as db:
            user = UserModel(
                **{
                    "id": id,
                    "name": name,
                    "email": email,
                    "role": role,
                    "profile_image_url": profile_image_url,
                    "domain": domain,
                    "last_active_at": int(time.time()),
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                    "oauth_sub": oauth_sub,
                }
            )
            result = User(**user.model_dump())
            db.add(result)
            await db.commit()
            await db.refresh(result)
            if result:
                return user
            else:
                return None

    async def get_user_by_id(self, id: str) -> UserModel | None:
        try:
            async with self.__db.get_async_db() as db:
                result = await db.execute(select(User).where(User.id == id))
                user = result.scalars().first()
                return UserModel.model_validate(user)
        except Exception:
            return None

    async def get_user_by_api_key(self, api_key: str) -> UserModel | None:
        try:
            async with self.__db.get_async_db() as db:
                result = await db.execute(select(User).where(User.api_key == api_key))
                user = result.scalars().first()
                return UserModel.model_validate(user)
        except Exception:
            return None

    async def get_user_by_email(self, email: str) -> UserModel | None:
        try:
            async with self.__db.get_async_db() as db:
                result = await db.execute(select(User).where(User.email == email))
                user = result.scalars().first()
                return UserModel.model_validate(user)
        except Exception:
            return None

    async def get_user_by_oauth_sub(self, sub: str) -> UserModel | None:
        try:
            async with self.__db.get_async_db() as db:
                result = await db.execute(select(User).where(User.oauth_sub == sub))
                user = result.scalars().first()
                return UserModel.model_validate(user)
        except Exception:
            return None

    async def get_users(
        self, skip: int | None = None, limit: int | None = None
    ) -> list[UserModel]:
        async with self.__db.get_async_db() as db:
            query = select(User).order_by(User.created_at.desc())
            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            result = await db.execute(query)
            users = result.scalars().all()

            return [UserModel.model_validate(user) for user in users]

    async def get_users_by_user_ids(self, user_ids: list[str]) -> list[UserModel]:
        async with self.__db.get_async_db() as db:
            result = await db.execute(select(User).where(User.id.in_(user_ids)))
            users = result.scalars().all()

            return [UserModel.model_validate(user) for user in users]

    async def get_user_domains(self) -> list[str]:
        async with self.__db.get_async_db() as db:
            result = await db.execute(select(User.domain).distinct())

            return [domain[0] for domain in result.all()]

    async def get_num_users(self, domain: str | None = None) -> int | None:
        try:
            async with self.__db.get_async_db() as db:
                statement = select(func.count(User.id))
                if domain:
                    statement = statement.where(User.domain == domain)

                result = await db.execute(statement)
                return result.scalar_one_or_none()
        except Exception:
            return None

    async def get_first_user(self) -> UserModel | None:
        try:
            async with self.__db.get_async_db() as db:
                result = await db.scalar(select(User).order_by(User.created_at.asc()))
                return UserModel.model_validate(result)
        except Exception:
            return None

    async def get_user_webhook_url_by_id(self, id: str) -> str | None:
        try:
            async with self.__db.get_async_db() as db:
                if user := await db.scalar(select(User).where(User.id == id)):
                    if user.settings is None:
                        return None
                    else:
                        settings = user.settings
                        ui = settings.get("ui", {})
                        notifications = ui.get("notifications", {})

                        return notifications.get("webhook_url", None)
        except Exception:
            return None

    async def update_user_role_by_id(self, id: str, role: str) -> UserModel | None:
        try:
            async with self.__db.get_async_db() as db:
                user = await db.scalar(select(User).where(User.id == id))

                if user:
                    user.role = role
                    await db.commit()
                    return UserModel.model_validate(user)
                return None
        except Exception:
            return None

    async def update_user_profile_image_url_by_id(
        self, id: str, profile_image_url: str
    ) -> UserModel | None:
        try:
            async with self.__db.get_async_db() as db:
                user = await db.scalar(select(User).where(User.id == id))

                if user:
                    user.profile_image_url = profile_image_url
                    await db.commit()
                    return UserModel.model_validate(user)
                return None
        except Exception:
            return None

    async def update_user_last_active_by_id(self, id: str) -> UserModel | None:
        try:
            async with self.__db.get_async_db() as db:
                user = await db.scalar(select(User).where(User.id == id))

                if user:
                    user.last_active_at = int(time.time())
                    await db.commit()
                    return UserModel.model_validate(user)
                return None
        except Exception:
            return None

    async def get_daily_users_number(
        self, days: int = 1, domain: str | None = None
    ) -> int | None:
        try:
            async with self.__db.get_async_db() as db:
                start_time = int(time.time()) - (days * 24 * 60 * 60)
                query = (
                    select(func.count())
                    .select_from(User)
                    .where(User.last_active_at >= start_time)
                )

                if domain:
                    query = query.where(User.domain == domain)

                return await db.scalar(query)

        except Exception as e:
            logger.error(f"Failed to get daily users number: {e}")
            return None

    async def update_user_oauth_sub_by_id(
        self, id: str, oauth_sub: str
    ) -> UserModel | None:
        try:
            async with self.__db.get_async_db() as db:
                user = await db.scalar(select(User).where(User.id == id))

                if user:
                    user.oauth_sub = oauth_sub
                    await db.commit()
                    return UserModel.model_validate(user)
                return None
        except Exception:
            return None

    async def update_user_by_id(self, id: str, updated: dict) -> UserModel | None:
        try:
            async with self.__db.get_async_db() as db:
                user = await db.scalar(select(User).where(User.id == id))

                if user:
                    for key, value in updated.items():
                        if hasattr(user, key):
                            setattr(user, key, value)
                        else:
                            logger.error(f"{key} is not a valid attribute of User")

                    await db.commit()
                    await db.refresh(user)
                    return UserModel.model_validate(user)
                return None
        except Exception:
            return None

    async def delete_user_by_id(self, id: str) -> bool:
        try:
            # Delete User Chats
            _ = await self.__chats.delete_chats_by_user_id(id)
            async with self.__db.get_async_db() as db:
                # Delete User
                _ = await db.execute(delete(User).where(User.id == id))
                await db.commit()

            return True
        except Exception:
            return False

    async def update_user_api_key_by_id(self, id: str, api_key: str) -> bool:
        try:
            async with self.__db.get_async_db() as db:
                if user := await db.scalar(select(User).where(User.id == id)):
                    user.api_key = api_key
                    await db.commit()
                    await db.refresh(user)
                    return True
                return False
        except Exception:
            return False

    async def get_user_api_key_by_id(self, id: str) -> str | None:
        try:
            async with self.__db.get_async_db() as db:
                if user := await db.scalar(select(User).where(User.id == id)):
                    return user.api_key
                return None
        except Exception:
            return None

    async def get_valid_user_ids(self, user_ids: list[str]) -> list[str]:
        async with self.__db.get_async_db() as db:
            users = await db.scalars(select(User).where(User.id.in_(user_ids)))
            return [user.id for user in users.all()]

    async def get_historical_users_data(
        self, days: int = 7, domain: str | None = None
    ) -> list[dict[str, str | int]]:
        try:
            result: list[dict[str, str | int]] = []
            current_time = int(time.time())

            # Calculate today's date at midnight for proper day boundary
            today = time.strftime("%Y-%m-%d", time.localtime(current_time))
            today_midnight = int(
                time.mktime(time.strptime(f"{today} 00:00:00", "%Y-%m-%d %H:%M:%S"))
            )

            # Generate all date strings first to ensure no gaps
            date_strings: list[str] = []
            dates_timestamps: list[int] = []
            for day in range(days):
                # Calculate day start (midnight) for each day in the past
                day_start = today_midnight - (day * 24 * 60 * 60)
                date_str = time.strftime("%Y-%m-%d", time.localtime(day_start))
                date_strings.append(date_str)
                dates_timestamps.append(day_start)

            # Sort date strings to ensure chronological order
            date_pairs = sorted(zip(date_strings, dates_timestamps))
            date_strings = [pair[0] for pair in date_pairs]
            dates_timestamps = [pair[1] for pair in date_pairs]

            # Process each day individually
            for i, (date_str, day_start) in enumerate(
                zip(date_strings, dates_timestamps)
            ):
                # Calculate day boundaries (midnight to midnight)
                start_time = day_start
                end_time = start_time + (24 * 60 * 60)

                async with self.__db.get_async_db() as db:
                    query = (
                        select(func.count())
                        .select_from(User)
                        .where(
                            User.created_at < end_time,
                        )
                    )

                    if domain:
                        query = query.where(User.domain == domain)

                    count = await db.scalar(query)

                    result.append({"date": date_str, "count": count if count else 0})

            # Return in chronological order
            return result
        except Exception as e:
            logger.error(f"Failed to get historical users data: {e}")
            # Generate continuous date range as fallback
            fallback: list[dict[str, str | int]] = []
            today = time.strftime("%Y-%m-%d", time.localtime(current_time))
            today_midnight = int(
                time.mktime(time.strptime(f"{today} 00:00:00", "%Y-%m-%d %H:%M:%S"))
            )

            for day in range(days):
                day_start = today_midnight - (day * 24 * 60 * 60)
                date_str = time.strftime("%Y-%m-%d", time.localtime(day_start))
                fallback.append({"date": date_str, "count": 0})

            return sorted(fallback, key=lambda x: x["date"])

    async def get_range_metrics(
        self, start_timestamp: int, end_timestamp: int, domain: str | None = None
    ) -> dict[str, int]:
        """Get user metrics for a specific date range"""
        try:
            async with self.__db.get_async_db() as db:
                # Get the total count of users active in the range
                query = (
                    select(func.count())
                    .select_from(User)
                    .where(
                        User.last_active_at >= start_timestamp,
                        User.last_active_at < end_timestamp,
                    )
                )

                if domain:
                    query = query.where(User.domain == domain)

                active_users = await db.scalar(query)

                # Get the total count of all users (for domain if specified)
                total_query = select(func.count()).select_from(User)
                if domain:
                    total_query = total_query.filter(User.domain == domain)

                total_users = await db.scalar(total_query)

                return {
                    "total_users": total_users if total_users else 0,
                    "active_users": active_users if active_users else 0,
                }
        except Exception as e:
            logger.error(f"Failed to get range metrics: {e}")
            return {"total_users": 0, "active_users": 0}
