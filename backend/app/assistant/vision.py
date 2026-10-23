"""Contract for a future local visual analyzer; no synthetic visual answers."""
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class SampledFrame:
    path: Path
    source_frame_index: int
    timecode: str


@dataclass(frozen=True)
class VisualRequest:
    frames: tuple[SampledFrame, ...]
    instructions: str
    transcript: str = ""


@dataclass(frozen=True)
class VisualProposal:
    description: str
    source_frame_indices: tuple[int, ...]
    uncertainty: str
    # A proposal requires explicit user review before becoming an annotation.
    verification: str = "Da verificare"


class LocalVisualAnalyzer(Protocol):
    def available(self) -> bool: ...
    def analyze(self, request: VisualRequest) -> list[VisualProposal]: ...
