# Refined Power — socle Modular Power

## Périmètre de cette première étape

Cette livraison met en place le catalogue technique local, les modèles de configuration par parc, le calcul d'une chaîne **chauffage + combustible → chaudière → vapeur haute pression → turbine → générateur**, ainsi que les contrôles d'évacuation du CO₂ et de la vapeur basse pression.

Les sources directes (éoliennes, solaire, turbines hydrauliques, barrages), les réacteurs, Project Icarus, les schémas visuels et l'interface de configuration sont des étapes distinctes. Ils ne sont pas simulés par ce premier moteur.

Chaque combustible doit également déclarer au plus une entrée par identifiant de
coproduit. Les capacités du solveur sont indexées par identifiant de ressource ;
refuser les doublons empêche qu'un même coproduit soit comptabilisé séparément
plusieurs fois lors du contrôle des capacités, puis agrégé dans le résultat final.

## Données du catalogue

Le fichier `resources/catalogs/refined_power/modular_power.json` est autonome et versionné. Il identifie le mod `2026.3.26` et conserve les URL documentaires utilisées pour constituer les profils.

Les unités des débits sont exprimées par minute :

- combustibles solides et résidus : `item/min` ;
- combustibles et fluides : `m³/min` ;
- eau et vapeur : `m³/min` ;
- puissance : `MW` ;
- vitesse : `RPM`.

## Méthode de calcul

1. Le profil de combustible détermine le chauffage compatible, le débit d'entrée, la température de fonctionnement, le CO₂ et les éventuels coproduits.
2. Le point de fonctionnement de la chaudière est sélectionné à la température fournie par le combustible. Une chaudière Mk.1 reste à son débit nominal de 60 m³/min au-delà de 500 °C ; le moteur signale la chaleur excédentaire perdue.
3. Le débit total de vapeur haute pression est comparé à la demande des turbines.
4. La vapeur basse pression produite est comparée à la capacité des Steam Cooling Towers.
5. Le CO₂ produit est comparé à la capacité des CO₂ Chimneys.
6. La puissance électrique est calculée à partir de la table de compatibilité turbine/générateur.

À pleine alimentation vapeur, les puissances par combinaison reprennent les valeurs du tableau officiel. En alimentation partielle, le moteur applique une interpolation linéaire proportionnelle au régime RPM. La documentation décrit une montée/descente de puissance avec le régime, mais ne publie pas sa courbe exacte : ces valeurs partielles sont donc explicitement des estimations.

Le moteur calcule un régime permanent. Il ne simule pas encore le temps de montée en température, l'inertie de démarrage des turbines, les pertes transitoires, ni le comportement détaillé des réseaux et des plateformes.

## Persistance

Les chaînes sont enregistrées dans `park.mods["refined_power"].configuration` via `ParkRepository`. Chaque parc conserve ses propres configurations. La désactivation du module ne détruit pas ses chaînes ; les opérations de modification et de calcul exigent que Refined Power soit activé sur le parc.

Avant une création ou une modification, `RefinedPowerService` reconstruit le modèle à
partir de ses données afin de réexécuter les validations Pydantic, puis demande au
moteur de vérifier les profils, les compatibilités chauffage/combustible et les
points de fonctionnement. Cette validation est appliquée au niveau du service,
pas uniquement dans l'interface : un appel direct au service ne peut donc pas
enregistrer une chaîne structurellement invalide ou impossible à calculer. Un
équilibrage physique imparfait reste enregistrable pour permettre sa consultation
et sa correction ; il continue d'être signalé par le résultat du moteur.

Structure de configuration :

```json
{
  "schema_version": 1,
  "catalog_version": "2026.3.26",
  "chains": []
}
```

## Interface de gestion Modular Power

La rubrique **Refined Power** est accessible depuis la navigation principale. Elle permet
de sélectionner une partie et un parc, puis de gérer les chaînes Modular Power associées
à ce parc. Cette page ne crée ni partie ni parc et n'active pas automatiquement le mod.

Lorsque Refined Power est désactivé sur le parc, les chaînes existantes restent visibles
en lecture seule. Le bouton **Gérer les modules** ouvre la rubrique Mods & extensions sur
la partie et le parc actuellement sélectionnés. L'activation reste une action explicite.

