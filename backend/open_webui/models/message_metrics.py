import time
from typing import Any
import uuid
from logging import getLogger

from open_webui.internal.db_utils import AsyncDatabaseConnector
from open_webui.models.base import Base
from open_webui.models.users import UserModel
from pydantic import BaseModel
from sqlalchemy import BigInteger, Text, func, select
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import Select


logger = getLogger(__name__)


class MessageMetric(Base):
    __tablename__ = "message_metrics"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str] = mapped_column(Text)
    user_domain: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(Text)
    completion_tokens: Mapped[int] = mapped_column(BigInteger)
    prompt_tokens: Mapped[int] = mapped_column(BigInteger)
    total_tokens: Mapped[int] = mapped_column(BigInteger)
    chat_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    mcp_tool: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # MCP toggle/process name, None for non-MCP calls
    created_at: Mapped[int] = mapped_column(BigInteger)


class MessageMetricsModel(BaseModel):
    id: str
    user_id: str
    user_domain: str
    model: str
    completion_tokens: float
    prompt_tokens: float
    total_tokens: float
    chat_id: str | None = None
    mcp_tool: str | None = None  # MCP toggle/process name, None for non-MCP calls
    created_at: int


class UsageModel(BaseModel):
    completion_tokens: float
    prompt_tokens: float
    total_tokens: float


