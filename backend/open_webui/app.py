import time
from typing import Optional
import uuid
from pydantic import BaseModel
from sqlalchemy import Column, Text, BigInteger, func
from open_webui.internal.db import Base, get_db
from logging import getLogger

logger = getLogger(__name__)


class MessageMetric(Base):
    __tablename__ = "message_metrics"

    id = Column(Text, primary_key=True)
    user_id = Column(Text)
    user_domain = Column(Text)
    model = Column(Text)
    completion_tokens = Column(BigInteger)
    prompt_tokens = Column(BigInteger)
    total_tokens = Column(BigInteger)
    created_at = Column(BigInteger)


class MessageMetricsModel(BaseModel):
    id: str
    user_id: str
    user_domain: str
    model: str
    completion_tokens: float
    prompt_tokens: float
    total_tokens: float
    created_at: int


class UsageModel(BaseModel):
    completion_tokens: float
    prompt_tokens: float
    total_tokens: float


class MessageMetricsTable:
    def insert_new_metrics(self, user: dict, model: str, usage: dict):
        with get_db() as db:
            id = str(uuid.uuid4())
            ts = int(time.time_ns())
            tokens = UsageModel(**usage)

            metrics = MessageMetricsModel(
                **{
                    "id": id,
                    "user_id": user.id,
                    "user_domain": user.domain,
                    "model": model,
                    "completion_tokens": tokens.completion_tokens,
                    "prompt_tokens": tokens.prompt_tokens,
                    "total_tokens": tokens.total_tokens,
                    "created_at": ts,
                }
            )

            result = MessageMetric(**metrics.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)

    def get_messages_number(self, domain: Optional[str] = None) -> Optional[int]:
        try:
            with get_db() as db:
                query = db.query(MessageMetric)
                if domain:
                    query = query.filter(MessageMetric.user_domain == domain)
                return query.count()
        except Exception as e:
            logger.error(f"Failed to get messages number: {e}")
            return 0  # Return 0 instead of None

    def get_daily_messages_number(
        self, days: int = 1, domain: Optional[str] = None
    ) -> Optional[int]:
        try:
            with get_db() as db:
                # Get the timestamp for the start of the day 'days' days ago
                start_time = int(time.time()) - (days * 24 * 60 * 60)

                # Build the query to count users active after the start time
                query = db.query(MessageMetric).filter(
                    MessageMetric.created_at >= start_time
                )

                if domain:
                    query = query.filter(MessageMetric.user_domain == domain)

                return query.count()
        except Exception as e:
            logger.error(f"Failed to get daily messages number: {e}")
            return 0  # Return 0 instead of None

    def get_message_tokens_sum(self, domain: Optional[str] = None) -> Optional[int]:
        try:
            with get_db() as db:
                query = db.query(MessageMetric)
                if domain:
                    query = query.filter(MessageMetric.user_domain == domain)
                result = query.with_entities(
                    func.sum(MessageMetric.total_tokens),
                ).first()
                return round(result[0], 2) if result and result[0] else 0
        except Exception as e:
            logger.error(f"Failed to get message tokens number: {e}")
            return 0  # Return 0 instead of None

    def get_daily_message_tokens_sum(
        self, days: int = 1, domain: Optional[str] = None
    ) -> Optional[int]:
        try:
            with get_db() as db:
                start_time = int(time.time()) - (days * 24 * 60 * 60)

                query = db.query(MessageMetric).filter(
                    MessageMetric.created_at >= start_time
                )

                if domain:
                    query = query.filter(MessageMetric.user_domain == domain)

                result = query.with_entities(
                    func.sum(MessageMetric.total_tokens),
                ).first()
                return round(result[0], 2) if result and result[0] else 0
        except Exception as e:
            logger.error(f"Failed to get message tokens number: {e}")
            return 0  # Return 0 instead of None

    def get_historical_messages_data(
        self, days: int = 7, domain: Optional[str] = None
    ) -> list[dict]:
        try:
            result = []
            current_time = int(time.time())

            # Debug logging
            logger.info(
                f"Fetching historical messages for domain: {domain}, days: {days}"
            )

            for day in range(days):
                # Calculate start and end time for this day
                end_time = current_time - (day * 24 * 60 * 60)
                start_time = end_time - (24 * 60 * 60)

                # Convert seconds to nanoseconds for comparison with created_at
                # MessageMetric.created_at is stored in nanoseconds (time.time_ns())
                start_time_ns = start_time * 1_000_000_000
                end_time_ns = end_time * 1_000_000_000

                with get_db() as db:
                    query = db.query(MessageMetric).filter(
                        MessageMetric.created_at >= start_time_ns,
                        MessageMetric.created_at < end_time_ns,
                    )

                    if domain:
                        query = query.filter(MessageMetric.user_domain == domain)

                    count = query.count()
                    # Format date as YYYY-MM-DD
                    date_str = time.strftime("%Y-%m-%d", time.localtime(start_time))

                    logger.debug(f"Domain: {domain}, Date: {date_str}, Count: {count}")

                    result.append({"date": date_str, "count": count})

            # Return in chronological order (oldest first)
            return list(reversed(result))
        except Exception as e:
            logger.error(f"Failed to get historical messages data: {e}")
            return [
                {
                    "date": time.strftime(
                        "%Y-%m-%d",
                        time.localtime(int(time.time()) - (i * 24 * 60 * 60)),
                    ),
                    "count": 0,
                }
                for i in range(days)
            ]

    def get_historical_tokens_data(
        self, days: int = 7, domain: Optional[str] = None
    ) -> list[dict]:
        try:
            result = []
            current_time = int(time.time())

            # Debug logging
            logger.info(
                f"Fetching historical tokens for domain: {domain}, days: {days}"
            )

            for day in range(days):
                # Calculate start and end time for this day
                end_time = current_time - (day * 24 * 60 * 60)
                start_time = end_time - (24 * 60 * 60)

                # Convert seconds to nanoseconds for comparison with created_at
                start_time_ns = start_time * 1_000_000_000
                end_time_ns = end_time * 1_000_000_000

                with get_db() as db:
                    query = db.query(MessageMetric).filter(
                        MessageMetric.created_at >= start_time_ns,
                        MessageMetric.created_at < end_time_ns,
                    )

                    if domain:
                        query = query.filter(MessageMetric.user_domain == domain)

                    # Sum tokens for this day
                    tokens_sum = query.with_entities(
                        func.sum(MessageMetric.total_tokens),
                    ).first()

                    # Format date as YYYY-MM-DD
                    date_str = time.strftime("%Y-%m-%d", time.localtime(start_time))

                    count = (
                        round(tokens_sum[0], 2) if tokens_sum and tokens_sum[0] else 0
                    )
                    logger.debug(
                        f"Domain: {domain}, Date: {date_str}, Token Sum: {count}"
                    )

                    result.append({"date": date_str, "count": count})

            # Return in chronological order (oldest first)
            return list(reversed(result))
        except Exception as e:
            logger.error(f"Failed to get historical tokens data: {e}")
            return [
                {
                    "date": time.strftime(
                        "%Y-%m-%d",
                        time.localtime(int(time.time()) - (i * 24 * 60 * 60)),
                    ),
                    "count": 0,
                }
                for i in range(days)
            ]


MessageMetrics = MessageMetricsTable()
