import json
import queue
import sys
import threading
import traceback
from typing import Any, Dict

from .errors import EngineError
from .service import EngineService


class RpcServer:
    def __init__(self) -> None:
        self.service = EngineService()
        self.requests: "queue.Queue[Dict[str, Any]]" = queue.Queue()
        self.write_lock = threading.Lock()
        self.plan_cancel = threading.Event()

    def write(self, payload: Dict[str, Any]) -> None:
        with self.write_lock:
            sys.stdout.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
            sys.stdout.flush()

    def event(self, name: str, payload: Dict[str, Any]) -> None:
        self.write({"event": name, "payload": payload})

    def read_loop(self) -> None:
        for line in sys.stdin:
            try:
                request = json.loads(line)
                method = request.get("method")
                if method == "run.cancel":
                    self.service.executor.cancel()
                    self.write({"id": request.get("id"), "result": {"accepted": True}})
                elif method == "plan.cancel":
                    self.plan_cancel.set()
                    self.write({"id": request.get("id"), "result": {"accepted": True}})
                else:
                    self.requests.put(request)
            except Exception as exc:
                self.write({"error": {"code": "INVALID_REQUEST", "message": str(exc)}})
        self.requests.put({"method": "__shutdown__"})

    def dispatch(self, method: str, params: Dict[str, Any]) -> Any:
        if method == "app.initialize":
            return self.service.initialize()
        if method == "app.version":
            return self.service.version()
        if method == "preset.list":
            return self.service.presets()
        if method == "profile.validate":
            return self.service.validate(params["profile"])
        if method == "plan.create":
            self.plan_cancel.clear()
            return self.service.create_plan(
                params["profile"],
                lambda data: self.event("plan.%s" % data.get("type", "progress"), data),
                self.plan_cancel.is_set,
            )
        if method == "plan.get":
            return self.service.get_plan(params["planId"])
        if method == "plan.excludeItems":
            return self.service.select_plan_items(params["planId"], params["selectedItemIds"])
        if method == "run.execute":
            return self.service.execute(
                params["planId"], lambda data: self.event("run.%s" % data.get("type", "progress"), data)
            )
        if method == "history.list":
            return self.service.history(int(params.get("limit", 50)))
        if method == "history.detail":
            return self.service.history_detail(params["runId"])
        if method == "history.undoPlan":
            return self.service.undo_preview(params["runId"])
        if method == "history.undo":
            return self.service.undo(
                params["runId"], params["operationIds"],
                lambda data: self.event(data.get("type", "undo.progress"), data),
            )
        if method == "quarantine.list":
            return self.service.quarantine()
        if method == "quarantine.restore":
            return self.service.restore_quarantine(
                params["quarantineIds"], params.get("destinationFolder")
            )
        if method == "quarantine.moveToTrash":
            return self.service.trash_quarantine(params["quarantineIds"])
        if method == "settings.get":
            return self.service.settings()
        if method == "settings.update":
            return self.service.update_settings(params["values"])
        if method == "diagnostics.export":
            return self.service.export_diagnostics(params["destination"])
        raise EngineError("METHOD_NOT_FOUND", "Unknown method: %s" % method)

    def worker_loop(self) -> None:
        while True:
            request = self.requests.get()
            if request.get("method") == "__shutdown__":
                return
            request_id = request.get("id")
            try:
                result = self.dispatch(request.get("method", ""), request.get("params") or {})
                self.write({"id": request_id, "result": result})
            except EngineError as exc:
                self.write({"id": request_id, "error": exc.as_dict()})
            except Exception as exc:
                traceback.print_exc(file=sys.stderr)
                self.write({"id": request_id, "error": {"code": "INTERNAL_ERROR", "message": str(exc)}})

    def run(self) -> None:
        reader = threading.Thread(target=self.read_loop, name="rpc-reader", daemon=True)
        reader.start()
        self.worker_loop()


if __name__ == "__main__":
    RpcServer().run()
