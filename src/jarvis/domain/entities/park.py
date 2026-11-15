
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from jarvis.domain.entities.mod import ParkModInstallation


class Park(BaseModel):
    """Représente un parc industriel d'une partie Satisfactory."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    schema_version: int = Field(default=2, ge=1)

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

    # Chaque parc possède ses propres activations et paramètres de modules.
    # Une configuration reste conservée même lorsque le module est désactivé.
    mods: dict[str, ParkModInstallation] = Field(default_factory=dict)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_schema(cls, value):
        """Migre les anciens park.json sans configuration de mods."""

        if not isinstance(value, dict):
            return value

        data = dict(value)
        try:
            version = int(data.get("schema_version", 1))
        except (TypeError, ValueError):
            return data

        if version == 1:
            data.setdefault("mods", {})
            data["schema_version"] = 2

        return data

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("Le nom du parc doit être du texte.")

        value = value.strip()

        if not value:
            raise ValueError("Le nom du parc ne peut pas être vide.")

        return value
