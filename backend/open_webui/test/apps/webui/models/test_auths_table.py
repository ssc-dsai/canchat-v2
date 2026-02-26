import pytest
from open_webui.internal.db_utils import AsyncDatabaseConnector
from open_webui.models.auths_table import AuthsTable
from open_webui.models.users import User
from sqlalchemy import select, update

_user_attributes: dict[str, str] = {
    "email": "test.bob@example.test",
    "name": "Test Bob",
    "profile_image_url": "http://image.profile",
    "role": "user",
    "oauth_sub": "oauth2_sub",
    "domain": "example.test",
}
_password = "testPassword"


class TestAuths:

    @pytest.mark.asyncio
    async def test_insert_new_auth(
        self,
        auths_table: AuthsTable,
        db_connector: AsyncDatabaseConnector,
    ):

        usermodel = await auths_table.insert_new_auth(
            email=_user_attributes["email"],
            name=_user_attributes["name"],
            password=_password,
            profile_image_url=_user_attributes["profile_image_url"],
            role=_user_attributes["role"],
            oauth_sub=_user_attributes["oauth_sub"],
            domain=_user_attributes["domain"],
        )
        assert usermodel

        # Ensure returned model conforms to data input
        for k, v in _user_attributes.items():
            assert getattr(usermodel, k, None) == v

        async with db_connector.get_async_db() as session:
            try:
                from open_webui.models.auths import Auth

                auth = await session.scalar(
                    select(Auth).where(Auth.email == _user_attributes["email"])
                )
                assert auth
                assert auth.id
                assert auth.email == _user_attributes["email"]
                assert auth.password == _password
                assert auth.active == True

                user = await session.scalar(
                    select(User).where(User.email == _user_attributes["email"])
                )
                for k, v in _user_attributes.items():
                    assert getattr(user, k, None) == v

            finally:
                await session.rollback()

    @pytest.mark.asyncio
    async def test_authenticate_user_correct_password(
        self,
        auths_table: AuthsTable,
    ):
        # Required import since hashing happens outside of this service
        # but unhashing happens within.
        from open_webui.utils.auth import get_password_hash

        usermodel = await auths_table.insert_new_auth(
            email=_user_attributes["email"],
            name=_user_attributes["name"],
            password=get_password_hash(_password),
            profile_image_url=_user_attributes["profile_image_url"],
            role=_user_attributes["role"],
            oauth_sub=_user_attributes["oauth_sub"],
            domain=_user_attributes["domain"],
        )
        assert usermodel

        # Ensure returned model conforms to data input
        for k, v in _user_attributes.items():
            assert getattr(usermodel, k, None) == v

        authenticated_usermodel = await auths_table.authenticate_user(
            email=_user_attributes["email"], password=_password
        )

        assert authenticated_usermodel

        for k, v in _user_attributes.items():
            assert getattr(authenticated_usermodel, k, None) == v

    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(
        self,
        auths_table: AuthsTable,
    ):

        # Required import since hashing happens outside of this service
        # but unhashing happens within.
        from open_webui.utils.auth import get_password_hash

        usermodel = await auths_table.insert_new_auth(
            email=_user_attributes["email"],
            name=_user_attributes["name"],
            password=get_password_hash(_password),
            profile_image_url=_user_attributes["profile_image_url"],
            role=_user_attributes["role"],
            oauth_sub=_user_attributes["oauth_sub"],
            domain=_user_attributes["domain"],
        )
        assert usermodel

        # Ensure returned model conforms to data input
        for k, v in _user_attributes.items():
            assert getattr(usermodel, k, None) == v

        authenticated_usermodel = await auths_table.authenticate_user(
            email=_user_attributes["email"], password="wrongTestPassword"
        )

        assert not authenticated_usermodel

    @pytest.mark.asyncio
    async def test_authenticate_user_by_trusted_header_email_present_active(
        self, auths_table: AuthsTable
    ):
        usermodel = await auths_table.insert_new_auth(
            email=_user_attributes["email"],
            name=_user_attributes["name"],
            password=_password,
            profile_image_url=_user_attributes["profile_image_url"],
            role=_user_attributes["role"],
            oauth_sub=_user_attributes["oauth_sub"],
            domain=_user_attributes["domain"],
        )
        assert usermodel

        user = await auths_table.authenticate_user_by_trusted_header(
            _user_attributes["email"]
        )

        assert user
        # Ensure returned model conforms to data input
        for k, v in _user_attributes.items():
            assert getattr(user, k, None) == v

    @pytest.mark.asyncio
    async def test_authenticate_user_by_trusted_header_email_present_inactive(
        self,
        auths_table: AuthsTable,
        db_connector: AsyncDatabaseConnector,
    ):
        usermodel = await auths_table.insert_new_auth(
            email=_user_attributes["email"],
            name=_user_attributes["name"],
            password=_password,
            profile_image_url=_user_attributes["profile_image_url"],
            role=_user_attributes["role"],
            oauth_sub=_user_attributes["oauth_sub"],
            domain=_user_attributes["domain"],
        )
        assert usermodel

        async with db_connector.get_async_db() as db:
            from open_webui.models.auths import Auth

            result = await db.execute(
                update(Auth)
                .where(Auth.email == _user_attributes["email"])
                .values(active=False)
            )

            assert result.rowcount > 0

            await db.commit()

        user = await auths_table.authenticate_user_by_trusted_header(
            _user_attributes["email"]
        )

        # Return should be None since auth is not active.
        assert not user

    @pytest.mark.asyncio
    async def test_authenticate_user_by_trusted_header_email_not_present(
        self,
        auths_table: AuthsTable,
    ):

        user = await auths_table.authenticate_user_by_trusted_header(
            _user_attributes["email"]
        )

        # Return should be None since auth is not active.
        assert not user

    @pytest.mark.asyncio
    async def test_update_user_password_by_id(
        self,
        auths_table: AuthsTable,
        db_connector: AsyncDatabaseConnector,
    ):
        # Required import since hashing happens outside of this service
        # but unhashing happens within.
        from open_webui.utils.auth import get_password_hash

        usermodel = await auths_table.insert_new_auth(
            email=_user_attributes["email"],
            name=_user_attributes["name"],
            password=_password,
            profile_image_url=_user_attributes["profile_image_url"],
            role=_user_attributes["role"],
            oauth_sub=_user_attributes["oauth_sub"],
            domain=_user_attributes["domain"],
        )
        assert usermodel

        new_hashed = get_password_hash("pw1234new")
        is_updated = await auths_table.update_user_password_by_id(
            id=usermodel.id, new_password=new_hashed
        )

        assert is_updated

        async with db_connector.get_async_db() as db:
            from open_webui.models.auths import Auth

            result = await db.execute(
                select(Auth.password).where(Auth.id == usermodel.id)
            )

            pw = result.first()
            assert pw and pw[0] == new_hashed

    @pytest.mark.asyncio
    async def test_update_user_password_by_id_no_user(
        self,
        auths_table: AuthsTable,
    ):
        # Required import since hashing happens outside of this service
        # but unhashing happens within.
        from open_webui.utils.auth import get_password_hash

        new_hashed = get_password_hash("pw1234new")
        is_updated = await auths_table.update_user_password_by_id(
            id="randomID", new_password=new_hashed
        )

        assert not is_updated

    @pytest.mark.asyncio
    async def test_update_user_email_by_id(
        self,
        auths_table: AuthsTable,
        db_connector: AsyncDatabaseConnector,
    ):

        usermodel = await auths_table.insert_new_auth(
            email=_user_attributes["email"],
            name=_user_attributes["name"],
            password=_password,
            profile_image_url=_user_attributes["profile_image_url"],
            role=_user_attributes["role"],
            oauth_sub=_user_attributes["oauth_sub"],
            domain=_user_attributes["domain"],
        )
        assert usermodel

        new_email = "test.test2@test.example"
        is_updated = await auths_table.update_email_by_id(
            id=usermodel.id, email=new_email
        )

        assert is_updated

        async with db_connector.get_async_db() as db:
            from open_webui.models.auths import Auth

            result = await db.execute(select(Auth.email).where(Auth.id == usermodel.id))

            email = result.first()
            assert email and email[0] == new_email

    @pytest.mark.asyncio
    async def test_delete_auth_by_user_id(
        self,
        auths_table: AuthsTable,
        db_connector: AsyncDatabaseConnector,
    ):

        usermodel = await auths_table.insert_new_auth(
            email=_user_attributes["email"],
            name=_user_attributes["name"],
            password=_password,
            profile_image_url=_user_attributes["profile_image_url"],
            role=_user_attributes["role"],
            oauth_sub=_user_attributes["oauth_sub"],
            domain=_user_attributes["domain"],
        )
        assert usermodel

        is_deleted = await auths_table.delete_auth_by_user_id(user_id=usermodel.id)

        assert is_deleted

        async with db_connector.get_async_db() as db:
            from open_webui.models.auths import Auth
            from open_webui.models.users import User

            auth = await db.scalar(select(Auth).where(Auth.email == usermodel.email))
            assert not auth

            user = await db.scalar(select(User).where(User.id == usermodel.id))
            assert not user
