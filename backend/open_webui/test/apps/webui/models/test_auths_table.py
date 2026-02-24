import pytest
from open_webui.models.auths_table import AuthsTable
from open_webui.models.users import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class TestAuths:

    @pytest.mark.asyncio
    async def test_insert(
        self,
        auths_table: AuthsTable,
        async_session_maker: async_sessionmaker[AsyncSession],
    ):
        __email = "test.bob@example.test"
        __name = "Test Bob"
        __password = "testPassword"
        __profile_image_url = "http://image.profile"
        __role = "user"
        __oauth_sub = "oauth2_sub"
        __domain = "example.test"

        usermodel = await auths_table.insert_new_auth(
            email=__email,
            name=__name,
            password=__password,
            profile_image_url=__profile_image_url,
            role=__role,
            oauth_sub=__oauth_sub,
            domain=__domain,
        )

        assert usermodel

        session = async_session_maker()
        try:
            from backend.open_webui.models.auths import Auth

            auth = await session.scalar(select(Auth).where(Auth.email == __email))
            assert auth
            assert auth.id
            assert auth.email == __email
            assert auth.password == __password
            assert auth.active == True

            user = await session.scalar(select(User).where(User.email == __email))
            assert user
            assert user.id
            assert user.email == __email
            assert user.profile_image_url == __profile_image_url

        except Exception as e:
            print(e)
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_update(self, auths_table: AuthsTable):
        # await auths_table.update_email_by_id("test", "bob")
        pass
