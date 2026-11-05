# J.A.R.V.I.S. — Planificateur d'usines Satisfactory

J.A.R.V.I.S. est une application de bureau Windows qui aide à concevoir et équilibrer des usines Satisfactory. Elle rassemble les machines, les recettes, les ressources, l'énergie et les coûts de construction dans un même projet, organisé par usines.

> Projet communautaire non officiel, non affilié à Coffee Stain Studios ni aux créateurs de Satisfactory.

## Fonctionnalités

- **Plusieurs usines** : créer, renommer, sélectionner et supprimer des usines ; leurs données sont conservées séparément dans le dossier Documents de l'utilisateur.
- **Ateliers de production** : ajouter des machines, choisir une recette standard ou alternative, régler leur quantité, leur cadence et leurs Somersloops, puis consulter les flux de production.
- **Foreuses et extracteurs** : choisir le type de machine, la ressource, la quantité, la pureté du gisement et la cadence.
- **Bilan de l'usine** : afficher les machines utilisées, les flux de ressources produits ou consommés, les besoins électriques et les éventuels déficits ou surplus.
- **Énergie et Refined Power** : configurer des parcs énergétiques et des chaînes Refined Power, puis estimer leur production, leurs besoins et leurs consommations.
- **Auto-solveur** : explorer une chaîne de production pour un objet cible et aider à déterminer les machines et débits à prévoir.
- **Digital Storage** : configurer l'infrastructure de serveurs, ses capacités et ses flux d'import ou d'export.
- **Mods et laboratoire** : ajuster des règles de calcul et les paramètres des machines personnalisées.
- **Recettes, coûts et stacks** : consulter le catalogue des recettes, calculer des besoins de construction configurés et retrouver les tailles de stacks.
- **Wiki et images** : consulter des pages d'aide intégrées et les compléter avec du contenu et des images.
- **Interface personnalisable** : thème, affichage en ligne ou en cartes, aides contextuelles, sauvegarde et restauration des projets.
- **Mises à jour** : l'exécutable vérifie les nouvelles versions publiées, propose leur installation et contrôle l'empreinte SHA-256 avant de remplacer le programme.

Les recettes de production sont fournies par le fichier CSV du projet. Certaines machines, recettes ou règles de mods peuvent nécessiter une configuration adaptée à la partie jouée.

## Lancer depuis les sources

Prérequis : Windows et Python 3.14.

Dans PowerShell, place-toi dans le dossier du projet puis exécute :

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

Le fichier `Planificateur Satisfactory - Recettes.csv` doit rester à côté de `main.py`.

## Construire et publier une version Windows

La compilation se fait sur ton propre PC ; GitHub Actions n'est pas nécessaire. Avec l'environnement virtuel activé :

```powershell
python -m unittest discover -s tests -v
python -m PyInstaller --noconfirm JARVIS.spec
```

L'exécutable est produit dans `dist\JARVIS.exe`.

Pour publier une nouvelle version :

1. Modifier `VERSION_APPLICATION` dans `main.py` et l'augmenter (par exemple `1.0.2` après `1.0.1`).
2. Lancer les tests et construire `dist\JARVIS.exe` avec les commandes ci-dessus.
3. Enregistrer et pousser les changements de code sur la branche `main`.
4. Créer et pousser un tag `v` correspondant exactement à cette version :

   ```powershell
   git add -A
   git commit -m "Release v1.0.2"
   git push origin main
   git tag v1.0.2
   git push origin v1.0.2
   ```

5. Sur GitHub, crée une Release depuis le tag `v1.0.2`, joins le fichier `dist\JARVIS.exe`, puis publie-la. L'application vérifie les Releases publiques et télécharge l'exécutable en arrière-plan ; chaque utilisateur peut choisir quand redémarrer pour installer la mise à jour. Il n'a pas besoin de visiter GitHub lui-même.

La version `v1.0.0` ne contient pas le mécanisme de mise à jour. Ses utilisateurs doivent installer `v1.0.1` manuellement une première fois ; les versions ultérieures pourront ensuite s'installer depuis l'application.

Le dépôt doit rester public pour que l'application et les amis qui l'utilisent puissent accéder aux Releases sans authentification. Les données de l'usine restent séparées du programme et ne sont pas envoyées à GitHub. Les binaires ne sont pas conservés dans le dépôt source : ils sont ajoutés comme fichiers joints aux Releases.

## Vérifier les tests

```powershell
python -m unittest discover -s tests
```

## Fichiers du projet

- `main.py` : code source de l'application.
- `Planificateur Satisfactory - Recettes.csv` : catalogue des recettes utilisé par l'application.
- `icone.ico` : icône de l'application.
- `JARVIS.spec` : configuration de génération de l'exécutable PyInstaller.
- `requirements.txt` : dépendances Python et version de PyInstaller.

Les plans d'usines, réglages et données personnelles ne sont pas stockés dans le dépôt : l'application les conserve dans les dossiers Documents de chaque utilisateur.
