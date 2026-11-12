# Consultation du catalogue des recettes

La page **Recettes** exploite les 872 entrées `FGRecipe` du catalogue Satisfactory.
Elle présente les composants, les temps de cycle, les fabricants compatibles et
les descriptions localisées disponibles dans les exports du jeu.

## Descriptions

Les exports analysés ne fournissent pas de champ `mDescription` pour les recettes
`FGRecipe`. La page affiche donc un **résumé technique calculé** à partir des
entrées, des sorties et du temps de cycle. Ce résumé est explicitement distingué
d'une description narrative du jeu.

Les descriptions des objets sont reprises du champ localisé `mDescription` de
leur descripteur. Les descripteurs de bâtiments `FGBuildingDescriptor` étant
vides pour les champs de nom et de description, leur nom est résolu à partir de
la recette de construction correspondante et, lorsque disponible, la description
à partir de la classe `Build_*` associée.

## Unités de fluides et de gaz

Les quantités brutes de fluides dans les exports sont stockées en litres internes.
La couche métier les normalise en mètres cubes :

- solides : nombre d'objets par cycle ;
- liquides et gaz : volume en m³ par cycle (`valeur brute / 1 000`) ;
- recettes automatisées : débit théorique à 100 % calculé en objets/min ou m³/min
  (`quantité normalisée × 60 / durée du cycle en secondes`).

La valeur source brute reste disponible dans `RecipeComponent.source_amount` pour
traçabilité. Les recettes manuelles et de construction n'affichent pas de débit
par minute, car ce débit ne correspond pas à une cadence de machine automatisée.

Les données sources ne sont jamais modifiées par cette normalisation.
