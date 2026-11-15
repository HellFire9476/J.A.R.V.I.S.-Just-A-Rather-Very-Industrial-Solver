# Page Simulations — J.A.R.V.I.S. 2.0

## Objectif

La page Simulations expose le moteur de production à l'utilisateur sans déplacer
la logique de calcul dans PySide6. Elle est indépendante des parties et des parcs :
elle lit le catalogue Satisfactory local et calcule un besoin théorique à partir
d'un objectif de production et des recettes disponibles. Aucun stock, bâtiment
posé ou équipement possédé dans une sauvegarde n'est consulté.

## Parcours utilisateur

1. Choisir un produit fabriqué par au moins une recette automatisée.
2. Définir un objectif en objets/min ou m³/min selon la forme du produit.
3. Choisir la langue du catalogue.
4. Sélectionner une recette si plusieurs recettes automatisées sont disponibles.
5. Lancer le calcul.
6. Consulter les fabricants, les ressources, les options d'extraction, les
   coproduits et l'estimation énergétique.
7. Changer un extracteur dans le tableau des ressources pour recalculer le plan.
8. Régler le plafond de cadence des fabricants et extracteurs (1 à 250 %) ; le
   moteur recalcule le nombre entier de machines et leur cadence réelle uniforme.

## Chargement et threads

Le catalogue de cibles et le calcul du plan sont exécutés dans des QThread dédiés.
La page attend leur terminaison lors de la fermeture de la fenêtre afin d'éviter
la destruction d'un thread Qt encore actif.

## Portée actuelle

- Le plan est consultatif : il n'est pas encore enregistré comme scénario.
- Les réglages de pureté des gisements ne sont pas encore proposés dans l'interface.
- Les recettes ambiguës sont proposées dans le sélecteur ; le moteur reste l'autorité
  finale sur la validité du choix.
- Les options d'extraction disponibles peuvent être sélectionnées et déclenchent un
  nouveau calcul.
- Chaque ligne de fabrication et d'extraction expose un plafond de cadence réglable.
  Le plafond réduit éventuellement le nombre de machines ; la cadence réellement
  appliquée est recalculée pour couvrir exactement le débit demandé, sans surproduction.
- Les tableaux affichent la puissance cumulée des fabricants et des extracteurs ;
  les nombres sont limités à deux décimales pour rester lisibles.
- Les choix de recettes affichent leurs ingrédients, leurs produits et leurs fabricants,
  sans exposer les identifiants internes des classes dans les libellés.
- Les coproduits sont affichés séparément et ne compensent pas encore les besoins
  d'autres branches.
- Les calculs de réseaux de puits et leurs pressuriseurs restent signalés comme
  incomplets par le moteur.
- Les paramètres et résultats d'un scénario ne sont pas encore persistés. La
  simulation n'est pas rattachée à une partie ou à un parc.

## Dépendances

- `ProductionService` prépare les données du catalogue et appelle le moteur.
- `ProductionEngine` reste indépendant de Qt.
- `CatalogRepository` lit les données JSON locales.

## Aides contextuelles

Les commandes, sélecteurs, en-têtes de tableaux, cellules de résultats et indicateurs
de synthèse possèdent des info-bulles. Elles décrivent les unités, les hypothèses et
les calculs utilisés : nombre physique de bâtiments, équivalents à 100 %, plafond de
cadence, cadence réellement appliquée, puissance connue, extraction et coproduits.
Les identifiants de classes restent internes et ne sont pas affichés dans les libellés
ou les info-bulles destinés au joueur.
