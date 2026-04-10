from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PathLayout:
    root: Path
    data_raw: Path
    data_interim: Path
    data_processed: Path
    outputs_figures: Path
    outputs_tables: Path
    outputs_metrics: Path
    outputs_final_bundle: Path


def build_layout(root: Path) -> PathLayout:
    root = root.resolve()
    return PathLayout(
        root=root,
        data_raw=root / "data" / "raw",
        data_interim=root / "data" / "interim",
        data_processed=root / "data" / "processed",
        outputs_figures=root / "outputs" / "figures",
        outputs_tables=root / "outputs" / "tables",
        outputs_metrics=root / "outputs" / "metrics",
        outputs_final_bundle=root / "outputs" / "final_bundle",
    )


def ensure_layout(layout: PathLayout) -> None:
    for p in [
        layout.data_raw,
        layout.data_interim,
        layout.data_processed,
        layout.outputs_figures,
        layout.outputs_tables,
        layout.outputs_metrics,
        layout.outputs_final_bundle,
    ]:
        p.mkdir(parents=True, exist_ok=True)
