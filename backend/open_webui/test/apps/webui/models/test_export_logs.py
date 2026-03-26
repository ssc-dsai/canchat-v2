import random
import time
import uuid

import pytest
from open_webui.internal.db_utils import AsyncDatabaseConnector
from open_webui.models.export_logs import ExportLog, ExportLogForm, ExportLogsTable


class TestExportLogsTable:

    class TestInsertNewExportLog:
        @pytest.mark.asyncio
        async def test_valid(
            self,
            export_logs_table: ExportLogsTable,
        ):

            export_log_form = ExportLogForm(
                user_id=str(uuid.uuid4()),
                email_domain="email.com",
                date_range_start=int(time.time()),
                date_range_end=int(time.time()),
                row_count=10000,
                file_size=100,
            )
            export_log = await export_logs_table.insert_new_export_log(export_log_form)

            assert export_log
            assert export_log_form.user_id == export_log.user_id
            assert export_log_form.email_domain == export_log.email_domain
            assert export_log_form.date_range_start == export_log.date_range_start
            assert export_log_form.date_range_end == export_log.date_range_end
            assert export_log_form.row_count == export_log.row_count
            assert export_log_form.file_size == export_log.file_size

    class TestGetExportLogsByUser:
        @pytest.mark.asyncio
        async def test_valid(
            self,
            export_logs_table: ExportLogsTable,
        ):
            user_ids = [str(uuid.uuid4()) for _ in range(3)]

            export_logs = [
                ExportLog(
                    id=str(uuid.uuid4()),
                    user_id=random.choice(user_ids),
                    email_domain=f"{i}-email.com",
                    export_timestamp=int(time.time()),
                    file_size=random.randint(10, 2000),
                )
                for i in range(40)
            ]
