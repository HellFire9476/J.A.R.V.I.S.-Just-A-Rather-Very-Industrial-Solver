# Gestion des usines et scénarios de production

## Périmètre de ce premier incrément

Une usine est rattachée à un projet et à un parc précis. Les usines ne sont pas
partagées entre les parcs. Chaque usine possède un historique de scénarios de
production enregistrés depuis la page Simulations.

Le premier incrément permet de :

- créer une usine vide depuis la page **Usines** ;
- enregistrer le résultat courant d'une simulation dans une nouvelle usine ou
  dans une usine existante ;
- consulter les scénarios enregistrés et leur bilan ;
- renommer une usine et modifier sa description ;
- archiver une usine avec tous ses scénarios dans le centre d'archives.

## Stockage JSON

Les données utilisateur restent dans le dossier utilisateur J.A.R.V.I.S. :

```text
Documents/J.A.R.V.I.S./Projects/{project_id}/parks/{park_id}/factories/
├── index.json
└── {factory_id}/
    ├── factory.json
    └── scenarios.json
```

L'index du parc ne référence que les usines actives. Lorsqu'une usine est
archivée, son dossier complet est déplacé dans `Archives/Factories` par le
mécanisme central d'archivage. Les scénarios restent inclus dans cette archive.

## Instantané d'un scénario

Un scénario conserve :

- le produit cible, le débit, l'unité et la langue du catalogue ;
- les paramètres d'entrée transmis au moteur (recettes, fabricants,
  extracteurs et limites de cadence) ;
- une copie JSON complète du `ProductionPlan` calculé ;
- la date d'enregistrement.

L'instantané est un historique consultatif : il ne se recalcule pas lorsque le
catalogue Satisfactory change. Le moteur de production reste indépendant de
PySide6 et aucun calcul n'est déplacé dans l'interface. Si la partie active change
pendant un calcul asynchrone, le résultat de l'ancienne requête est écarté et ne
peut pas être enregistré dans la nouvelle partie.

## Limites assumées

Ce premier incrément ne gère pas encore les lignes de production multiples,
les bâtiments réellement posés, les stocks, les transferts entre usines ou la
synchronisation avec une sauvegarde de jeu. Ces sujets seront construits dans
les chantiers Réseau industriel et Extraction.


## Chemins Windows

Les scénarios d'une usine sont regroupés dans `scenarios.json` plutôt que dans
un fichier par UUID. Cette structure compacte évite de dépasser la limite
historique de longueur des chemins Windows lorsque les dossiers projet, parc
et usine sont imbriqués. L'écriture atomique utilise également un nom
temporaire court. Les anciennes archives au format individuel restent
reconnues lors de leur lecture et de leur restauration.
