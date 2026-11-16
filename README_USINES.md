# J.A.R.V.I.S. 2.0 — Premier incrément de gestion des usines

Cette livraison ajoute un premier parcours vertical pour enregistrer et gérer les
usines de production à l'intérieur des parcs industriels.

## Utilisation

1. Ouvrir une partie et créer au moins un parc industriel.
2. Depuis **Simulations**, lancer un calcul de production.
3. Utiliser **Enregistrer dans une usine** sous le résultat.
4. Choisir le parc, puis créer une usine ou ajouter le scénario à une usine existante.
5. Ouvrir **Usines** dans la navigation pour consulter, renommer ou archiver les usines.

Un scénario conserve les paramètres utilisés et un instantané JSON complet du
résultat du moteur. Il ne se recalcule pas automatiquement si le catalogue est
mis à jour.

## Stockage

Les fichiers sont créés dans le dossier utilisateur, sous :

`Documents/J.A.R.V.I.S./Projects/{project_id}/parks/{park_id}/factories/`

Aucune base de données externe ou payante n'est utilisée. L'archivage déplace le
dossier complet de l'usine et ses scénarios dans le centre d'archives central.

## Portée

Cette version ne gère pas encore les bâtiments réellement posés, plusieurs lignes
interconnectées, les stocks ou les transferts entre usines. Ces fonctions seront
traitées dans les chantiers Réseau industriel et Extraction.

Les scénarios sont regroupés dans `scenarios.json` afin de conserver
des chemins courts et compatibles avec Windows.
