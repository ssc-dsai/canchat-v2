import logging
import time
import uuid
from threading import Lock

from open_webui.env import SRC_LOG_LEVELS
from open_webui.internal.db_utils import AsyncDatabaseConnector
from open_webui.models.base import Base
from open_webui.models.users import UsersTable
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import JSON, BigInteger, String, Text, delete, func, or_, select, update
from sqlalchemy.orm import Mapped, mapped_column

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

# Cache for group memberships - invalidated when groups or users change
_group_membership_cache = {}
_cache_timestamp = 0
_cache_lock = Lock()
CACHE_TTL = 300  # 5 minutes


def invalidate_group_membership_cache():
    """Public function to invalidate group membership cache - can be called from other modules."""
    _invalidate_group_membership_cache()


def _get_cache_key(user_id: str, user_domain: str) -> str:
    """Generate cache key for user's group memberships."""
    return f"groups:{user_id}:{user_domain or 'none'}"


def _invalidate_group_membership_cache():
    """Invalidate the entire group membership cache."""
    global _group_membership_cache, _cache_timestamp
    with _cache_lock:
        _group_membership_cache.clear()
        _cache_timestamp = time.time()
        log.debug("Group membership cache invalidated")


def _is_cache_valid() -> bool:
    """Check if cache is still valid based on TTL."""
    return time.time() - _cache_timestamp < CACHE_TTL


####################
# UserGroup DB Schema
####################


class Group(Base):
    __tablename__ = "group"

    id: Mapped[str] = mapped_column(Text, unique=True, primary_key=True)
    user_id: Mapped[str] = mapped_column(Text)

    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)

    data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    permissions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    user_ids: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    allowed_domains: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[int] = mapped_column(BigInteger)
    updated_at: Mapped[int] = mapped_column(BigInteger)


class GroupModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: str

    name: str
    description: str

    data: dict | None = None
    meta: dict | None = None

    permissions: dict | None = None
    user_ids: list[str] = []
    allowed_domains: list[str] | None = []

    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch

    @field_validator("allowed_domains", mode="before")
    @classmethod
    def validate_allowed_domains(cls, v):
        if v is None:
            return []
        return v


####################
# Forms
####################


class GroupResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: str
    permissions: dict | None = None
    data: dict | None = None
    meta: dict | None = None
    user_ids: list[str] = []
    allowed_domains: list[str | None] = []
    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch

    @field_validator("allowed_domains", mode="before")
    @classmethod
    def validate_allowed_domains(cls, v):
        if v is None:
            return []
        return v


class GroupForm(BaseModel):
    name: str
    description: str
    permissions: dict | None = None
    allowed_domains: list[str | None] = []


class GroupUpdateForm(GroupForm):
    user_ids: list[str | None] | None = None
    allowed_domains: list[str | None] | None = None


