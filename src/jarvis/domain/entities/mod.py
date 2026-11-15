"""Modèles métier pour les extensions optionnelles d'un parc."""

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ParkModInstallation(BaseModel):
    """État d'un module dans un parc, avec sa configuration préservée."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    enabled: bool = False
    configuration: dict[str, Any] = Field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ModDefinition:
    """Décrit un module que J.A.R.V.I.S. sait prendre en charge."""

    mod_id: str
    name: str
    category: str
    summary: str
    description: str
    features: tuple[str, ...]
    integration_note: str
