
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from pydantic import BaseModel


def write_json_atomic(
    path: Path,
    data: BaseModel | dict[str, Any] | list[Any],
) -> None:
    """Enregistre un JSON en limitant les risques de corruption."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(data, BaseModel):
        payload = data.model_dump(mode="json")
    else:
        payload = data

    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        indent=4,
        allow_nan=False,
    )

    temp_path = None

    try:
        file_descriptor, temp_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
        )

        temp_path = Path(temp_name)

        with os.fdopen(
            file_descriptor,
            mode="w",
            encoding="utf-8",
            newline="\n",
        ) as temp_file:
            temp_file.write(serialized)
            temp_file.write("\n")
            temp_file.flush()
            os.fsync(temp_file.fileno())

        # Remplacement atomique sur le même volume.
        os.replace(temp_path, path)

    except Exception:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)

        raise
