"""Solveur déterministe d'équilibrage des chaînes Modular Power.

Le solveur explore des quantités entières d'équipements à partir des profils du
catalogue. Il ne sauvegarde jamais de configuration : il retourne une
proposition que l'application doit faire confirmer à l'utilisateur.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from uuid import uuid4

from jarvis.domain.entities.refined_power import (
    RefinedPowerCatalog,
    RefinedPowerChainConfiguration,
    RefinedPowerFuelProfile,
)
from jarvis.domain.entities.refined_power_optimization import (
    RefinedPowerOptimizationChange,
    RefinedPowerOptimizationLimits,
    RefinedPowerOptimizationRequest,
    RefinedPowerOptimizationSolution,
)
from jarvis.engines.refined_power_engine import (
    RefinedPowerChainResult,
    RefinedPowerEngine,
)

ZERO = Decimal("0")
ONE = Decimal("1")
MAX_MODEL_COUNT = 10000


class RefinedPowerOptimizationError(ValueError):
    """Une demande d'optimisation est invalide ou trop vaste à résoudre."""


@dataclass(frozen=True, slots=True)
class _Candidate:
    heater_id: str
    fuel_id: str
    boiler_id: str
    boiler_count: int
    turbine_id: str
    turbine_count: int
    generator_id: str
    generator_count: int
    co2_chimney_count: int
    steam_cooling_tower_count: int
    power_mw: Decimal
    water_rate: Decimal
    fuel_rate: Decimal
    co2_rate: Decimal
    equipment_count: int


