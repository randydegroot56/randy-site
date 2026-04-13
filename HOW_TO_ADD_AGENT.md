# How to Add a New Agent

Adding an agent to the Command Center takes **4 steps**.
When you're done, `python main.py <your-command> <args>` will work.

---

## Step 1 — Create your agent file

Create `agents/orchestrator/agents/my_agent.py`:

```python
from __future__ import annotations
from typing import Any, Dict, Optional
from agents.orchestrator.base_agent import BaseAgent
from agents.orchestrator.events import AgentEvent
from dataclasses import dataclass


# Define your agent's events
@dataclass
class MyTaskCompleted(AgentEvent):
    event_type: str = "MyTaskCompleted"

@dataclass
class MyTaskFailed(AgentEvent):
    event_type: str = "MyTaskFailed"
    status: str = "failed"


class MyAgent(BaseAgent):
    name = "my_agent"                              # unique, snake_case
    description = "One sentence about what it does"

    def run(self, target: str = ".", **kwargs: Any) -> Dict[str, Any]:
        try:
            # Your logic here
            result = {"target": target, "status": "success"}
            self.emit(MyTaskCompleted(agent_name=self.name, payload=result))
            return result
        except Exception as exc:
            self.emit(MyTaskFailed(
                agent_name=self.name,
                error=str(exc),
                payload={"error": str(exc)},
            ))
            raise
```

Rules:
- `name` must be unique across all agents (the registry key)
- `run()` must return a `Dict[str, Any]`
- Call `self.emit(event)` to publish results — this writes to the bus AND state automatically
- Access previous agent outputs: `self._state.get("last_AuditCompleted")`
- Emit failure events before re-raising exceptions

---

## Step 2 — Register the agent in main.py

Open `main.py`, add one import and one `registry.register()` call in `build_registry()`:

```python
from agents.orchestrator.agents.my_agent import MyAgent   # add import

def build_registry() -> AgentRegistry:
    registry = AgentRegistry()
    registry.register(AuditAgent)
    registry.register(FixerAgent)
    registry.register(MyAgent)    # <-- add this
    return registry
```

---

## Step 3 — Add a CLI command in orchestrator.py

Open `agents/orchestrator/orchestrator.py`. Add your command to `INTENT_MAP`:

```python
INTENT_MAP: Dict[str, Tuple[str, Optional[str]]] = {
    "audit":    ("code_auditor", "target"),
    "fix":      ("code_fixer",   "target"),
    "my-task":  ("my_agent",     "target"),   # <-- add this
}
```

Now `python main.py my-task ./src` works.

---

## Step 4 — Write tests

Create `agents/orchestrator/tests/test_my_agent.py`:

```python
from agents.orchestrator.agents.my_agent import MyAgent
from agents.orchestrator.bus import EventBus
from agents.orchestrator.state import StateStore


def make_deps(tmp_path):
    return EventBus(), StateStore(tmp_path / "state.json")


def test_my_agent_name():
    assert MyAgent.name == "my_agent"


def test_my_agent_run_returns_dict(tmp_path):
    bus, state = make_deps(tmp_path)
    agent = MyAgent(bus=bus, state=state)
    result = agent.run(target="./src")
    assert result["target"] == "./src"


def test_my_agent_emits_completed_event(tmp_path):
    bus, state = make_deps(tmp_path)
    received = []
    bus.subscribe("MyTaskCompleted", received.append)

    agent = MyAgent(bus=bus, state=state)
    agent.run(target="./src")

    assert len(received) == 1
    assert received[0].agent_name == "my_agent"
```

Run: `python -m pytest agents/orchestrator/tests/test_my_agent.py -v`

---

## Verify end-to-end

```bash
python main.py list              # my_agent should appear
python main.py my-task ./src     # runs your agent, logs event
```

The logger automatically captures all your events. The state store saves `last_MyTaskCompleted` so other agents can access it with `self._state.get("last_MyTaskCompleted")`.

---

## Architecture Quick Reference

```
agents/
├── code_auditor/         ← 5-phase static analysis agent
├── code_fixer/           ← applies audit findings to codebase
└── orchestrator/
    ├── base_agent.py     ← Inherit from BaseAgent
    ├── events.py         ← Define AgentEvent subclasses here
    ├── bus.py            ← EventBus (subscribe/publish)
    ├── state.py          ← StateStore (JSON persistence)
    ├── registry.py       ← AgentRegistry (register/get/list)
    ├── logger.py         ← OrchestratorLogger (subscribes to *)
    ├── orchestrator.py   ← INTENT_MAP + dispatch logic
    └── agents/
        ├── audit_agent.py
        ├── fixer_agent.py
        └── my_agent.py   ← Your new agent goes here
```

**Data flow for a single command:**

```
User: python main.py my-task ./src
  → main.py builds bus, state, logger, registry, orchestrator
  → Orchestrator.run("my-task", ["./src"])
  → INTENT_MAP → "my_agent"
  → MyAgent.run(target="./src")
  → result computed
  → self.emit(MyTaskCompleted(...))
    → EventBus.publish(event)  → Logger prints to terminal
    → StateStore.set("last_MyTaskCompleted", payload)
  → return result
  → Orchestrator.print_summary()
```
