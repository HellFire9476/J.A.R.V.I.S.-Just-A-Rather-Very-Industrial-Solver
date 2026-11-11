# Import du catalogue Satisfactory

## Principe

J.A.R.V.I.S. importe les exports JSON locaux de Satisfactory. L'import est
entièrement hors ligne et ne modifie jamais les fichiers sources.

Le stockage est séparé en trois éléments :

- `core.json` : identifiants de classes, catégories `NativeClass` et propriétés
  techniques (recettes, quantités, durées, machines, valeurs de puissance, etc.) ;
- `locales/<locale>.json` : noms, descriptions et autres champs d'interface du jeu ;
- `manifest.json` : langues importées, noms de fichiers sources, encodages et
  compteurs de contrôle.

Le catalogue est enregistré localement dans `Documents/J.A.R.V.I.S./Catalog`.
Aucune base SQL, connexion réseau ou licence payante n'est nécessaire.

## Importer un seul fichier

Depuis la racine du dépôt :

```powershell
python tools/import_satisfactory_catalog.py "C:\chemin\fr.json"
```

Le code de langue est déduit du nom. Pour un nom de fichier non standard :

```powershell
python tools/import_satisfactory_catalog.py "C:\chemin\export.json" --locale fr
```

## Importer un dossier de langues

Placer les fichiers JSON sources dans un dossier, puis exécuter :

```powershell
python tools/import_satisfactory_catalog.py --directory "C:\chemin\SatisfactoryLocales"
```

Le premier fichier crée `core.json`. Chaque langue suivante doit présenter les
mêmes identifiants, catégories et propriétés techniques. Une différence
technique bloque l'import de cette langue au lieu de remplacer le catalogue.

Pour refuser de remplacer une traduction déjà importée :

```powershell
python tools/import_satisfactory_catalog.py `
  --directory "C:\chemin\SatisfactoryLocales" `
  --no-overwrite
```

## Encodages

Le lecteur détecte les exports UTF-16 avec BOM, UTF-16 sans BOM lorsque la
signature binaire est reconnue, UTF-8 avec BOM et UTF-8.

## Résolution des langues

La consultation essaye successivement la langue exacte, sa langue de base,
puis `en-US` et `fr` par défaut. Une valeur vide n'écrase pas une traduction de
repli. Les paramètres de repli peuvent être adaptés par l'appelant.

## Tests

```powershell
python -m pytest tests/unit -v
python -m compileall -q src/jarvis tests tools
```

Les tests du catalogue utilisent de petits exports synthétiques. Ils couvrent
les encodages, les doublons, la séparation technique/localisée, la compatibilité
entre langues et la résolution des traductions.


## Traductions incomplètes

Les valeurs de type `#02710` et les textes encadrés par `‹...›` sont conservés
dans le fichier de langue et comptabilisés dans le manifeste. Ils sont toutefois
considérés comme des marqueurs non traduits : à l'affichage, J.A.R.V.I.S. utilise
la valeur de repli plutôt que de montrer ces marqueurs à l'utilisateur.

## Vérifier le catalogue

Après un import, exécuter :

```powershell
python tools/validate_catalog.py
```

Le validateur contrôle les compteurs, les liens entre groupes et classes, les
références des traductions, ainsi que les compteurs de marqueurs non traduits.
