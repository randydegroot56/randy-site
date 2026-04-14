#!/usr/bin/env python3
"""
main.py — AI Command Center entry point.

Usage::
    python main.py list                  # Show all registered agents
    python main.py audit ./src           # Run Code Auditor on ./src
    python main.py audit ./src -v        # Verbose: show event payloads
    python main.py fix ./src             # Run Code Fixer on ./src
    python main.py fix                   # Fix using last audit result from state
"""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

# Ensure repo root is importable when run as `python main.py`
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))

# Force UTF-8 output on Windows (cp1252 default can't encode ✓/✗)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from agents.orchestrator.agents.audit_agent import AuditAgent
from agents.orchestrator.agents.fixer_agent import FixerAgent
from agents.memory.agent import MemoryAgent
from agents.orchestrator.bus import EventBus
from agents.orchestrator.logger import OrchestratorLogger
from agents.orchestrator.orchestrator import Orchestrator
from agents.orchestrator.registry import AgentRegistry
from agents.orchestrator.state import StateStore


def build_registry() -> AgentRegistry:
    """Register all known agents. Add new agents here."""
    registry = AgentRegistry()
    registry.register(AuditAgent)
    registry.register(FixerAgent)
    registry.register(MemoryAgent)
    return registry


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="AI Command Center — orchestrate your agents",
    )
    parser.add_argument("command", help="Command to run: audit | fix | list")
    parser.add_argument("args", nargs="*", help="Arguments (e.g. ./src)")
    parser.add_argument(
        "--log-file",
        default=".orchestrator_log.json",
        help="Path for JSON event log (default: .orchestrator_log.json)",
    )
    parser.add_argument(
        "--state-file",
        default=".orchestrator_state.json",
        help="Path for state file (default: .orchestrator_state.json)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Print event payloads")
    parsed = parser.parse_args()

    bus = EventBus()
    state = StateStore(Path(parsed.state_file))
    logger = OrchestratorLogger(
        bus,
        log_file=Path(parsed.log_file),
        verbose=parsed.verbose,
    )
    registry = build_registry()
    orch = Orchestrator(registry, bus, state, logger)

    if parsed.command == "list":
        print("Registered agents:")
        for name, desc in registry.list_agents().items():
            print(f"  {name}: {desc}")
        return 0

    try:
        orch.run(parsed.command, parsed.args)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        orch.print_summary()

    return 0


if __name__ == "__main__":
    sys.exit(main())