Lorsque le module est actif, l'interface permet de créer, modifier, dupliquer et supprimer
une chaîne homogène. Le bilan est prévisualisé à mesure que les paramètres changent, sans
enregistrement automatique. L'enregistrement valide d'abord la configuration avec le moteur,
puis passe par `RefinedPowerService`.

Les résultats affichent la puissance, le combustible, l'eau, le régime de turbine, les flux
de vapeur haute et basse pression, le CO₂, les sous-produits et les avertissements du moteur.
L'interface ne recalcule pas elle-même les règles métier.

La page ne couvre pour le moment que **Modular Power**. Elle n'intègre pas encore les
sources directes, les réacteurs, Project Icarus ni le bilan énergétique global du parc.


## Équilibrage automatique — moteur de proposition

Le solveur `RefinedPowerOptimizer` est un composant indépendant de l'interface.
Il utilise les profils et les tables de compatibilité du catalogue local pour
proposer des quantités entières de chaudières, turbines, générateurs, cheminées
CO₂ et tours de refroidissement. Il ne modifie jamais une chaîne persistée.

Trois modes sont disponibles via `RefinedPowerService.preview_optimization` :

- `balance_existing` conserve les types d'équipements et le nombre de chaudières
  d'une chaîne de référence, puis recalcule le nombre de turbines, de générateurs
  et d'équipements d'évacuation nécessaires ;
- `maximize` recherche la puissance électrique estimée la plus élevée possible
  sous les limites fournies ;
- `target` recherche une solution atteignant au moins la puissance demandée avec
  le plus faible dépassement possible. Si la cible est inaccessible, la meilleure
  puissance faisable est retournée avec `target_reached=False`.

