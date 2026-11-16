from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Scenario(BaseModel):
    """Instantané historique d'un calcul de production enregistré dans une usine."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = Field(default=1, ge=1)
    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    park_id: UUID
    factory_id: UUID
    name: str = Field(min_length=1, max_length=120)
    target_class_name: str = Field(min_length=1, max_length=255)
    target_name: str = Field(min_length=1, max_length=160)
    target_rate_per_minute: Decimal = Field(gt=0)
    target_unit_label: str = Field(min_length=1, max_length=20)
    locale: str = Field(default="fr", min_length=2, max_length=20)
    simulation_inputs: dict[str, Any]
    plan_snapshot: dict[str, Any]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("Le nom du scénario doit être du texte.")
        value = value.strip()
        if not value:
            raise ValueError("Le nom du scénario est obligatoire.")
        return value

    @field_validator("target_class_name", "target_name", "target_unit_label", "locale")
    @classmethod
    def validate_non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Cette information de scénario ne peut pas être vide.")
        return value.strip()

    @field_validator("simulation_inputs", "plan_snapshot")
    @classmethod
    def validate_payload(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(value, dict) or not value:
            raise ValueError("L'instantané du scénario est vide ou invalide.")
        return value
