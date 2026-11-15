# Gestionnaire de mods

## Objectif

Le gestionnaire de mods sépare le catalogue des modules pris en charge par J.A.R.V.I.S. de leur activation dans un parc précis.

Les premiers modules référencés sont :

- **Refined Power** : chaudières, vapeur, turbines, RPM, alternateurs, sources énergétiques directes et bilan des ressources auxiliaires.
- **Digital Storage** : baies de disques, serveurs 1U/2U, disques d'objets/fluides/gaz, partitions, capacité, bande passante et échanges inter-usines.

## Portée des paramètres

Le catalogue de modules est global à l'application : il décrit les intégrations connues de J.A.R.V.I.S. Il ne signifie pas que le mod est installé dans le jeu Satisfactory. La rubrique **Mods & extensions** est accessible sans ouvrir au préalable une partie ou une page de parc. Elle possède ses propres sélecteurs de partie et de parc ; le catalogue reste consultable même lorsqu'aucune partie n'est enregistrée.

L'activation est stockée dans le fichier `park.json` du parc concerné :

```json
{
  "schema_version": 2,
  "mods": {
    "refined_power": {
      "enabled": true,
      "configuration": {}
    },
    "digital_storage": {
      "enabled": false,
      "configuration": {}
    }
  }
}
```

Chaque parc est indépendant. Ajouter Refined Power à un parc ne l'ajoute pas aux autres. Aucun module n'est activé automatiquement à la création d'un parc.

Désactiver un module ne supprime pas son objet `configuration`. Cela permet de le réactiver plus tard sans perdre ses paramètres.

## État de cette première étape

Cette première étape fournit le catalogue, l'écran de gestion autonome, la sélection d'une partie puis d'un parc, l'activation/désactivation et la persistance JSON. Les équipements et les calculateurs Refined Power et Digital Storage ne sont pas encore implémentés dans cette étape ; l'interface l'indique explicitement. Ils seront ajoutés séparément et raccordés aux bilans de production, d'énergie et de réseau.

La gestion des mods dans J.A.R.V.I.S. ne télécharge pas, n'installe pas et ne vérifie pas les mods présents dans le dossier du jeu.

## Migration

Les anciens parcs en schéma 1 sont chargés avec une configuration `mods` vide et exposés comme schéma 2. Aucun module n'est activé lors de cette migration.
