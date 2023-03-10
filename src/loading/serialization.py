from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import guitarpro as gm
from guitarpro.models import Song
from music21 import converter
from music21.stream.base import Score


class Serializer(ABC):
    """Interface for concrete Seralization methods."""

    @abstractmethod
    def dump(self, obj: Any, save_path: Path) -> None:
        pass

    @abstractmethod
    def load(self, load_path: Path) -> Any:
        pass


class PyGuitarProSerializer(Serializer):

    """Saves and loads a GuitarPro file. It's a concrete serializer."""
    def dump(self, gp_stream: Song, save_path: Path) -> None:
        gm.write(gp_stream, save_path)

    def load(self, load_path: Path) -> Song:
        stream = gm.parse(load_path)
        return stream


class Music21Serializer(Serializer):

    """Saves and loads a Music21 file. It's a concrete serializer."""

    def __init__(self, save_format: str = "midi") -> None:
        self.save_format = save_format

    def dump(self, m21_stream: Score, save_path: Path) -> None:
        m21_stream.write(fmt=self.save_format, fp=save_path)

    def load(self, load_path: Path) -> Score:
        stream = converter.parse(load_path)
        return stream