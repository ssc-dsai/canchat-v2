import pytest
from open_webui.internal.db_utils import AsyncDatabaseConnector
from open_webui.models.domains import Domain, DomainForm, DomainModel, DomainTable
from sqlalchemy import select


class TestDomains:
    @pytest.mark.parametrize(
        "domain",
        [
            "ssc-spc.gc.ca",
        ],
    )
    @pytest.mark.asyncio
    async def test_DomainForm_domain_validator_pass(
        self,
        domain: str,
    ):
        try:
            _ = DomainForm(domain=domain)
        except ValueError:
            pytest.fail("ValueError raised when it should not have")
        except Exception:
            pytest.fail("Unknown exception raised")

    @pytest.mark.parametrize(
        "domain",
        [
            "ssc-spc.ssc-spc.ssc-spc.ssc-spc.ssc-spc.ssc-spc.ssc-spc.ssc-spc.ssc-spc.ssc-spc.ssc-spc.ssc-spc.ssc-spc.ssc-spc.ssc-spc.ssc-spc.ssc-spc.ssc-spc.ssc-spc.ssc-spc.ssc-spc.ssc-spc.ssc-spc.ssc-spc.ssc-spc.ssc-spc.ssc-spc.ssc-spc.ssc-spc.ssc-spc.ssc-spc.ssc-spc.ssc-spc.ssc-spc.gc.ca",  # Too long
            "domain domain",  # contains space
            "ssc-spc.gc..ca",  # double period
            "sspc$#.ca",  # special characters
            None,  # not a string
        ],
    )
    @pytest.mark.asyncio
    async def test_DomainForm_domain_validator_fail(
        self,
        domain: str,
    ):
        try:
            _ = DomainForm(domain=domain)
        except ValueError:
            return
        except Exception:
            pytest.fail("Unknown exception raised")

        pytest.fail("ValueError exception should have been thrown.")

    @pytest.mark.parametrize(
        "domain, description",
        [
            ("ssc-spc2.gc.ca", None),
            ("ssc-spc2.gc.ca", ""),
            ("ssc-spc2.gc.ca", "This is a test domain."),
        ],
    )
    @pytest.mark.asyncio
    async def test_insert_new_domain(
        self,
        description: str | None,
        domain: str,
        domain_table: DomainTable,
        db_connector: AsyncDatabaseConnector,
    ):

        domain_form = DomainForm(
            domain=domain,
            description=description,
        )
        domain_model = await domain_table.insert_new_domain(domain_form)
        assert domain_model

        async with db_connector.get_async_db() as db:
            d = await db.scalar(select(Domain).where(Domain.domain == domain))

            assert d
            assert d.domain == domain
            assert d.description == description
            assert DomainModel.model_validate(d) == domain_model

    # @pytest.mark.asyncio
    # async def test_authenticate_user_correct_password(
    #     self,
    #     auths_table: AuthsTable,
    # ):
    #     # Required import since hashing happens outside of this service
    #     # but unhashing happens within.
    #     from open_webui.utils.auth import get_password_hash

    #     usermodel = await auths_table.insert_new_auth(
    #         email=_domain_attributes["email"],
    #         name=_domain_attributes["name"],
    #         password=get_password_hash(_password),
    #         profile_image_url=_domain_attributes["profile_image_url"],
    #         role=_domain_attributes["role"],
    #         oauth_sub=_domain_attributes["oauth_sub"],
    #         domain=_domain_attributes["domain"],
    #     )
    #     assert usermodel

    #     # Ensure returned model conforms to data input
    #     for k, v in _domain_attributes.items():
    #         assert getattr(usermodel, k, None) == v

    #     authenticated_usermodel = await auths_table.authenticate_user(
    #         email=_domain_attributes["email"], password=_password
    #     )

    #     assert authenticated_usermodel

    #     for k, v in _domain_attributes.items():
    #         assert getattr(authenticated_usermodel, k, None) == v
