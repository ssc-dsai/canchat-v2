import time
import uuid

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
            "",  # Empty
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

    @pytest.mark.asyncio
    async def test_get_domains(
        self,
        domain_table: DomainTable,
        db_connector: AsyncDatabaseConnector,
    ):
        current_time = int(time.time())
        new_domain = Domain(
            id=str(uuid.uuid4),
            domain="test.example.domain",
            created_at=current_time,
            updated_at=current_time,
        )

        async with db_connector.get_async_db() as db:
            db.add(new_domain)
            await db.commit()
            await db.refresh(new_domain)

            domains = await domain_table.get_domains()

            scalars_domains = await db.scalars(select(Domain))
            domain_models = [
                DomainModel.model_validate(domain) for domain in scalars_domains.all()
            ]

            domains.sort(key=lambda domain: domain.domain)
            domain_models.sort(key=lambda domain: domain.domain)

            assert domains == domain_models

    @pytest.mark.asyncio
    async def test_get_domain_by_id(
        self,
        domain_table: DomainTable,
        db_connector: AsyncDatabaseConnector,
    ):
        current_time = int(time.time())
        new_domain = Domain(
            id=str(uuid.uuid4),
            domain="test.example.domain",
            created_at=current_time,
            updated_at=current_time,
        )

        async with db_connector.get_async_db() as db:
            db.add(new_domain)
            await db.commit()
            await db.refresh(new_domain)

            domain = await domain_table.get_domain_by_id(domain_id=new_domain.id)

            assert domain
            assert DomainModel.model_validate(new_domain) == domain

    @pytest.mark.asyncio
    async def test_get_domain_by_domain(
        self,
        domain_table: DomainTable,
        db_connector: AsyncDatabaseConnector,
    ):
        current_time = int(time.time())
        new_domain = Domain(
            id=str(uuid.uuid4),
            domain="test.example.domain",
            created_at=current_time,
            updated_at=current_time,
        )

        async with db_connector.get_async_db() as db:
            db.add(new_domain)
            await db.commit()
            await db.refresh(new_domain)

            domain = await domain_table.get_domain_by_domain(
                domain_name=new_domain.domain
            )

            assert domain
            assert DomainModel.model_validate(new_domain) == domain

    @pytest.mark.asyncio
    async def test_update_domain_by_id(
        self,
        domain_table: DomainTable,
        db_connector: AsyncDatabaseConnector,
    ):
        current_time = int(time.time())
        new_domain = Domain(
            id=str(uuid.uuid4),
            domain="test.example.domain",
            created_at=current_time,
            updated_at=current_time,
        )

        async with db_connector.get_async_db() as db:
            db.add(new_domain)
            await db.commit()
            await db.refresh(new_domain)

            domain = await domain_table.update_domain_by_id(
                domain_id=new_domain.id,
                form_data=DomainForm(domain="new.domain.example"),
            )
            assert domain

            await db.refresh(new_domain)

            assert DomainModel.model_validate(new_domain) == domain

    @pytest.mark.asyncio
    async def test_delete_domain_by_id(
        self,
        domain_table: DomainTable,
        db_connector: AsyncDatabaseConnector,
    ):
        current_time = int(time.time())
        new_domain = Domain(
            id=str(uuid.uuid4),
            domain="test.example.domain",
            created_at=current_time,
            updated_at=current_time,
        )

        async with db_connector.get_async_db() as db:
            db.add(new_domain)
            await db.commit()
            await db.refresh(new_domain)

            domain = await domain_table.delete_domain_by_id(domain_id=new_domain.id)
            assert domain

            d = await db.scalar(select(Domain).where(Domain.id == new_domain.id))
            assert not d

    @pytest.mark.asyncio
    async def test_delete_domain_by_id_no_domain(
        self,
        domain_table: DomainTable,
    ):
        id = "ThisIsAnIdThatDoesntExist"

        domain = await domain_table.delete_domain_by_id(domain_id=id)
        assert not domain
