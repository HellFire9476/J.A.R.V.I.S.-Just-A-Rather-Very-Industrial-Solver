
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Park(BaseModel):
    """Représente un parc industriel d'une partie Satisfactory."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    schema_version: int = Field(default=1, ge=1)

    id: UUID = Field(default_factory=uuid4)

    project_id: UUID

    name: str = Field(
        min_length=1,
        max_length=80,
    )

    description: str = Field(
        default="",
        max_length=500,
    )

    location: str | None = Field(
        default=None,
        max_length=120,
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("Le nom du parc doit être du texte.")

        value = value.strip()

        if not value:
            raise ValueError("Le nom du parc ne peut pas être vide.")

        return value
