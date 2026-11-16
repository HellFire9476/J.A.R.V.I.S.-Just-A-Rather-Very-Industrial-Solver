# Correctif — Affichage numérique homogène

## Objectif

Les valeurs numériques présentées dans l'interface ne doivent plus afficher de zéros décimaux inutiles ni de longues représentations flottantes.

## Règles d'affichage

- Les champs numériques Qt conservent leur précision technique, mais masquent les zéros décimaux insignifiants.
- Les débits, objectifs, quantités et pourcentages sont affichés avec au plus trois décimales, sans zéros finaux.
- Les puissances sont affichées avec au plus deux décimales, sans zéros finaux.
- Le séparateur décimal est la virgule ; les nombres importants peuvent utiliser une espace insécable pour les milliers.
- L'arrondi concerne exclusivement le rendu. Les valeurs des calculs et les instantanés JSON restent inchangés.

## Zones concernées

- Champ d'objectif dans Simulations et réglages de cadence des machines/extracteurs.
- Fenêtre d'enregistrement d'une simulation dans une usine.
- Liste et détail des scénarios enregistrés dans les usines.
- Valeurs de l'écran Refined Power et de son optimiseur.
- Valeurs numériques affichées dans l'explorateur de recettes.

## Tests ajoutés ou ajustés

- Cas de formatage entier, fractionnaire, négatif proche de zéro et regroupement des milliers.
- Affichage compact du champ de débit de simulation.
- Affichage compact des détails d'un scénario enregistré.
- Affichage compact du champ de puissance cible Refined Power.

Les tests Qt doivent être exécutés dans l'environnement Windows du projet avec PySide6 installé.
