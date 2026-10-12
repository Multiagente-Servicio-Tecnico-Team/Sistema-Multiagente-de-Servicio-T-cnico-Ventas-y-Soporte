"""Trazas locales por lista permitida: nunca serializar entradas o errores."""
import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4

from langchain_core.callbacks import BaseCallbackHandler
from langsmith import tracing_context


class JsonTrace(BaseCallbackHandler):
    raise_error = True
    _lock = Lock()
    names = {"sales_graph", "sales_agent", "lookup_catalog", "support_graph",
             "support_agent", "router", "failure_probe"}

    def __init__(self, path: Path, execution_id: str):
        self.path = Path(path)
        self.execution_id = execution_id
        self.calls = {}

    def record(self, event, run_id, parent_run_id=None, name=None, kind="chain"):
        key = str(run_id)
        if event == "start":
            self.calls[key] = (name if name in self.names else "internal", kind)
        safe_name, safe_kind = self.calls.get(key, ("internal", kind))
        record = {"timestamp": datetime.now(timezone.utc).isoformat(),
                  "execution_id": self.execution_id, "run_id": key,
                  "parent_run_id": str(parent_run_id) if parent_run_id else None,
                  "name": safe_name, "kind": safe_kind, "event": event}
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record) + "\n")

    def on_chain_start(self, serialized, inputs, *, run_id, parent_run_id=None, **kwargs):
        self.record("start", run_id, parent_run_id, kwargs.get("name"))

    def on_chain_end(self, outputs, *, run_id, parent_run_id=None, **kwargs):
        self.record("success", run_id, parent_run_id)

    def on_chain_error(self, error, *, run_id, parent_run_id=None, **kwargs):
        self.record("error", run_id, parent_run_id)

    def on_tool_start(self, serialized, input_str, *, run_id, parent_run_id=None, **kwargs):
        self.record("start", run_id, parent_run_id, (serialized or {}).get("name"), "tool")

    def on_tool_end(self, output, *, run_id, parent_run_id=None, **kwargs):
        self.record("success", run_id, parent_run_id, kind="tool")

    def on_tool_error(self, error, *, run_id, parent_run_id=None, **kwargs):
        self.record("error", run_id, parent_run_id, kind="tool")


def invoke_traced(graph, state, path=Path(".local/traces.jsonl")):
    execution_id = str(uuid4())
    handler = JsonTrace(path, execution_id)
    # Evita que variables LANGSMITH/LANGCHAIN habiliten exportación de payloads.
    with tracing_context(enabled=False):
        result = graph.invoke(state, config={"callbacks": [handler]})
    return result, execution_id