class MessageMetricsTable:

    __db: AsyncDatabaseConnector

    def __init__(self, db_connector: AsyncDatabaseConnector) -> None:
        self.__db = db_connector

    async def insert_new_metrics(
        self,
        user: UserModel,
        model: str,
        usage: dict,
        chat_id: str | None = None,
        mcp_tool: str | None = None,
    ):
        async with self.__db.get_async_db() as db:
            id = str(uuid.uuid4())
            ts = int(time.time())
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
                    "chat_id": chat_id,
                    "mcp_tool": mcp_tool,
                    "created_at": ts,
                }
            )

            result = MessageMetric(**metrics.model_dump())
            db.add(result)
            await db.commit()
            await db.refresh(result)

    async def get_used_models(self) -> list[str]:
        try:
            async with self.__db.get_async_db() as db:
                models = await db.scalars(select(MessageMetric.model).distinct())
                return [model for model in models.all()]
        except Exception as e:
            logger.error(f"Failed to get used models: {e}")
            return []

    async def get_domains(self) -> list[str]:
        try:
            async with self.__db.get_async_db() as db:
                domains = await db.scalars(select(MessageMetric.user_domain).distinct())
                return [domain for domain in domains.all()]
        except Exception as e:
            logger.error(f"Failed to get domains: {e}")
            return []

    async def get_mcp_processes(self) -> list[str]:
        """Return the distinct MCP toggle/process names that have been logged."""
        try:
            async with self.__db.get_async_db() as db:
                processes = await db.execute(
                    select(MessageMetric.mcp_tool.distinct()).where(
                        MessageMetric.mcp_tool.isnot(None)
                    )
                )
                return [p[0] for p in processes if p[0] is not None]
        except Exception as e:
            logger.error(f"Failed to get MCP processes: {e}")
            return []

    async def get_messages_number(
        self, domain: str | None = None, model: str | None = None
    ) -> int | None:
        try:
            async with self.__db.get_async_db() as db:
                query = select(func.count()).select_from(MessageMetric)
                if domain:
                    query = query.where(MessageMetric.user_domain == domain)
                if model:
                    query = query.where(MessageMetric.model == model)
                return await db.scalar(query)
        except Exception as e:
            logger.error(f"Failed to get messages number: {e}")
            return 0

    async def get_daily_messages_number(
        self, domain: str | None = None, model: str | None = None
    ) -> int | None:
        try:
            async with self.__db.get_async_db() as db:
                # Use the same time calculation as historical data for consistency
                current_time = int(time.time())
                end_time = current_time
                # Calculate start of the current day in UTC
                start_time = current_time - (current_time % 86400)
                # Build the query to count messages for the current day
                query = (
                    select(func.count())
                    .select_from(MessageMetric)
                    .where(
                        MessageMetric.created_at >= start_time,
                        MessageMetric.created_at < end_time,
                    )
                )

                if domain:
                    query = query.where(MessageMetric.user_domain == domain)
                if model:
                    query = query.where(MessageMetric.model == model)

                return await db.scalar(query)
        except Exception as e:
            logger.error(f"Failed to get daily messages number: {e}")
            return 0

    def _apply_mcp_filter[T](self, query: Select[T], mcp_tool: str | None) -> Select[T]:
        """Apply mcp_tool filter to a SQLAlchemy query.

        Sentinel values:
          '__mcp_all__'  → mcp_tool IS NOT NULL  (all MCP rows)
          '__non_mcp__'  → mcp_tool IS NULL      (non-MCP rows only)
          anything else  → mcp_tool = <value>    (specific tool)
          None / falsy   → no filter
        """
        if mcp_tool == "__mcp_all__":
            return query.where(MessageMetric.mcp_tool.isnot(None))
        elif mcp_tool == "__non_mcp__":
            return query.where(MessageMetric.mcp_tool.is_(None))
        elif mcp_tool:
            return query.where(MessageMetric.mcp_tool == mcp_tool)
        return query

    async def get_message_tokens_sum(
        self,
        domain: str | None = None,
        start_timestamp: int | None = None,
        end_timestamp: int | None = None,
        mcp_tool: str | None = None,
    ) -> int | None:
        try:
            async with self.__db.get_async_db() as db:
                query = select(func.sum(MessageMetric.total_tokens))
                if domain:
                    query = query.filter(MessageMetric.user_domain == domain)
                if start_timestamp:
                    query = query.filter(MessageMetric.created_at >= start_timestamp)
                if end_timestamp:
                    query = query.filter(MessageMetric.created_at <= end_timestamp)
                query = self._apply_mcp_filter(query, mcp_tool)
                result = await db.scalar(query)
                return round(result, 2) if result else 0
        except Exception as e:
            logger.error(f"Failed to get message tokens number: {e}")
            return 0  # Return 0 instead of None

    async def get_daily_message_tokens_sum(
        self,
        days: int = 1,
        domain: str | None = None,
        mcp_tool: str | None = None,
    ) -> int | None:
        try:
            async with self.__db.get_async_db() as db:
                current_time = int(time.time())
                end_time = current_time
                start_time = current_time - (current_time % 86400)

                query = select(func.sum(MessageMetric.total_tokens)).where(
                    MessageMetric.created_at >= start_time,
                    MessageMetric.created_at < end_time,
                )

                if domain:
                    query = query.filter(MessageMetric.user_domain == domain)
                query = self._apply_mcp_filter(query, mcp_tool)

                result = await db.scalar(query)
                return round(result, 2) if result and result else 0
        except Exception as e:
            logger.error(f"Failed to get daily message tokens number: {e}")
            return 0  # Return 0 instead of None

    async def get_historical_messages_data(
        self, days: int = 7, domain: str | None = None, model: str | None = None
    ) -> list[dict[str, str | int]]:
        """
        Returns a list of dicts with 'date' and 'count' for each day in the range (oldest to newest),
        counting the number of MessageMetric per day for the given number of days (UTC).
        """
        try:
            result: list[dict[str, str | int]] = []
            current_time = int(time.time())
            today_midnight = current_time - (current_time % 86400)

            # Calculate the start and end timestamps (inclusive of today)
            start_timestamp = today_midnight - ((days - 1) * 86400)
            end_timestamp = today_midnight + 86400

            # Build expected date keys in chronological order (oldest to newest)
            expected_dates = {}
            for offset in reversed(range(days)):
                day_start = today_midnight - (offset * 86400)
                date_str = time.strftime("%Y-%m-%d", time.gmtime(day_start))
                expected_dates[date_str] = 0

            async with self.__db.get_async_db() as db:
                query = select(
                    func.strftime(
                        "%Y-%m-%d", func.datetime(MessageMetric.created_at, "unixepoch")
                    ).label("date"),
                    func.count(MessageMetric.id).label("count"),
                ).where(
                    MessageMetric.created_at >= start_timestamp,
                    MessageMetric.created_at < end_timestamp,
                )
                if domain:
                    query = query.where(MessageMetric.user_domain == domain)
                if model:
                    query = query.where(MessageMetric.model == model)
                query = query.group_by("date")
                results = await db.execute(query)
                for date_str, count in results:
                    if date_str in expected_dates:
                        expected_dates[date_str] = count if count else 0

            # Output as a sorted list (oldest to newest)
            return [
                {"date": date, "count": expected_dates[date]}
                for date in sorted(expected_dates.keys())
            ]
        except Exception as e:
            logger.error(f"Failed to get historical messages data: {e}")
            # Fallback: return zeros for each day in the range
            fallback = []
            for offset in reversed(range(days)):
                day_start = today_midnight - (offset * 86400)
                date_str = time.strftime("%Y-%m-%d", time.gmtime(day_start))
                fallback.append({"date": date_str, "count": 0})
            return fallback

    async def get_historical_tokens_data(
        self,
        days: int = 7,
        domain: str | None = None,
        mcp_tool: str | None = None,
    ) -> list[dict[str, str | int]]:
        """
        Returns a list of dicts with 'date' and 'count' for each day in the range (oldest to newest),
        summing the total tokens per day for the given number of days (UTC).
        """
        try:
            current_time = int(time.time())
            today_midnight = current_time - (current_time % 86400)

            start_timestamp = today_midnight - ((days - 1) * 86400)
            end_timestamp = today_midnight + 86400

            expected_dates = {}
            for offset in reversed(range(days)):
                day_start = today_midnight - (offset * 86400)
                date_str = time.strftime("%Y-%m-%d", time.gmtime(day_start))
                expected_dates[date_str] = 0

            async with self.__db.get_async_db() as db:
                query = select(
                    func.strftime(
                        "%Y-%m-%d", func.datetime(MessageMetric.created_at, "unixepoch")
                    ).label("date"),
                    func.sum(MessageMetric.total_tokens).label("count"),
                ).where(
                    MessageMetric.created_at >= start_timestamp,
                    MessageMetric.created_at < end_timestamp,
                )
                if domain:
                    query = query.filter(MessageMetric.user_domain == domain)
                query = self._apply_mcp_filter(query, mcp_tool)
                query = query.group_by("date")
                results = await db.execute(query)
                for date_str, count in results:
                    if date_str in expected_dates:
                        expected_dates[date_str] = round(count, 2) if count else 0

            return [
                {"date": date, "count": expected_dates[date]}
                for date in sorted(expected_dates.keys())
            ]
        except Exception as e:
            logger.error(f"Failed to get historical tokens data: {e}")
            fallback = []
            for offset in reversed(range(days)):
                day_start = today_midnight - (offset * 86400)
                date_str = time.strftime("%Y-%m-%d", time.gmtime(day_start))
                fallback.append({"date": date_str, "count": 0})
            return fallback

    async def get_range_metrics(
        self,
        start_timestamp: int,
        end_timestamp: int,
        domain: str | None = None,
        model: str | None = None,
    ) -> dict[str, int]:
        """Get message metrics for a specific date range"""
        try:
            async with self.__db.get_async_db() as db:
                # Build query with range filters
                query = (
                    select(
                        func.count(),
                        func.sum(MessageMetric.total_tokens),
                    )
                    .select_from(MessageMetric)
                    .filter(
                        MessageMetric.created_at >= start_timestamp,
                        MessageMetric.created_at < end_timestamp,
                    )
                )

                # Apply domain filter if specified
                if domain:
                    query = query.filter(MessageMetric.user_domain == domain)

                # Apply model filter if specified
                if model:
                    query = query.filter(MessageMetric.model == model)

                result = (await db.execute(query)).first()

                total_prompts = result[0] if result else 0
                total_tokens = round(result[1], 2) if result and result[1] else 0

                return {"total_prompts": total_prompts, "total_tokens": total_tokens}
        except Exception as e:
            logger.error(f"Failed to get range metrics: {e}")
            return {"total_prompts": 0, "total_tokens": 0}

    async def get_model_token_usage(
        self, start_timestamp: int, end_timestamp: int, domain: str | None = None
    ) -> list[dict[str, int | str]]:
        """Get token usage by model for a specific date range"""
        try:
            async with self.__db.get_async_db() as db:
                # Base query with filters
                query = (
                    select(
                        MessageMetric.model,
                        func.sum(MessageMetric.total_tokens).label("tokens"),
                    )
                    .where(
                        MessageMetric.created_at >= start_timestamp,
                        MessageMetric.created_at < end_timestamp,
                    )
                    .group_by(MessageMetric.model)
                )

                if domain:
                    query = query.where(MessageMetric.user_domain == domain)

                # Execute query and process results
                results = await db.execute(query)

                # Format the results as a list of dictionaries
                model_usage = [
                    {"model": model, "tokens": round(tokens, 2) if tokens else 0}
                    for model, tokens in results.all()
                ]

                return model_usage
        except Exception as e:
            logger.error(f"Failed to get model token usage: {e}")
            return []

    async def get_historical_daily_data(
        self,
        start_timestamp: int,
        end_timestamp: int,
        domain: str | None = None,
        model: str | None = None,
    ) -> list[dict[str, int]]:
        """Get historical daily prompt data for a specific date range"""
        try:
            result: list[dict[str, int]] = []

            # Get daily data for each day in the range
            current_day = start_timestamp
            while current_day < end_timestamp:
                next_day = current_day + 86400  # add one day in seconds

                async with self.__db.get_async_db() as db:
                    query = (
                        select(func.count())
                        .select_from(MessageMetric)
                        .where(
                            MessageMetric.created_at >= current_day,
                            MessageMetric.created_at < next_day,
                        )
                    )

                    if domain:
                        query = query.where(MessageMetric.user_domain == domain)

                    if model:
                        query = query.where(MessageMetric.model == model)

                    count = await db.scalar(query)

                    day_str = time.strftime("%Y-%m-%d", time.gmtime(current_day))
                    result.append({"date": day_str, "prompts": count if count else 0})

                current_day = next_day

            return result
        except Exception as e:
            logger.error(f"Failed to get historical daily data: {e}")
            return []

    async def get_historical_daily_tokens(
        self,
        start_timestamp: int,
        end_timestamp: int,
        domain: str | None = None,
        model: str | None = None,
        mcp_tool: str | None = None,
    ) -> list[dict[str, str | int]]:
        """Get historical daily token usage data for a specific date range"""
        try:
            result: list[dict[str, str | int]] = []

            # Get daily data for each day in the range
            current_day = start_timestamp
            while current_day < end_timestamp:
                next_day = current_day + 86400  # add one day in seconds

                async with self.__db.get_async_db() as db:
                    query = select(func.sum(MessageMetric.total_tokens)).where(
                        MessageMetric.created_at >= current_day,
                        MessageMetric.created_at < next_day,
                    )

                    if domain:
                        query = query.where(MessageMetric.user_domain == domain)

                    if model:
                        query = query.where(MessageMetric.model == model)

                    query = self._apply_mcp_filter(query, mcp_tool)

                    tokens_sum = await db.scalar(query)
                    tokens_count = (
                        round(tokens_sum, 2) if tokens_sum and tokens_sum else 0
                    )

                    day_str = time.strftime("%Y-%m-%d", time.gmtime(current_day))
                    result.append({"date": day_str, "tokens": tokens_count})

                current_day = next_day

            return result
        except Exception as e:
            logger.error(f"Failed to get historical daily tokens: {e}")
            return []

    # This function is here and not with Users model since the values needed are in the message metrics table.
    # Values are grouped by date and user_id without sql due to limitations with timestamps and being database agnostic.
    async def get_historical_daily_users(
        self, days: int = 7, domain: str | None = None, model: str | None = None
    ) -> list[dict[str, str | int]]:
        try:
            current_time = int(time.time())
            today_midnight = current_time - (current_time % 86400)
            start_time = today_midnight - (days * 86400)
            end_time = today_midnight + 86400

            async with self.__db.get_async_db() as db:
                query = select(MessageMetric.user_id, MessageMetric.created_at).where(
                    MessageMetric.created_at >= start_time,
                    MessageMetric.created_at < end_time,
                )

                if domain:
                    query = query.where(MessageMetric.user_domain == domain)
                if model:
                    query = query.where(MessageMetric.model == model)

                results = await db.execute(query)

                # Group user_ids by date string
                day_to_users: dict[str, set[str]] = {}
                for user_id, created_at in results.all():
                    date_str = time.strftime("%Y-%m-%d", time.gmtime(created_at))
                    if date_str not in day_to_users:
                        day_to_users[date_str] = set()
                    day_to_users[date_str].add(user_id)

                output: list[dict[str, str | int]] = []
                for day in range(days):
                    day_start = today_midnight - (day * 86400)
                    date_str = time.strftime("%Y-%m-%d", time.gmtime(day_start))
                    count = len(day_to_users.get(date_str, set()))
                    output.append({"date": date_str, "count": count})

                # Return in chronological order (oldest to newest)
                return sorted(output, key=lambda x: x["date"])
        except Exception as e:
            logger.error(f"Failed to get historical daily user counts: {e}")
            # Fallback: return zeros for each day
            fallback: list[dict[str, str | int]] = []
            current_time = int(time.time())
            today_midnight = current_time - (current_time % 86400)
            for day in range(days):
                day_start = today_midnight - (day * 86400)
                date_str = time.strftime("%Y-%m-%d", time.gmtime(day_start))
                fallback.append({"date": date_str, "count": 0})
            return sorted(fallback, key=lambda x: x["date"])

    async def get_inter_prompt_latency_histogram(
        self, domain: str | None = None, model: str | None = None
    ) -> dict[str, list[str] | list[int] | int]:
        """
        Calculate inter-prompt latency histogram for user behavior analysis.

        Returns the time between user prompts in a session (chat), presented as
        histogram data with logarithmic bins from 0-2s up to 1024-2048s.

        Only considers second or subsequent prompts in a chat session.
        """
        try:
            async with self.__db.get_async_db() as db:
                # Query all metrics with chat_id, ordered by chat_id and created_at
                query = select(MessageMetric.chat_id, MessageMetric.created_at).where(
                    MessageMetric.chat_id.isnot(None)
                )

                if domain:
                    query = query.where(MessageMetric.user_domain == domain)
                if model:
                    query = query.where(MessageMetric.model == model)

                query = query.order_by(MessageMetric.chat_id, MessageMetric.created_at)
                results = await db.execute(query)

                if not results:
                    return self._get_empty_histogram()

                # Group by chat_id and calculate inter-prompt latencies
                chat_sessions: dict[str, list[int]] = {}
                for chat_id, created_at in results.all():
                    if chat_id:
                        if chat_id not in chat_sessions:
                            chat_sessions[chat_id] = []
                        chat_sessions[chat_id].append(created_at)

                # Calculate latencies between consecutive prompts in each session
                latencies: list[int] = []
                for chat_id, timestamps in chat_sessions.items():
                    if len(timestamps) >= 2:  # Need at least 2 prompts
                        for i in range(1, len(timestamps)):
                            # Convert to milliseconds and calculate difference
                            prev_time = timestamps[i - 1] * 1000  # Convert to ms
                            curr_time = timestamps[i] * 1000  # Convert to ms
                            latency_ms = curr_time - prev_time

                            # Only include latencies up to 2048 seconds (2048000 ms)
                            if 0 <= latency_ms <= 2048000:
                                latencies.append(latency_ms)

                # Create histogram with logarithmic bins
                return self._create_latency_histogram(latencies)

        except Exception as e:
            logger.error(f"Failed to get inter-prompt latency histogram: {e}")
            return self._get_empty_histogram()

    def _get_empty_histogram(self) -> dict[str, list[str] | list[int] | int]:
        """Return empty histogram structure"""
        bins = [
            "0-2s",
            "2-4s",
            "4-8s",
            "8-16s",
            "16-32s",
            "32-64s",
            "64-128s",
            "128-256s",
            "256-512s",
            "512-1024s",
            "1024-2048s",
        ]
        return {"bins": bins, "counts": [0] * len(bins), "total_latencies": 0}

    def _create_latency_histogram(
        self, latencies: list[int]
    ) -> dict[str, list[str] | list[int] | int]:
        """Create histogram from latency values in milliseconds"""
        # Define bin edges in milliseconds (logarithmic scale)
        bin_edges = [
            0,  # 0s
            2000,  # 2s
            4000,  # 4s
            8000,  # 8s
            16000,  # 16s
            32000,  # 32s
            64000,  # 64s
            128000,  # 128s
            256000,  # 256s
            512000,  # 512s
            1024000,  # 1024s
            2048000,  # 2048s
        ]

        bin_labels = [
            "0-2s",
            "2-4s",
            "4-8s",
            "8-16s",
            "16-32s",
            "32-64s",
            "64-128s",
            "128-256s",
            "256-512s",
            "512-1024s",
            "1024-2048s",
        ]

        # Initialize counts
        counts = [0] * len(bin_labels)

        # Count latencies in each bin
        for latency in latencies:
            for i in range(len(bin_edges) - 1):
                if bin_edges[i] <= latency < bin_edges[i + 1]:
                    counts[i] += 1
                    break

        return {"bins": bin_labels, "counts": counts, "total_latencies": len(latencies)}

    async def get_export_data(
        self,
        start_timestamp: int,
        end_timestamp: int,
        domain: str | None = None,
    ) -> list[dict[str, str | int | None]]:
        """
        Get raw metrics data for export in a specific date range.
        Returns all message metrics within the specified timeframe.
        """
        try:
            async with self.__db.get_async_db() as db:
                query = select(MessageMetric).where(
                    MessageMetric.created_at >= start_timestamp,
                    MessageMetric.created_at < end_timestamp,
                )

                if domain:
                    query = query.where(MessageMetric.user_domain == domain)

                # Order by created_at for chronological export
                query = query.order_by(MessageMetric.created_at)

                results = await db.scalars(query)

                # Convert to list of dictionaries for CSV export
                export_data: list[dict[str, str | int | None]] = []
                for result in results.all():
                    export_data.append(
                        {
                            "id": result.id,
                            "user_id": result.user_id,
                            "user_domain": result.user_domain,
                            "model": result.model,
                            "completion_tokens": result.completion_tokens,
                            "prompt_tokens": result.prompt_tokens,
                            "total_tokens": result.total_tokens,
                            "chat_id": result.chat_id,
                            "mcp_tool": result.mcp_tool,
                            "created_at": result.created_at,
                        }
                    )

                return export_data
        except Exception as e:
            logger.error(f"Failed to get export data: {e}")
            return []
