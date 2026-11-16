from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Factory(BaseModel):
    """Usine enregistrée dans un parc industriel d'une partie Satisfactory."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    schema_version: int = Field(default=1, ge=1)
    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    park_id: UUID
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    scenario_ids: list[UUID] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("Le nom de l'usine doit être du texte.")
        value = value.strip()
        if not value:
            raise ValueError("Le nom de l'usine est obligatoire.")
        return value

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("La description de l'usine doit être du texte.")
        return value.strip()

    @model_validator(mode="after")
    def validate_scenario_ids(self):
        if len(self.scenario_ids) != len(set(self.scenario_ids)):
            raise ValueError("L'usine contient des scénarios dupliqués.")
        return self
