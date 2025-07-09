from enum import Enum, auto
import time
from typing import Optional
import uuid
from pydantic import BaseModel
from sqlalchemy import Column, Text, BigInteger, func, Boolean, Null
from open_webui.internal.db import Base, get_db

# The types of notifications that can be sent.
class NotificationType(Enum):
  WELCOME = auto(),
  ACCOUNT_DELETION = auto(),


class Notification(Base):
  __tableName__ = "notifications"

  id = Column(Text, primary_key=True)
  user_id = Column(Text)
  type = Column(Text)
  is_sent = Column(Boolean)
  is_received = Column(Boolean, nullable=True, default=Null)
  status = Column(Text, nullable=True)
  created_at = Column(BigInteger)
  updated_at = Column(BigInteger)
