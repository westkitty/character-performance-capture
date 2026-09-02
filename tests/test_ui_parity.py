from __future__ import annotations

from cpc.app import build_parser
from cpc.ui.parity import CLI_UI_PARITY_REGISTRY, EXCLUDED_CLI_DESTS, verify_cli_ui_parity


def test_cli_ui_capability_parity():
    """Assert that every user-facing CLI flag in build_parser() is mapped in the UI parity registry."""
    ok, missing = verify_cli_ui_parity()
    assert ok, f"CLI capabilities missing from UI parity registry: {missing}"


def test_parity_registry_entries_are_documented():
    """Verify that every registry item has a valid flag, dest, and UI component reference."""
    parser = build_parser()
    all_dests = {a.dest for a in parser._actions if a.dest not in EXCLUDED_CLI_DESTS}

    for dest, mapping in CLI_UI_PARITY_REGISTRY.items():
        assert dest in all_dests, f"Registry contains unknown CLI dest '{dest}'"
        assert mapping.cli_flag.startswith("--"), f"Invalid cli_flag '{mapping.cli_flag}'"
        assert mapping.ui_component, f"Missing ui_component mapping for '{dest}'"
        assert mapping.workspace, f"Missing workspace mapping for '{dest}'"
        assert mapping.description, f"Missing description for '{dest}'"
