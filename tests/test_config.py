"""Tests for CLI config loading."""

import json

from awescholar.cli import load_config


def test_load_config_defaults_data_json_path_to_none():
    config = load_config(None)

    assert config["data_json_path"] is None


def test_load_config_reads_pipeline_data_json_path(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"pipeline": {"data_json_path": "data/data.json"}}),
        encoding="utf-8",
    )

    config = load_config(str(config_path))

    assert config["data_json_path"] == "data/data.json"
