import logging
import time
from typing import List, Optional
import uuid
import re

from open_webui.internal.db import get_async_db
from open_webui.models.base import Base
from open_webui.env import SRC_LOG_LEVELS

from pydantic import BaseModel, ConfigDict, validator
from sqlalchemy import BigInteger, select, String, Text
from sqlalchemy.orm import Mapped, mapped_column

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


####################
# Domain DB Schema
####################


class Domain(Base):
    __tablename__ = "domain"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    domain: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[int] = mapped_column(BigInteger)
    updated_at: Mapped[int] = mapped_column(BigInteger)


class DomainModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    domain: str
    description: Optional[str] = None
    created_at: Optional[int] = None
    updated_at: Optional[int] = None


class DomainForm(BaseModel):
    domain: str
    description: Optional[str] = None

    @validator("domain")
    def validate_domain(cls, v):
        """Validate domain format"""
        if not v or not isinstance(v, str):
            raise ValueError("Domain cannot be empty")

        v = v.strip().lower()

        # Basic domain regex pattern
        domain_pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$"

        if not re.match(domain_pattern, v):
            raise ValueError("Invalid domain format")

        if len(v) > 253:  # Max domain length
            raise ValueError("Domain too long")

        if ".." in v:
            raise ValueError("Domain cannot contain consecutive dots")

        return v


####################
# Domain Table
####################


class DomainTable:
    async def insert_new_domain(self, form_data: DomainForm) -> Optional[DomainModel]:
        async with get_async_db() as db:
            domain_id = str(uuid.uuid4())
            timestamp = int(time.time())
            domain = Domain(
                **{
                    "id": domain_id,
                    "domain": form_data.domain,
                    "description": form_data.description,
                    "created_at": timestamp,
                    "updated_at": timestamp,
                }
            )

            try:
                db.add(domain)
                await db.commit()
                await db.refresh(domain)
                return DomainModel.model_validate(domain)
            except Exception as e:
                log.error(f"Error creating domain: {e}")
                await db.rollback()
                return None

    async def get_domains(self) -> list[DomainModel]:
        async with get_async_db() as db:
            domains = await db.scalars(
                select(Domain).order_by(Domain.description, Domain.domain)
            )

            return [DomainModel.model_validate(domain) for domain in domains.all()]

    async def get_domain_by_id(self, domain_id: str) -> Optional[DomainModel]:
        async with get_async_db() as db:
            domain = await db.scalar(select(Domain).where(Domain.id == domain_id))
            return DomainModel.model_validate(domain) if domain else None

    async def get_domain_by_domain(self, domain_name: str) -> Optional[DomainModel]:
        async with get_async_db() as db:
            domain = await db.scalar(select(Domain).where(Domain.domain == domain_name))
            return DomainModel.model_validate(domain) if domain else None

    async def update_domain_by_id(
        self, domain_id: str, form_data: DomainForm
    ) -> Optional[DomainModel]:
        async with get_async_db() as db:
            domain = await db.scalar(select(Domain).where(Domain.id == domain_id))
            if not domain:
                return None

            domain.domain = form_data.domain
            domain.description = form_data.description
            domain.updated_at = int(time.time())

            try:
                await db.commit()
                await db.refresh(domain)
                return DomainModel.model_validate(domain)
            except Exception as e:
                log.error(f"Error updating domain: {e}")
                await db.rollback()
                return None

    async def delete_domain_by_id(self, domain_id: str) -> bool:
        async with get_async_db() as db:
            domain = await db.scalar(select(Domain).where(Domain.id == domain_id))
            if not domain:
                return False

            try:
                await db.delete(domain)
                await db.commit()
                return True
            except Exception as e:
                log.error(f"Error deleting domain: {e}")
                await db.rollback()
                return False

    async def get_available_domains(self) -> List[DomainModel]:
        """Get list of all available domains from the domains table only"""
        # Get domains from domains table only
        return await self.get_domains()

    async def get_available_domains_list(self) -> List[str]:
        """Get list of all available domain names as strings from domains table only"""
        return [domain.domain for domain in await self.get_domains()]


Domains = DomainTable()
