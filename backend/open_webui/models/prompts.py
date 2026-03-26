import logging
import time

from open_webui.env import SRC_LOG_LEVELS
from open_webui.internal.db_utils import AsyncDatabaseConnector
from open_webui.models.base import Base
from open_webui.models.users import User, UserModel, UserResponse, UsersTable
from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    JSON,
    BigInteger,
    String,
    Text,
    cast,
    delete,
    func,
    or_,
    select,
)
from sqlalchemy.orm import Mapped, mapped_column

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# Prompts DB Schema
####################


class Prompt(Base):
    __tablename__ = "prompt"

    command: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[int] = mapped_column(BigInteger)

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


class PromptModel(BaseModel):
    command: str
    user_id: str
    title: str
    content: str
    timestamp: int  # timestamp in epoch

    access_control: dict | None = None
    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class PromptUserResponse(PromptModel):
    user: UserResponse | None = None


class PromptForm(BaseModel):
    command: str
    title: str
    content: str
    access_control: dict | None = None


class PromptsTable:
    __db: AsyncDatabaseConnector
    __users: UsersTable

    def __init__(
        self, db_connector: AsyncDatabaseConnector, users_table: UsersTable
    ) -> None:
        self.__db = db_connector
        self.__users = users_table

    async def insert_new_prompt(
        self, user_id: str, form_data: PromptForm
    ) -> PromptModel | None:
        prompt = PromptModel(
            **{
                "user_id": user_id,
                **form_data.model_dump(),
                "timestamp": int(time.time()),
            }
        )

        try:
            async with self.__db.get_async_db() as db:
                result = Prompt(**prompt.model_dump())
                db.add(result)
                await db.commit()
                await db.refresh(result)
                if result:
                    return PromptModel.model_validate(result)
                else:
                    return None
        except Exception:
            return None

    async def get_prompt_by_command(self, command: str) -> PromptModel | None:
        try:
            async with self.__db.get_async_db() as db:
                prompt = await db.scalar(
                    select(Prompt).where(Prompt.command == command)
                )
                return PromptModel.model_validate(prompt)
        except Exception:
            return None

    async def get_prompts(self) -> list[PromptUserResponse]:
        async with self.__db.get_async_db() as db:
            # Single query with JOIN to avoid N+1 problem and nested connections
            query = (
                select(Prompt, User)
                .join(User, Prompt.user_id == User.id, isouter=True)
                .order_by(Prompt.timestamp.desc())
            )
            try:
                # LEFT JOIN in case user is deleted
                results = await db.execute(query)

                prompts: list[PromptUserResponse] = []
                for prompt, user in results.all():
                    user_data = None
                    if user:
                        user_data = UserModel.model_validate(user).model_dump()

                    prompts.append(
                        PromptUserResponse.model_validate(
                            {
                                **PromptModel.model_validate(prompt).model_dump(),
                                "user": user_data,
                            }
                        )
                    )

                return prompts
            except Exception as e:
                log.error(e)
                return []

    async def get_prompts_paginated(
        self, page: int = 1, limit: int = 20, search: str | None = None
    ) -> list[PromptModel]:
        """Get paginated prompts with optional search"""
        async with self.__db.get_async_db() as db:
            query = select(Prompt).order_by(Prompt.timestamp.desc())

            # Apply search filter if provided
            if search and search.strip():
                search_term = f"%{search.strip().lower()}%"
                query = query.where(
                    Prompt.command.ilike(search_term)
                    | Prompt.title.ilike(search_term)
                    | Prompt.content.ilike(search_term)
                )

            # Apply pagination
            offset = (page - 1) * limit
            prompts = await db.scalars(query.offset(offset).limit(limit))

            return [PromptModel.model_validate(prompt) for prompt in prompts.all()]

    async def get_prompts_with_users_paginated(
        self, page: int = 1, limit: int = 20, search: str | None = None
    ) -> list[PromptUserResponse]:
        """Get paginated prompts with user info and optional search"""
        async with self.__db.get_async_db() as db:
            # Import User model for the join
            from open_webui.models.users import User

            # Start with joined query to avoid N+1 problem
            query = (
                select(Prompt, User)
                .join(User, Prompt.user_id == User.id, isouter=True)
                .order_by(Prompt.timestamp.desc())
            )

            # Apply search filter if provided
            if search and search.strip():
                search_term = f"%{search.strip().lower()}%"
                query = query.where(
                    Prompt.command.ilike(search_term)
                    | Prompt.title.ilike(search_term)
                    | Prompt.content.ilike(search_term)
                )

            # Apply pagination
            offset = (page - 1) * limit
            results = await db.execute(query.offset(offset).limit(limit))

            prompts: list[PromptUserResponse] = []
            for prompt, user in results.all():
                user_data = None
                if user:
                    from open_webui.models.users import UserModel

                    user_data = UserModel.model_validate(user).model_dump()

                prompts.append(
                    PromptUserResponse.model_validate(
                        {
                            **PromptModel.model_validate(prompt).model_dump(),
                            "user": user_data,
                        }
                    )
                )

            return prompts

    async def get_prompts_count(self, search: str | None = None) -> int:
        """Get total count of prompts with optional search filter"""
        async with self.__db.get_async_db() as db:
            query = select(func.count()).select_from(Prompt)

            # Apply search filter if provided
            if search and search.strip():
                search_term = f"%{search.strip().lower()}%"
                query = query.where(
                    Prompt.command.ilike(search_term)
                    | Prompt.title.ilike(search_term)
                    | Prompt.content.ilike(search_term)
                )
            count = await db.scalar(query)
            return count if count else 0

    async def get_prompts_by_user_id_paginated(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 20,
        search: str | None = None,
    ) -> list[PromptModel]:
        """Get paginated prompts by user - users only see their own prompts"""
        async with self.__db.get_async_db() as db:
            query = select(Prompt).order_by(Prompt.timestamp.desc())

            # Users only see their own prompts
            query = query.filter(Prompt.user_id == user_id)

            # Apply search filter if provided
            if search and search.strip():
                search_term = f"%{search.strip().lower()}%"
                query = query.where(
                    Prompt.command.ilike(search_term)
                    | Prompt.title.ilike(search_term)
                    | Prompt.content.ilike(search_term)
                )

            # Apply pagination
            offset = (page - 1) * limit
            prompts = await db.scalars(query.offset(offset).limit(limit))

            return [PromptModel.model_validate(prompt) for prompt in prompts.all()]

    async def get_prompts_by_user_id_with_users_paginated(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 20,
        search: str | None = None,
    ) -> list[PromptUserResponse]:
        """Get paginated prompts by user with user info - users only see their own prompts"""
        # Use JOIN query to avoid N+1 problem
        async with self.__db.get_async_db() as db:
            from open_webui.models.users import User, UserModel

            # Single query with JOIN
            query = (
                select(Prompt, User)
                .join(User, Prompt.user_id == User.id, isouter=True)
                .order_by(Prompt.timestamp.desc())
            )

            # Filter by user ID
            query = query.filter(Prompt.user_id == user_id)

            # Apply search filter if provided
            if search and search.strip():
                search_term = f"%{search.strip().lower()}%"
                query = query.where(
                    Prompt.command.ilike(search_term)
                    | Prompt.title.ilike(search_term)
                    | Prompt.content.ilike(search_term)
                )

            # Apply pagination
            offset = (page - 1) * limit
            results = await db.execute(query.offset(offset).limit(limit))

            result: list[PromptUserResponse] = []
            for prompt, user in results.all():
                user_data = None
                if user:
                    user_data = UserModel.model_validate(user).model_dump()

                result.append(
                    PromptUserResponse.model_validate(
                        {
                            **PromptModel.model_validate(prompt).model_dump(),
                            "user": user_data,
                        }
                    )
                )

        return result

    async def get_prompts_count_by_user_id(
        self, user_id: str, search: str | None = None
    ) -> int:
        """Get count of prompts for user - users only see their own prompts"""
        async with self.__db.get_async_db() as db:
            query = select(func.count()).select_from(Prompt)

            # Users only see their own prompts
            query = query.where(Prompt.user_id == user_id)

            # Apply search filter if provided
            if search and search.strip():
                search_term = f"%{search.strip().lower()}%"
                query = query.where(
                    Prompt.command.ilike(search_term)
                    | Prompt.title.ilike(search_term)
                    | Prompt.content.ilike(search_term)
                )
            count = await db.scalar(query)
            return count if count else 0

    async def get_prompts_by_user_id(self, user_id: str) -> list[PromptUserResponse]:
        """Get prompts for user - users only see their own prompts"""
        async with self.__db.get_async_db() as db:
            # Import User model to do the join
            from open_webui.models.users import User

            # Single query with JOIN to avoid N+1 problem and nested connections
            query = (
                select(Prompt, User)
                .join(User, Prompt.user_id == User.id, isouter=True)
                .where(Prompt.user_id == user_id)
                .order_by(Prompt.timestamp.desc())
            )
            # LEFT JOIN in case user is deleted
            results = await db.execute(query)

            prompts: list[PromptUserResponse] = []
            for prompt, user in results.all():
                user_data = None
                if user:
                    from open_webui.models.users import UserModel

                    user_data = UserModel.model_validate(user).model_dump()

                prompts.append(
                    PromptUserResponse.model_validate(
                        {
                            **PromptModel.model_validate(prompt).model_dump(),
                            "user": user_data,
                        }
                    )
                )

            return prompts

    async def update_prompt_by_command(
        self, command: str, form_data: PromptForm
    ) -> PromptModel | None:
        try:
            async with self.__db.get_async_db() as db:
                if prompt := await db.scalar(
                    select(Prompt).where(Prompt.command == command)
                ):
                    prompt.title = form_data.title
                    prompt.content = form_data.content
                    prompt.access_control = form_data.access_control
                    prompt.timestamp = int(time.time())
                    await db.commit()
                    return PromptModel.model_validate(prompt)
                return None
        except Exception:
            return None

    async def delete_prompt_by_command(self, command: str) -> bool:
        try:
            async with self.__db.get_async_db() as db:
                _ = await db.execute(delete(Prompt).where(Prompt.command == command))
                await db.commit()

                return True
        except Exception:
            return False

    async def get_prompts_with_access_control(
        self, user_id: str, page: int = 1, limit: int = 20, search: str | None = None
    ) -> list[PromptModel]:
        """Get paginated prompts that the user has access to (public + owned + shared)

        Performance optimization: This method filters at the database level first,
        which is much more efficient than loading all prompts and filtering in Python.
        It uses SQL OR conditions to filter for public prompts and user's own prompts,
        then only checks access control for the remaining subset.
        """
        async with self.__db.get_async_db() as db:
            from open_webui.utils.access_control import has_access

            # Database-agnostic condition using SQLAlchemy cast for PostgreSQL compatibility
            public_prompt_condition = or_(
                Prompt.access_control.is_(None),
                cast(Prompt.access_control, Text) == "null",
            )

            # Build base query that efficiently filters at database level
            query = (
                select(Prompt)
                .where(
                    or_(
                        # Public prompts (database-agnostic condition)
                        public_prompt_condition,
                        # User's own prompts
                        Prompt.user_id == user_id,
                        # Note: We still need to check shared prompts manually since
                        # access_control JSON structure requires application-level logic
                    )
                )
                .order_by(Prompt.timestamp.desc())
            )

            # Apply search filter if provided
            if search and search.strip():
                search_term = f"%{search.strip().lower()}%"
                query = query.where(
                    Prompt.command.ilike(search_term)
                    | Prompt.title.ilike(search_term)
                    | Prompt.content.ilike(search_term)
                )

            # Apply pagination and ordering at database level
            offset = (page - 1) * limit
            prompts = await db.scalars(query.offset(offset).limit(limit))

            # For the small result set, check shared prompts with has_access
            accessible_prompts: list[PromptModel] = []
            for prompt in prompts.all():
                # Public prompts (access_control is None) are accessible to everyone
                if prompt.access_control is None:
                    accessible_prompts.append(prompt)
                # User's own prompts are always accessible
                elif prompt.user_id == user_id:
                    accessible_prompts.append(prompt)
                # Check if user has explicit read access to shared prompts
                elif await has_access(user_id, "read", prompt.access_control):
                    accessible_prompts.append(prompt)

            return [PromptModel.model_validate(prompt) for prompt in accessible_prompts]

    async def get_prompts_with_access_control_and_users(
        self, user_id: str, page: int = 1, limit: int = 20, search: str | None = None
    ) -> list[PromptUserResponse]:
        """Get paginated prompts with user info that the user has access to"""
        # Get accessible prompts first
        prompts = await self.get_prompts_with_access_control(
            user_id, page, limit, search
        )

        # Add user info
        prompts_with_users: list[PromptUserResponse] = []
        for prompt in prompts:
            user = await self.__users.get_user_by_id(prompt.user_id)
            prompts_with_users.append(
                PromptUserResponse.model_validate(
                    {
                        **prompt.model_dump(),
                        "user": user.model_dump() if user else None,
                    }
                )
            )

        return prompts_with_users

    async def get_prompts_count_with_access_control(
        self, user_id: str, search: str | None = None
    ) -> int:
        """Get count of prompts the user has access to"""
        async with self.__db.get_async_db() as db:
            from open_webui.utils.access_control import has_access

            # Database-agnostic condition using SQLAlchemy cast for PostgreSQL compatibility
            public_prompt_condition = or_(
                Prompt.access_control.is_(None),
                cast(Prompt.access_control, Text) == "null",
            )

            # Build efficient query that filters at database level
            query = select(Prompt).where(
                or_(
                    # Public prompts (database-agnostic condition)
                    public_prompt_condition,
                    # User's own prompts
                    Prompt.user_id == user_id,
                    # Note: We still need to check shared prompts manually since
                    # access_control JSON structure requires application-level logic
                )
            )

            # Apply search filter if provided
            if search and search.strip():
                search_term = f"%{search.strip().lower()}%"
                query = query.where(
                    Prompt.command.ilike(search_term)
                    | Prompt.title.ilike(search_term)
                    | Prompt.content.ilike(search_term)
                )

            # Get the filtered prompts (much smaller set now)
            prompts = await db.scalars(query)

            # For the small result set, check shared prompts with has_access
            accessible_count = 0
            for prompt in prompts.all():
                # Public prompts (access_control is None) are accessible to everyone
                if prompt.access_control is None:
                    accessible_count += 1
                # User's own prompts are always accessible
                elif prompt.user_id == user_id:
                    accessible_count += 1
                # Check if user has explicit read access to shared prompts
                elif await has_access(user_id, "read", prompt.access_control):
                    accessible_count += 1

            return accessible_count
