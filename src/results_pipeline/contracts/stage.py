from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from ..settings import RuntimeConfig


@dataclass(frozen=True)
class StageMeta:
    stage_id: str
    name: str
    question: str
    description: str
    replaces_notebooks: list[str] = field(default_factory=list)
    required_inputs: list[str] = field(default_factory=list)
    produced_datasets: list[str] = field(default_factory=list)
    produced_tables: list[str] = field(default_factory=list)
    produced_figures: list[str] = field(default_factory=list)
    produced_findings: list[str] = field(default_factory=list)
    validations: list[str] = field(default_factory=list)


class StageProtocol(Protocol):
    meta: StageMeta

    def run(self, config: RuntimeConfig) -> dict[str, object]:
        ...
