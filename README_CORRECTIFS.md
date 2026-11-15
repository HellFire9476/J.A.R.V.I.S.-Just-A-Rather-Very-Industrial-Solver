# Correctifs et validation — Refined Power

Cette archive est une copie complète du projet J.A.R.V.I.S. 2.0, avec les
correctifs ciblés décrits ci-dessous. Son contenu peut être extrait directement
dans le dossier racine du projet.

## Correctifs apportés

- `RefinedPowerService.create_chain()` et `update_chain()` revalident désormais
  la configuration reçue avant toute écriture. Cela réexécute les validations
  Pydantic, puis le moteur vérifie l'existence des profils, les compatibilités et
  le point de fonctionnement. Cette sécurité s'applique aussi aux appels directs
  au service, sans dépendre de l'écran graphique.
- Les mises à jour invalides sont rejetées sans modifier la chaîne déjà enregistrée.
- Un combustible ne peut plus déclarer deux fois le même identifiant de coproduit.
  Les limites de capacité étant indexées par identifiant, cette validation évite
  qu'une quantité agrégée dépasse une capacité alors que chaque ligne individuelle
  semblait l'accepter.

## Tests ajoutés

- Rejet d'une création avec chauffage et combustible incompatibles.
- Rejet d'une mise à jour incompatible sans altérer la configuration enregistrée.
- Revalidation d'un modèle altéré avec `model_copy(update=...)`.
- Détection des identifiants de coproduits dupliqués dans un même combustible.
- Vérification des générateurs surnuméraires, des turbines sans générateur et de
  l'absence de turbines.

## Validation exécutée dans l'environnement de préparation

- `python -m pytest tests/unit -q` : **114 réussis, 17 ignorés**.
- `python -m compileall -q src/jarvis tests tools` : **réussi**.
- Les 17 tests ignorés dépendent de PySide6, non installé dans cet environnement.
- Ruff n'est pas installé et l'accès au dépôt de paquets n'est pas disponible ici :
  le contrôle Ruff n'a donc pas été exécuté.
- L'environnement de préparation utilise Python 3.13.5, tandis que le projet
  déclare Python 3.14.x. La validation finale doit être répétée dans le `.venv`
  Windows du projet avec Python 3.14.5 et PySide6.

## Validation finale sur Windows

Depuis la racine du dépôt, dans le terminal où `.venv` est activé :

```powershell
python -m ruff check src/jarvis tests
python -m ruff check --fix --show-fixes src/jarvis tests
python -m ruff check src/jarvis tests
python -m compileall -q src/jarvis tests tools
python -m pytest tests/unit -v
```

Ne pas committer si Ruff, la compilation ou les tests échouent. Puis vérifier
`git diff --check` et `git status --short`.
