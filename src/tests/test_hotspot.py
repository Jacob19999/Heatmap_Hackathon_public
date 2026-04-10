"""Tests for pipeline.hotspot (import and public API)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import hotspot
from pipeline import config


def test_hotspot_module_imports():
    """hotspot module imports and exposes config."""
    assert hasattr(hotspot, "config")
    assert hotspot.config is config


def test_hotspot_all_exports_config():
    """__all__ includes 'config'."""
    assert "config" in hotspot.__all__


def test_hotspot_config_has_repo_root():
    """Re-exported config has REPO_ROOT (sanity check)."""
    assert hasattr(hotspot.config, "REPO_ROOT")
    assert hotspot.config.REPO_ROOT.is_dir()


def test_hotspot_exports_compute_functions():
    """Hotspot module exports compute_hotspot_stats, compute_clusters_and_archetypes, compute_hotspot_layer."""
    assert hasattr(hotspot, "compute_hotspot_stats")
    assert hasattr(hotspot, "compute_clusters_and_archetypes")
    assert hasattr(hotspot, "compute_hotspot_layer")
    assert "compute_hotspot_stats" in hotspot.__all__
