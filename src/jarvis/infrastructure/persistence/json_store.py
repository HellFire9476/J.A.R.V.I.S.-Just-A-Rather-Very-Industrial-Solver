
import json
from pathlib import Path
from typing import Any, overload

from pydantic import BaseModel


class JsonDataError(Exception):
    """Erreur lors de la lecture ou de la validation d'un JSON."""


@overload
def read_json[T: BaseModel](
    path: Path,
    model_type: type[T],
) -> T:
    ...


@overload
def read_json(
    path: Path,
    model_type: None = None,
) -> dict[str, Any] | list[Any]:
    ...


def read_json[T: BaseModel](
    path: Path,
    model_type: type[T] | None = None,
) -> T | dict[str, Any] | list[Any]:
    """Lit un JSON et valide éventuellement son contenu."""

    path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(
            f"Fichier JSON introuvable : {path}"
        )

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

    except json.JSONDecodeError as error:
        raise JsonDataError(
            f"JSON invalide dans {path}, "
            f"ligne {error.lineno}, colonne {error.colno}."
        ) from error

    except UnicodeDecodeError as error:
        raise JsonDataError(
            f"Encodage incorrect dans le fichier : {path}"
        ) from error

    if model_type is not None:
        return model_type.model_validate(data)

    if not isinstance(data, (dict, list)):
        raise JsonDataError(
            f"Structure JSON inattendue dans {path}."
        )

    return data
