from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ArtifactRecord:
    artifact_id: str
    stage_id: str
    artifact_type: str
    path: str
    format: str
    artifact_role: str = ""
    scenario_id: str | None = None


@dataclass
class ArtifactManifest:
    run_id: str
    profile: str
    created_at: str = field(default_factory=utc_now_iso)
    artifacts: list[ArtifactRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "profile": self.profile,
            "created_at": self.created_at,
            "artifacts": [asdict(a) for a in self.artifacts],
        }


@dataclass
class FindingRecord:
    stage_id: str
    question: str
    finding: str
    why_it_matters: str
    action_implication: str
    scenario_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
