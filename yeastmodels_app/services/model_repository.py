"""Model loading and cache boundary."""

from __future__ import annotations

from contextlib import contextmanager
from functools import cached_property
import logging
from pathlib import Path
from typing import Iterator

from cobra.io import read_sbml_model

from yeastmodels_app.config import DEFAULT_MODEL_PATH


class ModelRepository:
    """Load the GEM once and provide safe model contexts."""

    def __init__(self, model_path: Path = DEFAULT_MODEL_PATH) -> None:
        self.model_path = Path(model_path)
        logging.getLogger("cobra").setLevel(logging.ERROR)

    @cached_property
    def model(self):
        return read_sbml_model(str(self.model_path))

    @contextmanager
    def model_context(self) -> Iterator[object]:
        with self.model as model:
            yield model
