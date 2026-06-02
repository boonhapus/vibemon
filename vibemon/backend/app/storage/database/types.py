"""Dialect-aware SQLAlchemy column types for the Vibemon database."""

from sqlalchemy import JSON, Date, DateTime
from sqlalchemy.dialects.postgresql import JSONB

JSON_STORE = JSON().with_variant(JSONB, "postgresql")
TIMESTAMPTZ = DateTime(timezone=True)
DATE = Date
