
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

EntityType = Literal[
    "project",
    "park",
    "factory",
    "machine",
    "extractor",
    "generator",
    "power_grid",
    "transfer",
]


class ArchiveRecord(BaseModel):
    """Métadonnées communes à tous les éléments archivés."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    schema_version: int = Field(default=1, ge=1)

    archive_id: UUID = Field(default_factory=uuid4)

    entity_type: EntityType

    entity_id: UUID

    entity_name: str = Field(
        min_length=1,
        max_length=120,
    )

    parent_project_id: UUID | None = None

    archived_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )

    original_location: str = Field(
        min_length=1,
        max_length=500,
    )