class GroupTable:

    __db: AsyncDatabaseConnector
    __users: UsersTable

    def __init__(
        self, db_connector: AsyncDatabaseConnector, users_table: UsersTable
    ) -> None:
        self.__db = db_connector
        self.__users = users_table

    async def insert_new_group(
        self, user_id: str, form_data: GroupForm
    ) -> GroupModel | None:
        async with self.__db.get_async_db() as db:
            group = GroupModel(
                **{
                    **form_data.model_dump(exclude_none=True),
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )

            try:
                result = Group(**group.model_dump())
                db.add(result)
                await db.commit()
                await db.refresh(result)
                if result:
                    # Invalidate cache when new group is created
                    _invalidate_group_membership_cache()
                    return GroupModel.model_validate(result)
                else:
                    return None

            except Exception:
                return None

    async def get_groups(self) -> list[GroupModel]:
        async with self.__db.get_async_db() as db:
            groups = await db.scalars(select(Group).order_by(Group.updated_at.desc()))
            return [GroupModel.model_validate(group) for group in groups.all()]

    async def get_groups_by_member_id(self, user_id: str) -> list[GroupModel]:
        """
        Get groups where user is either:
        1. Explicitly added to user_ids list, OR
        2. User's email domain matches any allowed_domains in the group

        Uses caching and SQL filtering for optimal performance.
        """
        # Get user info for domain checking
        user = await self.__users.get_user_by_id(user_id)
        user_domain = user.domain if user else None

        # Generate cache key
        cache_key = _get_cache_key(user_id, user_domain)

        # Try to get from cache first
        with _cache_lock:
            if _is_cache_valid() and cache_key in _group_membership_cache:
                log.debug(f"Cache hit for user {user_id}")
                return _group_membership_cache[cache_key]

        # Cache miss - compute groups using SQL filtering
        log.debug(f"Cache miss for user {user_id}, computing groups")

        async with self.__db.get_async_db() as db:
            query = select(Group).where(
                or_(
                    func.json_array_length(Group.user_ids) > 0,
                    func.json_array_length(Group.allowed_domains) > 0,
                )
            )  # Ensure arrays exist

            # Build filter conditions
            conditions = []

            # Check for user ID in user_ids array
            conditions.append(Group.user_ids.cast(String).like(f'%"{user_id}"%'))

            # Check for domain in allowed_domains array (if user has a domain)
            if user_domain:
                conditions.append(
                    Group.allowed_domains.cast(String).like(f'%"{user_domain}"%')
                )

            # Apply OR conditions and get results
            matching_groups = await db.scalars(
                query.where(or_(*conditions)).order_by(Group.updated_at.desc())
            )
            result = [
                GroupModel.model_validate(group) for group in matching_groups.all()
            ]

            # Cache the result
            with _cache_lock:
                _group_membership_cache[cache_key] = result

            return result

    async def get_group_by_id(self, id: str) -> GroupModel | None:
        try:
            async with self.__db.get_async_db() as db:
                group = await db.scalar(select(Group).where(Group.id == id))
                return GroupModel.model_validate(group) if group else None
        except Exception:
            return None

    async def get_group_user_ids_by_id(self, id: str) -> list[str | None]:
        """
        Get all user IDs for a group, including both:
        1. Explicitly added users in user_ids
        2. All users whose email domain matches allowed_domains
        """

        group = await self.get_group_by_id(id)
        if not group:
            return None

        # Start with explicit user_ids
        user_ids = set(group.user_ids or [])

        # Add domain-based users
        if group.allowed_domains:
            all_users = await self.__users.get_users()
            for user in all_users:
                if user.domain and user.domain in group.allowed_domains:
                    user_ids.add(user.id)

        return list(user_ids)

    async def update_group_by_id(
        self, id: str, form_data: GroupUpdateForm, overwrite: bool = False
    ) -> GroupModel | None:
        try:
            async with self.__db.get_async_db() as db:
                if group := await db.scalar(select(Group).where(Group.id == id)):
                    group.allowed_domains = form_data.allowed_domains
                    group.user_ids = form_data.user_ids
                    await db.commit()
                    await db.refresh(group)
                    # Invalidate cache when group is updated (membership may have changed)
                    _invalidate_group_membership_cache()

                return GroupModel.model_validate(group) if group else None
        except Exception as e:
            log.exception(e)
            return None

    async def delete_group_by_id(self, id: str) -> bool:
        try:
            async with self.__db.get_async_db() as db:
                _ = await db.execute(delete(Group).where(Group.id == id))
                await db.commit()
                # Invalidate cache when group is deleted
                _invalidate_group_membership_cache()
                return True
        except Exception:
            return False

    async def delete_all_groups(self) -> bool:
        async with self.__db.get_async_db() as db:
            try:
                _ = await db.execute(delete(Group))
                await db.commit()
                # Invalidate cache when group is deleted
                _invalidate_group_membership_cache()
                return True
            except Exception:
                return False

    async def remove_user_from_all_groups(self, user_id: str) -> bool:
        async with self.__db.get_async_db() as db:
            try:
                groups = await self.get_groups_by_member_id(user_id)

                for group in groups:
                    group.user_ids.remove(user_id)
                    _ = await db.execute(
                        update(Group)
                        .where(Group.id == group.id)
                        .values(
                            {
                                "user_ids": group.user_ids,
                                "updated_at": int(time.time()),
                            }
                        )
                    )
                    await db.commit()

                # Invalidate cache when user is removed from groups
                _invalidate_group_membership_cache()
                return True
            except Exception:
                return False
