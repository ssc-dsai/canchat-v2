import logging
import uuid

from open_webui.env import SRC_LOG_LEVELS
from open_webui.internal.db_utils import AsyncDatabaseConnector
from open_webui.models.auths import Auth, AuthModel
from open_webui.models.groups import GroupTable
from open_webui.models.users import UserModel, UsersTable
from sqlalchemy import delete, select, update

"""
The Auths service which provides the ability to interact with the DB.

Note: This service does not follow the pattern of being within the file
      of the Auth model due to causing circular dependency issues.
      This issue is due to the fact that the Auth model is instantiated via
      the model itself through SQLAlchemy whereas other tables use migration
      scripts.
"""

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


class AuthsTable:

    __db: AsyncDatabaseConnector
    __groups: GroupTable
    __users: UsersTable

    def __init__(
        self,
        db_connector: AsyncDatabaseConnector,
        groups: GroupTable,
        users_table: UsersTable,
    ) -> None:
        self.__db = db_connector
        self.__groups = groups
        self.__users = users_table

    async def insert_new_auth(
        self,
        email: str,
        password: str,
        name: str,
        profile_image_url: str = "/user.png",
        role: str = "pending",
        oauth_sub: str | None = None,
        domain: str = "*",
    ) -> UserModel | None:
        async with self.__db.get_async_db() as db:

            log.info("insert_new_auth")

            id = str(uuid.uuid4())

            auth = AuthModel(
                **{
                    "id": id,
                    "email": email,
                    "password": password,
                    "active": True,
                }
            )
            result = Auth(**auth.model_dump())
            db.add(result)

            user = await self.__users.insert_new_user(
                id,
                name,
                email,
                profile_image_url,
                role,
                oauth_sub,
                domain,
            )

            await db.commit()
            await db.refresh(result)

            if result and user:
                return user
            else:
                return None

    async def authenticate_user(self, email: str, password: str) -> UserModel | None:
        log.info(f"authenticate_user: {email}")
        try:
            async with self.__db.get_async_db() as db:

                result = await db.execute(
                    select(Auth).where(Auth.email == email, Auth.active)
                )

                auth = result.scalars().first()
                if auth:
                    from open_webui.utils.auth import verify_password

                    if verify_password(password, auth.password):
                        user = await self.__users.get_user_by_id(auth.id)
                        return user
                    else:
                        return None
                else:
                    return None
        except Exception:
            return None

    async def authenticate_user_by_api_key(self, api_key: str) -> UserModel | None:
        log.info(f"authenticate_user_by_api_key: {api_key}")
        # if no api_key, return None
        if not api_key:
            return None

        try:
            user = await self.__users.get_user_by_api_key(api_key)
            return user if user else None
        except Exception:
            return None

    async def authenticate_user_by_trusted_header(self, email: str) -> UserModel | None:
        log.info(f"authenticate_user_by_trusted_header: {email}")
        try:
            async with self.__db.get_async_db() as db:
                auth = await db.scalar(
                    select(Auth).where(Auth.email == email, Auth.active == True)
                )

                if auth:
                    user = await self.__users.get_user_by_id(auth.id)
                    return user
        except Exception:
            return None

    async def update_user_password_by_id(self, id: str, new_password: str) -> bool:
        try:
            async with self.__db.get_async_db() as db:
                result = await db.execute(
                    update(Auth).where(Auth.id == id).values(password=new_password)
                )
                await db.commit()
                return result.rowcount == 1
        except Exception:
            return False

    async def update_email_by_id(self, id: str, email: str) -> bool:
        try:
            async with self.__db.get_async_db() as db:
                result = await db.execute(
                    update(Auth).where(Auth.id == id).values(email=email)
                )
                await db.commit()
                return result.rowcount == 1
        except Exception:
            return False

    async def delete_auth_by_user_id(self, user_id: str) -> bool:
        try:
            async with self.__db.get_async_db() as db:
                user = await self.__users.get_user_by_id(user_id)

                if user:
                    _ = await db.execute(delete(Auth).where(Auth.email == user.email))
                    await db.commit()
                    _ = await self.__groups.remove_user_from_all_groups(user_id)
                    _ = await self.__users.delete_user_by_id(user_id)
                    return True
                else:
                    return False
        except Exception:
            return False
