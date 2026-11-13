# Moteur de calcul de production — première version

## Objectif

Le moteur transforme un objectif unique — par exemple `60` plaques de fer par
minute — en une décomposition récursive des recettes, des besoins de matières
premières, des fabricants, des extracteurs et d'une estimation électrique.

Le moteur métier (`engines/production_engine.py`) est indépendant de PySide6 et
du stockage JSON. Le service applicatif (`ProductionService`) adapte le
catalogue importé vers les profils attendus par le moteur.

## API

```python
from jarvis.application.services.production_service import ProductionService

service = ProductionService()
plan = service.plan_production(
    target_class_name="Desc_IronPlate_C",
    target_rate_per_minute=60,
    locale="fr",
)
```

Les débits sont exprimés en objets/min pour les solides et en m³/min pour les
liquides et les gaz. Les quantités fluides du catalogue, stockées en litres
internes, sont déjà normalisées par `RecipeService` avant d'entrer dans le
moteur.

Pour imposer une recette parmi plusieurs possibilités :

```python
plan = service.plan_production(
    target_class_name="Desc_Plastic_C",
    target_rate_per_minute=120,
    locale="fr",
    recipe_choices={"Desc_Plastic_C": "Recipe_Plastic_C"},
)
```

`list_recipe_options(class_name, locale)` expose les recettes candidates pour
un futur sélecteur dans l'interface. Si plusieurs recettes standard restent
possibles, le moteur lève `RecipeChoiceRequiredError` au lieu de choisir une
méthode silencieusement.

## Règles de calcul

- Les ressources de type `FGResourceDescriptor` sont considérées comme des
  entrées naturelles par défaut, même si des recettes peuvent aussi les
  fabriquer. Une recette de fabrication peut être imposée explicitement.
- Une recette standard unique est sélectionnée automatiquement. Les variantes
  marquées `Alternate` sont écartées lorsqu'une recette standard unique existe.
  Si plusieurs possibilités restent plausibles, le choix est demandé par une
  exception métier dédiée.
- Les recettes sont développées récursivement jusqu'aux entrées sans recette
  sélectionnée. Une dépendance circulaire provoque `ProductionCycleError`.
- Les fabricants sont dimensionnés en équivalents, puis arrondis au nombre
  entier supérieur. Les machines installées sont sous-cadencées ensemble pour
  atteindre le débit demandé sans dépasser 100 % de cadence.
- La puissance fixe est estimée avec la consommation de base, le nombre de
  machines, la cadence calculée et l'exposant électrique fourni par le jeu.
  Les fabricants à puissance variable utilisent les bornes minimales/maximales
  de l'export. Si le catalogue ne fournit pas la puissance, le résultat est
  marqué incomplet plutôt que de présenter `0 MW` comme une valeur réelle.
- Les profils d'extraction sont construits depuis les propriétés des bâtiments
  présents dans le catalogue : vitesse de cycle, quantité par cycle, forme de
  ressource et restrictions éventuelles. Les volumes extraits sont convertis
  en m³/min. Les multiplicateurs de rendement de gisement sont fournis par
  l'appelant et valent `1` par défaut.

## Limites explicites de cette version

Cette première version est un calculateur récursif à cible unique, pas encore un
optimiseur global de réseau.

- Les coproduits sont calculés et affichés, mais ils ne sont pas encore déduits
  des besoins d'une autre branche. Le plan émet un avertissement quand il en
  génère. Il ne faut donc pas interpréter les entrées comme un bilan matière
  net dans les chaînes qui réutilisent ces coproduits.
- Les boucles de recyclage et les dépendances circulaires ne sont pas résolues
  par équilibrage : elles sont signalées comme cycles.
- Le surcadencement, les Power Shards, le nombre réel de nœuds, les limites de
  convoyeurs et de pipelines, les pressuriseurs de puits, les contraintes de
  réseau et les pertes de transport ne sont pas dimensionnés.
- Les extracteurs de puits de ressources sont identifiés, mais le pressuriseur
  et la capacité globale du puits ne sont pas calculés. Leur puissance reste
  inconnue si le catalogue ne la fournit pas.
- Le moteur n'est pas encore connecté à la page Simulations. Cette étape
  valide d'abord le domaine, le service et les calculs automatisés.

## Vérification

```powershell
python -m pytest tests/unit -v
python -m compileall -q src/jarvis tests tools
```

Les tests du moteur utilisent des catalogues synthétiques et des profils
contrôlés. Une vérification manuelle complémentaire est également effectuée
sur les exports français et anglais du catalogue complet.
