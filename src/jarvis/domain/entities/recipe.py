"""Entités de consultation du catalogue des recettes Satisfactory."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

FLUID_FORMS = frozenset({"RF_LIQUID", "RF_GAS"})


@dataclass(frozen=True, slots=True)
class RecipeComponent:
    """Un ingrédient consommé ou un produit fabriqué pendant un cycle.

    ``amount`` est exprimé dans l'unité visible en jeu : nombre d'objets pour
    les solides, mètres cubes pour les liquides et les gaz. ``source_amount``
    conserve la valeur brute de l'export (litres internes pour les fluides).
    """

    class_name: str
    display_name: str
    amount: Decimal
    form: str = "RF_INVALID"
    description: str = ""
    source_amount: Decimal | None = None

    @property
    def is_fluid(self) -> bool:
        return self.form in FLUID_FORMS

    @property
    def unit_label(self) -> str:
        if self.is_fluid:
            return "m³"
        if self.form == "RF_SOLID":
            return "unité"
        return "élément"


@dataclass(frozen=True, slots=True)
class RecipeProducer:
    """Un fabricant ou poste autorisé à exécuter une recette."""

    class_name: str
    display_name: str
    producer_type: str
    description: str = ""


@dataclass(frozen=True, slots=True)
class Recipe:
    """Vue métier normalisée d'une recette du catalogue."""

    class_name: str
    display_name: str
    duration_seconds: Decimal
    ingredients: tuple[RecipeComponent, ...]
    products: tuple[RecipeComponent, ...]
    producers: tuple[RecipeProducer, ...]
    recipe_type: str
    description: str = ""

    @property
    def producer_names(self) -> tuple[str, ...]:
        return tuple(producer.display_name for producer in self.producers)
