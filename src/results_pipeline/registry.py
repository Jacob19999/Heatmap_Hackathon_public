from __future__ import annotations

from dataclasses import dataclass

from .contracts.stage import StageMeta


@dataclass
class StageRegistry:
    stages: dict[str, StageMeta]
    deps: dict[str, list[str]]

    def get(self, stage_id: str) -> StageMeta:
        if stage_id not in self.stages:
            raise KeyError(f"Unknown stage: {stage_id}")
        return self.stages[stage_id]

    def ordered_stage_ids(self) -> list[str]:
        visited: set[str] = set()
        temp: set[str] = set()
        order: list[str] = []

        def visit(node: str) -> None:
            if node in visited:
                return
            if node in temp:
                raise ValueError(f"Cycle detected at stage '{node}'.")
            temp.add(node)
            for dep in self.deps.get(node, []):
                visit(dep)
            temp.remove(node)
            visited.add(node)
            order.append(node)

        for stage_id in self.stages.keys():
            visit(stage_id)
        return order


def create_default_registry() -> StageRegistry:
    stages = {
        "00": StageMeta("00", "data_audit", "Is NIRD standardized and trustworthy?", "Normalize and audit source data."),
        "01": StageMeta("01", "geography_enrichment", "Where are facilities and denominators anchored?", "Attach geography and denominators."),
        "02": StageMeta("02", "supply_capacity_baseline", "How is burn supply distributed per capita?", "Compute supply and structural baseline."),
        "03": StageMeta("03", "ground_access_burden", "How unequal is ground travel burden?", "Compute ground access burden summaries."),
        "04": StageMeta("04", "pediatric_access_gap", "Where is pediatric access most constrained?", "Compute pediatric gap metrics."),
        "05": StageMeta("05", "transfer_aware_access", "How does transfer-aware access change burden?", "Compute direct vs transfer-aware metrics."),
        "06": StageMeta("06", "structural_capacity", "Where is structural capacity competition highest?", "Compute structural capacity accessibility."),
        "07": StageMeta("07", "air_sensitivity", "How sensitive are results to conditional air transport?", "Compute air-sensitivity scenario outputs."),
        "08": StageMeta("08", "bei_hotspots", "Where are BEI hotspots and what drives them?", "Assemble BEI and hotspot tiers."),
        "09": StageMeta("09", "story_exports", "What should be exported for judging?", "Build findings, manifests, and final bundle."),
    }
    deps = {
        "01": ["00"],
        "02": ["01"],
        "03": ["02"],
        "04": ["03"],
        "05": ["04"],
        "06": ["02"],
        "07": ["02"],
        "08": ["05"],
        "09": ["08"],
    }
    return StageRegistry(stages=stages, deps=deps)
