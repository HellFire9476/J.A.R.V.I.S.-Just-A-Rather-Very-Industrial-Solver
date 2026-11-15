# Refined Power — socle Modular Power

## Périmètre de cette première étape

Cette livraison met en place le catalogue technique local, les modèles de configuration par parc, le calcul d'une chaîne **chauffage + combustible → chaudière → vapeur haute pression → turbine → générateur**, ainsi que les contrôles d'évacuation du CO₂ et de la vapeur basse pression.

Les sources directes (éoliennes, solaire, turbines hydrauliques, barrages), les réacteurs, Project Icarus, les schémas visuels et l'interface de configuration sont des étapes distinctes. Ils ne sont pas simulés par ce premier moteur.

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

Structure de configuration :

```json
{
  "schema_version": 1,
  "catalog_version": "2026.3.26",
  "chains": []
}
```

## Sources documentaires

- [Page du mod Refined Power](https://ficsit.app/mod/RefinedPower)
- [Heaters](https://docs.ficsit.app/refinedrd/latest/rp/buildings/modularpower/MP-Heaters.html)
- [Boilers](https://docs.ficsit.app/refinedrd/latest/rp/buildings/modularpower/MP-Boilers.html)
- [Turbines](https://docs.ficsit.app/refinedrd/latest/rp/buildings/modularpower/MP-Turbines.html)
- [Generators](https://docs.ficsit.app/refinedrd/latest/rp/buildings/modularpower/MP-Generators.html)
- [Chimneys](https://docs.ficsit.app/refinedrd/latest/rp/buildings/modularpower/MP-Chimneys.html)

Le profil de consommation des fleurs est mentionné dans la liste des combustibles Biomass du mod, mais aucun débit chiffré ne figure dans la table de consommation consultée : il n'est donc pas proposé comme combustible calculable dans cette version du catalogue. Les valeurs doivent être revérifiées si la version de Refined Power est différente de celle du catalogue.

Les pages documentaires utilisées sont publiées sous le chemin `latest`. Le catalogue enregistre donc la version du mod et la date de révision pour permettre une mise à jour ciblée des données lorsque les statistiques évoluent.