class RefinedPowerOptimizer:
    """Équilibre une chaîne ou recherche une configuration sous contraintes."""

    MAX_CANDIDATE_EVALUATIONS = 1_000_000

    def __init__(self, engine: RefinedPowerEngine | None = None) -> None:
        self.engine = engine or RefinedPowerEngine()

    def optimize(
        self,
        request: RefinedPowerOptimizationRequest,
        catalog: RefinedPowerCatalog,
    ) -> RefinedPowerOptimizationSolution:
        """Retourne une proposition sans modifier la configuration persistée."""

        self._validate_request_references(request, catalog)
        if request.mode == "balance_existing":
            return self._balance_existing(request, catalog)
        return self._search(request, catalog)

    def _balance_existing(
        self,
        request: RefinedPowerOptimizationRequest,
        catalog: RefinedPowerCatalog,
    ) -> RefinedPowerOptimizationSolution:
        reference = request.reference_configuration
        if reference is None:  # Garde-fou de typage, déjà contrôlé par le modèle.
            raise RefinedPowerOptimizationError(
                "Une configuration est nécessaire pour équilibrer une installation."
            )

        try:
            reference_result = self.engine.calculate(reference, catalog)
            fuel = catalog.get_fuel(reference.fuel_id)
            boiler = catalog.get_boiler(reference.boiler_id)
            boiler_point = boiler.operating_point(fuel.operating_temperature_c)
            turbine = catalog.get_turbine(reference.turbine_id)
        except ValueError as error:
            raise RefinedPowerOptimizationError(
                f"L'installation de référence ne peut pas être calculée : {error}"
            ) from error

        steam_generated = (
            boiler_point.high_pressure_steam_m3_per_minute
            * Decimal(reference.boiler_count)
        )
        turbine_count = self._ceil_count(
            steam_generated,
            turbine.high_pressure_steam_input_m3_per_minute,
        )
        turbine_demand = (
            turbine.high_pressure_steam_input_m3_per_minute
            * Decimal(turbine_count)
        )
        utilization = steam_generated / turbine_demand if turbine_demand else ZERO
        low_pressure_steam = (
            turbine.low_pressure_steam_output_m3_per_minute
            * Decimal(turbine_count)
            * utilization
        )
        co2_output = fuel.co2_output_m3_per_minute * Decimal(reference.boiler_count)
        cooling_tower_count = self._ceil_count(
            low_pressure_steam,
            catalog.ventilation.steam_cooling_tower_capacity_m3_per_minute,
        )
        chimney_count = self._ceil_count(
            co2_output,
            catalog.ventilation.co2_chimney_capacity_m3_per_minute,
        )

        if max(turbine_count, cooling_tower_count, chimney_count) > MAX_MODEL_COUNT:
            raise RefinedPowerOptimizationError(
                "L'équilibrage demanderait plus de 10 000 équipements d'un même type."
            )

        proposed = reference.model_copy(
            update={
                "turbine_count": turbine_count,
                "generator_count": turbine_count,
                "steam_cooling_tower_count": cooling_tower_count,
                "co2_chimney_count": chimney_count,
            },
            deep=True,
        )
        proposed_result = self.engine.calculate(proposed, catalog)
        violations = self._configuration_violations(proposed, proposed_result, fuel, request.limits)
        changes = self._build_changes(reference, proposed)
        warnings = list(proposed_result.warnings)
        if not changes:
            warnings.append("L'installation est déjà équilibrée selon les limites du catalogue.")
        if proposed_result.power_is_estimated:
            warnings.append(
                "Le régime calculé est partiel ; la puissance électrique reste une estimation."
            )

        return RefinedPowerOptimizationSolution(
            mode=request.mode,
            feasible=not violations,
            target_reached=None,
            target_power_mw=None,
            configuration=proposed,
            calculation=proposed_result,
            reference_calculation=reference_result,
            changes=changes,
            limiting_constraints=tuple(violations),
            warnings=tuple(dict.fromkeys(warnings)),
            candidates_evaluated=1,
            objective_summary=(
                "Conserver les types et le nombre de chaudières, puis ajuster turbines, "
                "générateurs et évacuations pour supprimer les surplus et débordements."
            ),
        )

    def _search(
        self,
        request: RefinedPowerOptimizationRequest,
        catalog: RefinedPowerCatalog,
    ) -> RefinedPowerOptimizationSolution:
        limits = request.limits
        if limits.max_boilers is None:
            raise RefinedPowerOptimizationError(
                "Le mode de recherche exige une limite explicite de chaudières "
                "pour borner l'espace de configurations."
            )

        fuels = self._select_profiles(catalog.fuels, "fuel_id", request.allowed_fuel_ids)
        boilers = self._select_profiles(catalog.boilers, "boiler_id", request.allowed_boiler_ids)
        turbines = self._select_profiles(
            catalog.turbines, "turbine_id", request.allowed_turbine_ids
        )
        generators = self._select_profiles(
            catalog.generators, "generator_id", request.allowed_generator_ids
        )
        allowed_heaters = set(request.allowed_heater_ids)

        candidates: list[_Candidate] = []
        rejection_reasons: set[str] = set()
        evaluated = 0
        possible_pairs = [
            (turbine, generator, performance)
            for turbine in turbines
            for generator in generators
            for performance in catalog.generator_performance
            if performance.turbine_id == turbine.turbine_id
            and performance.generator_id == generator.generator_id
        ]
        projected_evaluations = 0
        if not possible_pairs:
            rejection_reasons.add(
                "Aucune association turbine/générateur autorisée n'est documentée."
            )
        if allowed_heaters and not any(
            fuel.heater_id in allowed_heaters for fuel in fuels
        ):
            rejection_reasons.add(
                "Aucun combustible autorisé ne correspond aux chauffages sélectionnés."
            )

        for fuel in fuels:
            if allowed_heaters and fuel.heater_id not in allowed_heaters:
                continue
            for boiler in boilers:
                try:
                    boiler_point = boiler.operating_point(fuel.operating_temperature_c)
                except ValueError:
                    rejection_reasons.add(
                        f"{boiler.display_name} ne possède pas de point de fonctionnement "
                        f"à {fuel.operating_temperature_c} °C pour {fuel.display_name}."
                    )
                    continue

                maximum_boilers = self._maximum_boiler_count(
                    fuel,
                    boiler_point.water_consumption_m3_per_minute,
                    request,
                    catalog,
                )
                if maximum_boilers <= 0:
                    rejection_reasons.update(
                        self._zero_bound_reasons(
                            fuel,
                            boiler_point.water_consumption_m3_per_minute,
                            boiler_point.high_pressure_steam_m3_per_minute,
                            limits,
                            catalog,
                        )
                    )
                    continue

                for turbine, generator, performance in possible_pairs:
                    turbine_capacity = turbine.high_pressure_steam_input_m3_per_minute
                    maximum_turbine_equipment = min(
                        limits.max_turbines
                        if limits.max_turbines is not None
                        else MAX_MODEL_COUNT,
                        limits.max_generators
                        if limits.max_generators is not None
                        else MAX_MODEL_COUNT,
                    )
                    maximum_steam = turbine_capacity * Decimal(maximum_turbine_equipment)
                    maximum_lp_per_boiler = (
                        boiler_point.high_pressure_steam_m3_per_minute
                        * turbine.low_pressure_steam_output_m3_per_minute
                        / turbine.high_pressure_steam_input_m3_per_minute
                    )
                    maximum_towers = (
                        limits.max_steam_cooling_towers
                        if limits.max_steam_cooling_towers is not None
                        else MAX_MODEL_COUNT
                    )
                    maximum_lp_total = (
                        catalog.ventilation.steam_cooling_tower_capacity_m3_per_minute
                        * Decimal(maximum_towers)
                    )
                    lp_boiler_bound = self._floor_count(
                        maximum_lp_total,
                        maximum_lp_per_boiler,
                    )
                    pair_maximum_boilers = min(
                        maximum_boilers,
                        lp_boiler_bound,
                        int(
                            (maximum_steam / boiler_point.high_pressure_steam_m3_per_minute)
                            .to_integral_value(rounding=ROUND_FLOOR)
                        ),
                    )
                    if pair_maximum_boilers <= 0:
                        if limits.max_turbines == 0 or limits.max_generators == 0:
                            rejection_reasons.add(
                                "Aucune turbine ou aucun générateur n'est disponible."
                            )
                        elif lp_boiler_bound <= 0:
                            rejection_reasons.add(
                                "La capacité maximale des tours de refroidissement est "
                                "insuffisante pour la vapeur basse pression."
                            )
                        else:
                            rejection_reasons.add(
                                "Les limites de turbines ou de générateurs sont "
                                f"insuffisantes pour {turbine.display_name} / "
                                f"{generator.display_name}."
                            )
                        continue

                    projected_evaluations += pair_maximum_boilers
                    if projected_evaluations > self.MAX_CANDIDATE_EVALUATIONS:
                        raise RefinedPowerOptimizationError(
                            "La recherche dépasse le budget de calcul autorisé. Réduis "
                            "les limites d'équipements ou restreins les profils autorisés. "
                            f"Plus de {self.MAX_CANDIDATE_EVALUATIONS:,} candidats."
                        )

                    for boiler_count in range(1, pair_maximum_boilers + 1):
                        evaluated += 1
                        candidate, reason = self._make_candidate(
                            fuel=fuel,
                            boiler=boiler,
                            boiler_count=boiler_count,
                            boiler_water_rate=boiler_point.water_consumption_m3_per_minute,
                            boiler_steam_rate=(
                                boiler_point.high_pressure_steam_m3_per_minute
                            ),
                            turbine=turbine,
                            generator=generator,
                            full_speed_power=performance.maximum_power_mw_at_full_turbine_speed,
                            request=request,
                            catalog=catalog,
                        )
                        if candidate is None:
                            if reason:
                                rejection_reasons.add(reason)
                            continue
                        candidates.append(candidate)

        if not candidates:
            return RefinedPowerOptimizationSolution(
                mode=request.mode,
                feasible=False,
                target_reached=False if request.mode == "target" else None,
                target_power_mw=request.target_power_mw,
                configuration=None,
                calculation=None,
                reference_calculation=self._reference_calculation(request, catalog),
                changes=(),
                limiting_constraints=tuple(sorted(rejection_reasons)) or (
                    "Aucune configuration ne respecte les contraintes fournies.",
                ),
                warnings=("Aucune solution réalisable n'a été trouvée.",),
                candidates_evaluated=evaluated,
                objective_summary=self._objective_summary(request),
            )

        if request.mode == "maximize":
            selected = min(
                candidates,
                key=lambda candidate: (
                    -candidate.power_mw,
                    candidate.water_rate,
                    candidate.co2_rate,
                    candidate.equipment_count,
                ),
            )
            target_reached = None
        else:
            target = request.target_power_mw
            if target is None:
                raise RefinedPowerOptimizationError("La puissance cible est absente.")
            target_candidates = [item for item in candidates if item.power_mw >= target]
            if target_candidates:
                selected = min(
                    target_candidates,
                    key=lambda candidate: (
                        candidate.power_mw - target,
                        candidate.equipment_count,
                        candidate.water_rate,
                        candidate.co2_rate,
                    ),
                )
                target_reached = True
            else:
                selected = min(
                    candidates,
                    key=lambda candidate: (
                        -candidate.power_mw,
                        candidate.water_rate,
                        candidate.co2_rate,
                        candidate.equipment_count,
                    ),
                )
                target_reached = False
                rejection_reasons.add(
                    "La puissance cible n'est pas atteignable avec les limites fournies."
                )

        configuration = self._candidate_configuration(selected, request)
        calculation = self.engine.calculate(configuration, catalog)
        if calculation.estimated_power_mw != selected.power_mw:
            raise RefinedPowerOptimizationError(
                "Le calcul du solveur ne correspond plus au moteur Modular Power."
            )
        if not calculation.sustainable:
            raise RefinedPowerOptimizationError(
                "Le solveur a retenu une configuration dont les flux ne sont pas équilibrés."
            )
        warnings = list(calculation.warnings)
        if calculation.power_is_estimated:
            warnings.append(
                "La puissance utilise une interpolation linéaire pour un débit de vapeur "
                "partiel ; elle doit être considérée comme une estimation."
            )
        if target_reached is False and request.target_power_mw is not None:
            warnings.append(
                f"Meilleure puissance réalisable : {calculation.estimated_power_mw} MW, "
                f"pour une cible de {request.target_power_mw} MW."
            )
        reference_result = self._reference_calculation(request, catalog)
        changes = self._build_changes(request.reference_configuration, configuration)

        return RefinedPowerOptimizationSolution(
            mode=request.mode,
            feasible=True,
            target_reached=target_reached,
            target_power_mw=request.target_power_mw,
            configuration=configuration,
            calculation=calculation,
            reference_calculation=reference_result,
            changes=changes,
            limiting_constraints=tuple(sorted(rejection_reasons)),
            warnings=tuple(dict.fromkeys(warnings)),
            candidates_evaluated=evaluated,
            objective_summary=self._objective_summary(request),
        )

    def _maximum_boiler_count(
        self,
        fuel: RefinedPowerFuelProfile,
        water_per_boiler: Decimal,
        request: RefinedPowerOptimizationRequest,
        catalog: RefinedPowerCatalog,
    ) -> int:
        limits = request.limits
        upper = limits.max_boilers if limits.max_boilers is not None else 0

        if limits.max_water_m3_per_minute is not None:
            upper = min(
                upper,
                self._floor_count(
                    limits.max_water_m3_per_minute,
                    water_per_boiler,
                ),
            )
        if fuel.fuel_id in limits.fuel_available_per_minute:
            upper = min(
                upper,
                self._floor_count(
                    limits.fuel_available_per_minute[fuel.fuel_id],
                    fuel.consumption_per_minute,
                ),
            )

        maximum_chimneys = (
            limits.max_co2_chimneys
            if limits.max_co2_chimneys is not None
            else MAX_MODEL_COUNT
        )
        co2_total_capacity = (
            catalog.ventilation.co2_chimney_capacity_m3_per_minute
            * Decimal(maximum_chimneys)
        )
        if fuel.co2_output_m3_per_minute > ZERO:
            upper = min(
                upper,
                self._floor_count(co2_total_capacity, fuel.co2_output_m3_per_minute),
            )

        for byproduct in fuel.byproducts:
            capacity = limits.byproduct_capacity_per_minute.get(
                byproduct.resource_id,
                ZERO,
            )
            if byproduct.rate_per_minute > ZERO:
                upper = min(
                    upper,
                    self._floor_count(capacity, byproduct.rate_per_minute),
                )
        return max(0, upper)

    def _make_candidate(
        self,
        *,
        fuel: RefinedPowerFuelProfile,
        boiler,
        boiler_count: int,
        boiler_water_rate: Decimal,
        boiler_steam_rate: Decimal,
        turbine,
        generator,
        full_speed_power: Decimal,
        request: RefinedPowerOptimizationRequest,
        catalog: RefinedPowerCatalog,
    ) -> tuple[_Candidate | None, str | None]:
        limits = request.limits
        boiler_amount = Decimal(boiler_count)
        steam_generated = boiler_steam_rate * boiler_amount
        turbine_count = self._ceil_count(
            steam_generated,
            turbine.high_pressure_steam_input_m3_per_minute,
        )
        if turbine_count <= 0:
            return None, "Une configuration doit comporter au moins une turbine."
        maximum_turbines = (
            limits.max_turbines if limits.max_turbines is not None else MAX_MODEL_COUNT
        )
        maximum_generators = (
            limits.max_generators if limits.max_generators is not None else MAX_MODEL_COUNT
        )
        if turbine_count > maximum_turbines or turbine_count > maximum_generators:
            return None, "Les limites de turbines ou de générateurs sont insuffisantes."

        steam_demand = (
            turbine.high_pressure_steam_input_m3_per_minute * Decimal(turbine_count)
        )
        steam_utilization = min(ONE, steam_generated / steam_demand)
        low_pressure_output = (
            turbine.low_pressure_steam_output_m3_per_minute
            * Decimal(turbine_count)
            * steam_utilization
        )
        steam_tower_count = self._ceil_count(
            low_pressure_output,
            catalog.ventilation.steam_cooling_tower_capacity_m3_per_minute,
        )
        co2_output = fuel.co2_output_m3_per_minute * boiler_amount
        chimney_count = self._ceil_count(
            co2_output,
            catalog.ventilation.co2_chimney_capacity_m3_per_minute,
        )
        if (
            limits.max_steam_cooling_towers is not None
            and steam_tower_count > limits.max_steam_cooling_towers
        ):
            return None, "La capacité maximale de refroidissement de vapeur est insuffisante."
        if limits.max_co2_chimneys is not None and chimney_count > limits.max_co2_chimneys:
            return None, "La capacité maximale d'évacuation du CO₂ est insuffisante."

        water_rate = boiler_water_rate * boiler_amount
        if (
            limits.max_water_m3_per_minute is not None
            and water_rate > limits.max_water_m3_per_minute
        ):
            return None, "Le débit d'eau disponible est insuffisant."

        fuel_rate = fuel.consumption_per_minute * boiler_amount
        available_fuel = limits.fuel_available_per_minute.get(fuel.fuel_id)
        if available_fuel is not None and fuel_rate > available_fuel:
            return None, f"Le combustible {fuel.display_name} disponible est insuffisant."

        for byproduct in fuel.byproducts:
            produced = byproduct.rate_per_minute * boiler_amount
            capacity = limits.byproduct_capacity_per_minute.get(
                byproduct.resource_id,
                ZERO,
            )
            if produced > capacity:
                return (
                    None,
                    f"Capacité de stockage ou d'évacuation insuffisante pour "
                    f"{byproduct.display_name}.",
                )

        power = full_speed_power * steam_utilization * Decimal(turbine_count)
        equipment_count = (
            boiler_count
            + turbine_count
            + turbine_count
            + chimney_count
            + steam_tower_count
        )
        return (
            _Candidate(
                heater_id=fuel.heater_id,
                fuel_id=fuel.fuel_id,
                boiler_id=boiler.boiler_id,
                boiler_count=boiler_count,
                turbine_id=turbine.turbine_id,
                turbine_count=turbine_count,
                generator_id=generator.generator_id,
                generator_count=turbine_count,
                co2_chimney_count=chimney_count,
                steam_cooling_tower_count=steam_tower_count,
                power_mw=power,
                water_rate=water_rate,
                fuel_rate=fuel_rate,
                co2_rate=co2_output,
                equipment_count=equipment_count,
            ),
            None,
        )

    def _configuration_violations(
        self,
        configuration: RefinedPowerChainConfiguration,
        calculation: RefinedPowerChainResult,
        fuel: RefinedPowerFuelProfile,
        limits: RefinedPowerOptimizationLimits,
    ) -> list[str]:
        violations: list[str] = []
        if limits.max_boilers is not None and configuration.boiler_count > limits.max_boilers:
            violations.append(
                f"Nombre de chaudières requis : {configuration.boiler_count}, "
                f"limite : {limits.max_boilers}."
            )
        if limits.max_turbines is not None and configuration.turbine_count > limits.max_turbines:
            violations.append(
                f"Nombre de turbines requis : {configuration.turbine_count}, "
                f"limite : {limits.max_turbines}."
            )
        if (
            limits.max_generators is not None
            and configuration.generator_count > limits.max_generators
        ):
            violations.append(
                f"Nombre de générateurs requis : {configuration.generator_count}, "
                f"limite : {limits.max_generators}."
            )
        if (
            limits.max_co2_chimneys is not None
            and configuration.co2_chimney_count > limits.max_co2_chimneys
        ):
            violations.append(
                f"Nombre de cheminées requis : {configuration.co2_chimney_count}, "
                f"limite : {limits.max_co2_chimneys}."
            )
        if (
            limits.max_steam_cooling_towers is not None
            and configuration.steam_cooling_tower_count
            > limits.max_steam_cooling_towers
        ):
            violations.append(
                "Nombre de tours de refroidissement requis : "
                f"{configuration.steam_cooling_tower_count}, limite : "
                f"{limits.max_steam_cooling_towers}."
            )
        if (
            limits.max_water_m3_per_minute is not None
            and calculation.water_consumption_m3_per_minute
            > limits.max_water_m3_per_minute
        ):
            violations.append(
                "Débit d'eau insuffisant : "
                f"{calculation.water_consumption_m3_per_minute} m³/min requis, "
                f"{limits.max_water_m3_per_minute} m³/min disponible."
            )
        available_fuel = limits.fuel_available_per_minute.get(fuel.fuel_id)
        if (
            available_fuel is not None
            and calculation.fuel_consumption_per_minute > available_fuel
        ):
            violations.append(
                f"Combustible insuffisant : {calculation.fuel_consumption_per_minute} "
                f"{fuel.input_unit} requis, {available_fuel} disponible."
            )
        for byproduct in calculation.byproducts:
            capacity = limits.byproduct_capacity_per_minute.get(byproduct.resource_id, ZERO)
            if byproduct.rate_per_minute > capacity:
                violations.append(
                    f"Capacité insuffisante pour {byproduct.display_name} : "
                    f"{byproduct.rate_per_minute} {byproduct.unit} produits, "
                    f"{capacity} {byproduct.unit} acceptés."
                )
        if calculation.low_pressure_steam_overflow_m3_per_minute > ZERO:
            violations.append(
                "La capacité d'évacuation de vapeur basse pression est insuffisante."
            )
        if calculation.co2_overflow_m3_per_minute > ZERO:
            violations.append("La capacité d'évacuation du CO₂ est insuffisante.")
        if calculation.high_pressure_steam_surplus_m3_per_minute > ZERO:
            violations.append("Un surplus de vapeur haute pression subsiste.")
        return violations

    def _validate_request_references(
        self,
        request: RefinedPowerOptimizationRequest,
        catalog: RefinedPowerCatalog,
    ) -> None:
        self._validate_allowed_ids(
            request.allowed_heater_ids,
            {item.heater_id for item in catalog.heaters},
            "chauffage",
        )
        self._validate_allowed_ids(
            request.allowed_fuel_ids,
            {item.fuel_id for item in catalog.fuels},
            "combustible",
        )
        self._validate_allowed_ids(
            request.allowed_boiler_ids,
            {item.boiler_id for item in catalog.boilers},
            "chaudière",
        )
        self._validate_allowed_ids(
            request.allowed_turbine_ids,
            {item.turbine_id for item in catalog.turbines},
            "turbine",
        )
        self._validate_allowed_ids(
            request.allowed_generator_ids,
            {item.generator_id for item in catalog.generators},
            "générateur",
        )
        fuel_ids = {item.fuel_id for item in catalog.fuels}
        unknown_fuel_limits = set(request.limits.fuel_available_per_minute) - fuel_ids
        if unknown_fuel_limits:
            raise RefinedPowerOptimizationError(
                "Limites de combustible inconnues : "
                + ", ".join(sorted(unknown_fuel_limits))
                + "."
            )
        byproduct_ids = {
            product.resource_id
            for fuel in catalog.fuels
            for product in fuel.byproducts
        }
        unknown_byproducts = (
            set(request.limits.byproduct_capacity_per_minute) - byproduct_ids
        )
        if unknown_byproducts:
            raise RefinedPowerOptimizationError(
                "Capacités de coproduits inconnues : "
                + ", ".join(sorted(unknown_byproducts))
                + "."
            )

    @staticmethod
    def _validate_allowed_ids(
        requested: Iterable[str],
        available: set[str],
        label: str,
    ) -> None:
        unknown = set(requested) - available
        if unknown:
            raise RefinedPowerOptimizationError(
                f"Profil(s) de {label} inconnu(s) : " + ", ".join(sorted(unknown)) + "."
            )

    @staticmethod
    def _select_profiles(items, identifier: str, allowed: tuple[str, ...]):
        if not allowed:
            return tuple(items)
        selected = set(allowed)
        return tuple(item for item in items if getattr(item, identifier) in selected)

    @staticmethod
    def _floor_count(available: Decimal, per_unit: Decimal) -> int:
        if per_unit <= ZERO:
            return MAX_MODEL_COUNT
        return int((available / per_unit).to_integral_value(rounding=ROUND_FLOOR))

    @staticmethod
    def _ceil_count(required: Decimal, capacity: Decimal) -> int:
        if required <= ZERO:
            return 0
        return int((required / capacity).to_integral_value(rounding=ROUND_CEILING))

    @staticmethod
    def _candidate_configuration(
        candidate: _Candidate,
        request: RefinedPowerOptimizationRequest,
    ) -> RefinedPowerChainConfiguration:
        reference = (
            request.reference_configuration
            if request.mode == "balance_existing"
            else None
        )
        return RefinedPowerChainConfiguration(
            chain_id=reference.chain_id if reference else uuid4(),
            name=reference.name if reference else request.chain_name,
            heater_id=candidate.heater_id,
            fuel_id=candidate.fuel_id,
            boiler_id=candidate.boiler_id,
            boiler_count=candidate.boiler_count,
            turbine_id=candidate.turbine_id,
            turbine_count=candidate.turbine_count,
            generator_id=candidate.generator_id,
            generator_count=candidate.generator_count,
            co2_chimney_count=candidate.co2_chimney_count,
            steam_cooling_tower_count=candidate.steam_cooling_tower_count,
        )

    def _reference_calculation(
        self,
        request: RefinedPowerOptimizationRequest,
        catalog: RefinedPowerCatalog,
    ) -> RefinedPowerChainResult | None:
        if request.reference_configuration is None:
            return None
        return self.engine.calculate(request.reference_configuration, catalog)

    @staticmethod
    def _build_changes(
        previous: RefinedPowerChainConfiguration | None,
        proposed: RefinedPowerChainConfiguration,
    ) -> tuple[RefinedPowerOptimizationChange, ...]:
        if previous is None:
            return ()
        fields = (
            ("heater_id", "Chauffage", "Compatibilité thermique"),
            ("fuel_id", "Combustible", "Profil de combustible sélectionné"),
            ("boiler_id", "Chaudière", "Production de vapeur"),
            ("boiler_count", "Chaudières", "Débit de vapeur nécessaire"),
            ("turbine_id", "Turbine", "Capacité d'absorption de vapeur"),
            ("turbine_count", "Turbines", "Absorber la vapeur haute pression"),
            ("generator_id", "Générateur", "Association disponible au catalogue"),
            ("generator_count", "Générateurs", "Un générateur par turbine active"),
            ("co2_chimney_count", "Cheminées CO₂", "Évacuation du CO₂ produit"),
            (
                "steam_cooling_tower_count",
                "Tours de refroidissement",
                "Évacuation de la vapeur basse pression",
            ),
        )
        changes: list[RefinedPowerOptimizationChange] = []
        for field_name, label, reason in fields:
            old_value = getattr(previous, field_name)
            new_value = getattr(proposed, field_name)
            if old_value != new_value:
                changes.append(
                    RefinedPowerOptimizationChange(
                        field_name=field_name,
                        label=label,
                        previous_value=str(old_value),
                        proposed_value=str(new_value),
                        reason=reason,
                    )
                )
        return tuple(changes)

    @staticmethod
    def _objective_summary(request: RefinedPowerOptimizationRequest) -> str:
        if request.mode == "maximize":
            return (
                "Maximiser la puissance électrique nominale estimée dans les limites "
                "de ressources, de ventilation et d'équipements. À puissance égale, "
                "préférer moins d'eau, moins de CO₂ et moins d'équipements."
            )
        return (
            f"Atteindre au moins {request.target_power_mw} MW avec le plus faible "
            "dépassement possible, puis limiter le nombre d'équipements, l'eau et le CO₂."
        )

    @staticmethod
    def _zero_bound_reasons(
        fuel: RefinedPowerFuelProfile,
        water_per_boiler: Decimal,
        steam_per_boiler: Decimal,
        limits: RefinedPowerOptimizationLimits,
        catalog: RefinedPowerCatalog,
    ) -> set[str]:
        reasons: set[str] = set()
        if limits.max_boilers == 0:
            reasons.add("Aucune chaudière n'est autorisée.")
        if (
            limits.max_water_m3_per_minute is not None
            and water_per_boiler > limits.max_water_m3_per_minute
        ):
            reasons.add(
                "Le débit d'eau disponible ne permet pas d'alimenter une chaudière."
            )
        available_fuel = limits.fuel_available_per_minute.get(fuel.fuel_id)
        if available_fuel is not None and fuel.consumption_per_minute > available_fuel:
            reasons.add(
                f"Le combustible {fuel.display_name} disponible ne permet pas "
                "d'alimenter une chaudière."
            )
        if fuel.co2_output_m3_per_minute > ZERO and limits.max_co2_chimneys == 0:
            reasons.add("Aucune cheminée CO₂ n'est disponible pour ce combustible.")
        if fuel.byproducts:
            for product in fuel.byproducts:
                capacity = limits.byproduct_capacity_per_minute.get(product.resource_id, ZERO)
                if capacity < product.rate_per_minute:
                    reasons.add(
                        "Aucune capacité suffisante pour le coproduit "
                        f"{product.display_name}."
                    )
        if limits.max_turbines == 0 or limits.max_generators == 0:
            reasons.add("Aucune turbine ou aucun générateur n'est disponible.")
        if limits.max_steam_cooling_towers == 0 and steam_per_boiler > ZERO:
            if catalog.ventilation.steam_cooling_tower_capacity_m3_per_minute > ZERO:
                reasons.add("Aucune tour de refroidissement n'est disponible.")
        return reasons


__all__ = [
    "RefinedPowerOptimizationError",
    "RefinedPowerOptimizer",
]
