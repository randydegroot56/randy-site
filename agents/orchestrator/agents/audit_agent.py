"""
orchestrator/agents/audit_agent.py
====================================
AuditAgent — adapter for the Code Auditor.

Current implementation: stub that proves the framework plumbing works.
Real implementation: invoke agents.code_auditor.cli subcommands via
subprocess or direct Python import.
"""
from __future__ import annotations

from typing import Any, Dict

from agents.orchestrator.base_agent import BaseAgent
from agents.orchestrator.events import AuditCompleted, AuditFailed


class AuditAgent(BaseAgent):
    name = "code_auditor"
    description = "Audits a target directory for unused code and quality issues"

    def run(self, target: str = ".", **kwargs: Any) -> Dict[str, Any]:
        try:
            # TODO: replace stub with real call:
            # from agents.code_auditor.cli import cmd_discover
            result: Dict[str, Any] = {
                "target": target,
                "issues_found": 0,
                "status": "stub",
            }
            self.emit(AuditCompleted(agent_name=self.name, payload=result))
            return result
        except Exception as exc:
            self.emit(AuditFailed(
                agent_name=self.name,
                error=str(exc),
                payload={"error": str(exc)},
            ))
            raise