Les limites peuvent porter sur le débit d'eau disponible, la quantité de chaque
combustible (`fuel_available_per_minute`, dans l'unité de son profil catalogue),
les quantités maximales d'équipements et les capacités de traitement des
coproduits. Un combustible ou un débit d'eau sans limite explicite est considéré
comme disponible sans plafond ; il faut donc renseigner les ressources pertinentes
pour obtenir un scénario représentatif. Les modes `maximize` et `target` exigent
un plafond explicite de chaudières : le solveur n'invente ainsi pas un nombre
illimité de bâtiments et le résultat est clairement borné par le matériel annoncé.
Les limites des autres équipements laissées à `None` sont bornées en interne à
10 000 unités, conformément aux maxima des modèles de configuration. Un coproduit sans capacité déclarée est considéré comme non géré et
écarte la solution : les déchets nucléaires ou les autres sorties ne sont donc
pas ignorés silencieusement. Les cheminées et tours nécessaires sont calculées
à partir des capacités documentées du catalogue.

L'optimisation est une recherche déterministe sur des quantités entières et des
combinaisons existantes dans la table turbine/générateur. Elle ne compare pas
les valeurs de consommation de combustibles de familles d'unités différentes
comme si elles étaient directement équivalentes. En cas d'égalité de puissance,
le mode `maximize` préfère moins d'eau, moins de CO₂ puis moins d'équipements.
Le mode `target` minimise d'abord le dépassement, puis le nombre d'équipements,
l'eau et le CO₂. L'ordre du catalogue départage les égalités restantes.

La solution renvoie la configuration proposée, le calcul après optimisation,
le calcul de référence lorsqu'il existe, la liste des changements, les limites
non satisfaites et les avertissements. Le résultat reste une prévisualisation :
aucune donnée persistée n'est modifiée par le solveur.

Le panneau **Équilibrage automatique** expose les trois modes du solveur.
Il permet de choisir une chaîne de référence, les profils autorisés, les bornes
matérielles, les ressources disponibles et les capacités d'accueil des coproduits.
Les modes de recherche exigent un plafond explicite de chaudières.

La prévisualisation affiche la puissance avant/après, les ressources consommées,
les changements proposés, les contraintes non satisfaites et les avertissements.
Toute modification des paramètres invalide la proposition précédente afin
qu'une solution calculée avec d'anciennes limites ne puisse pas être appliquée.

Le bouton **Appliquer la proposition** déclenche une confirmation explicite.
Une chaîne de référence est mise à jour ; une recherche de puissance maximale
ou cible crée une nouvelle chaîne. Le service existant effectue la persistance
uniquement après confirmation. Le solveur et le panneau ne sauvegardent rien
pendant la prévisualisation.

Le panneau ne constitue pas encore un planificateur multi-chaînes ou multi-parcs :
chaque recherche porte sur une seule chaîne homogène Modular Power. Les ressources
sont les limites saisies par l'utilisateur, pas un inventaire automatiquement
lu dans le parc. Les calculs à régime partiel restent signalés comme estimations
conformément aux limites du moteur Modular Power actuel.

## Aide intégrée et langues du catalogue

Le panneau **Équilibrage automatique** présente une explication mise à jour selon le
mode choisi et un tutoriel express repliable. Le guide décrit les six étapes :
activation du module, choix du mode, saisie des limites, gestion des coproduits,
lecture de la prévisualisation et confirmation de l'application. Des infobulles
complètent les champs de ressources et de limites matérielles.

La page Refined Power dispose d'un sélecteur **Langue du catalogue**. Il agit sur
les noms affichés des ressources, combustibles, chauffages, chaudières, turbines,
générateurs et coproduits, ainsi que sur les noms repris dans les résultats et les
propositions de l'optimiseur. Les identifiants techniques, les paramètres et les
calculs ne changent jamais avec la langue.

Pour les ressources du jeu de base, le catalogue Refined Power associe les profils
aux identifiants de classes Satisfactory (`game_class_name`). Le nom est récupéré
dans le catalogue de langue local importé par l'utilisateur. Les profils propres
au mod, qui ne sont pas nécessairement présents dans un export du jeu de base,
utilisent des traductions embarquées (`localized_names`). Les libellés français
et les noms anglais par défaut sont fournis. Si une traduction n'existe pas pour
une langue choisie, le nom anglais du profil est utilisé en repli.

Le sélecteur suit la convention actuelle des pages Recettes et Simulations : la
langue du catalogue est choisie dans chaque page. Il ne constitue pas encore un
réglage global partagé entre toutes les rubriques. Les textes de l'interface et
du tutoriel restent en français dans cette version ; seule la langue des noms du
catalogue est changée par ce sélecteur.

## Sources documentaires

- [Page du mod Refined Power](https://ficsit.app/mod/RefinedPower)
- [Heaters](https://docs.ficsit.app/refinedrd/latest/rp/buildings/modularpower/MP-Heaters.html)
- [Boilers](https://docs.ficsit.app/refinedrd/latest/rp/buildings/modularpower/MP-Boilers.html)
- [Turbines](https://docs.ficsit.app/refinedrd/latest/rp/buildings/modularpower/MP-Turbines.html)
- [Generators](https://docs.ficsit.app/refinedrd/latest/rp/buildings/modularpower/MP-Generators.html)
- [Chimneys](https://docs.ficsit.app/refinedrd/latest/rp/buildings/modularpower/MP-Chimneys.html)

Le profil de consommation des fleurs est mentionné dans la liste des combustibles Biomass du mod, mais aucun débit chiffré ne figure dans la table de consommation consultée : il n'est donc pas proposé comme combustible calculable dans cette version du catalogue. Les valeurs doivent être revérifiées si la version de Refined Power est différente de celle du catalogue.

Les pages documentaires utilisées sont publiées sous le chemin `latest`. Le catalogue enregistre donc la version du mod et la date de révision pour permettre une mise à jour ciblée des données lorsque les statistiques évoluent.


## Langues du catalogue et noms affichés

Le sélecteur de langue de Refined Power utilise les langues importées dans le
catalogue Satisfactory. Les variantes régionales sont conservées : si seul
`fr-FR` est disponible, le choix français utilise ce catalogue même si une
fonction demande la langue générique `fr`. Les identifiants techniques des
ressources et des machines ne sont jamais traduits.

Les ressources disposant d'un `game_class_name` sont résolues depuis les
traductions Satisfactory importées. Les équipements propres à Refined Power
utilisent `localized_names` dans `resources/catalogs/refined_power/
modular_power.json`. Le français est embarqué dans le catalogue du mod ; les
autres langues retombent sur le nom anglais `display_name` tant qu'une
traduction dédiée n'a pas été ajoutée.

### Exemple d'utilisation de l'équilibrage

Pour viser 500 MW, choisir le mode « Puissance cible », saisir 500 MW,
sélectionner le combustible souhaité et définir les limites matérielles :
nombre maximal de chaudières, capacité de refroidissement, évacuation du CO₂
et capacité de traitement des coproduits. L'aperçu indique la puissance
atteignable et les équipements nécessaires. Une prévisualisation ne modifie
pas la sauvegarde ; l'utilisateur doit appliquer explicitement la proposition.
