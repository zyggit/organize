import os
import json
import platform
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from organize.__version__ import __version__ as organize_version

from . import __version__
from .executor import Executor
from .planner import Planner, validate_profile
from .presets import all_presets
from .store import Store
from .errors import EngineError


def default_data_dir() -> Path:
    override = os.environ.get("ORGANIZE_GUI_DATA_DIR")
    if override:
        return Path(override).expanduser().absolute()
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
    elif os.sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share")))
    return base / "organize-gui"


class EngineService:
    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self.data_dir = data_dir or default_data_dir()
        self.store = Store(self.data_dir / "journal.db")
        quarantine = self.data_dir / "quarantine"
        self.planner = Planner(self.store, quarantine)
        self.executor = Executor(self.store)

    def initialize(self) -> Dict[str, Any]:
        recovery = self.executor.recover_interrupted()
        return {
            "engineVersion": __version__,
            "firstLaunch": self.store.get_setting("onboardingCompleted", False) is False,
            "dataDir": str(self.data_dir),
            "recoverableRuns": sum(
                1 for run in self.store.list_history() if run["status"] in {"completed", "partial", "cancelled"}
            ),
            "quarantineCount": len(self.store.list_quarantine()),
            "recovery": recovery,
        }

    def version(self) -> Dict[str, str]:
        return {"engine": __version__, "organize": organize_version}

    def presets(self) -> List[Dict[str, Any]]:
        return all_presets()

    def validate(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        issues = validate_profile(profile)
        return {"valid": not issues, "issues": issues}

    def create_plan(
        self,
        profile: Dict[str, Any],
        events: Optional[Callable[[Dict[str, Any]], None]] = None,
        cancelled: Optional[Callable[[], bool]] = None,
    ) -> Dict[str, Any]:
        return self.planner.create(profile, events, cancelled)

    def get_plan(self, plan_id: str) -> Dict[str, Any]:
        return self.store.get_plan(plan_id)

    def select_plan_items(self, plan_id: str, selected_ids: List[str]) -> Dict[str, Any]:
        self.store.select_items(plan_id, selected_ids)
        return self.store.get_plan(plan_id)

    def execute(self, plan_id: str, events: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
        return self.executor.execute(plan_id, events)

    def history(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self.store.list_history(limit)

    def history_detail(self, run_id: str) -> Dict[str, Any]:
        return self.store.run_detail(run_id)

    def undo_preview(self, run_id: str) -> Dict[str, Any]:
        return self.executor.undo_preview(run_id)

    def undo(self, run_id: str, operation_ids: List[str], events: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
        return self.executor.undo(run_id, operation_ids, events)

    def quarantine(self) -> List[Dict[str, Any]]:
        return self.store.list_quarantine()

    def restore_quarantine(
        self, quarantine_ids: List[str], destination_folder: Optional[str] = None
    ) -> Dict[str, Any]:
        return self.executor.restore_quarantine(quarantine_ids, destination_folder)

    def trash_quarantine(self, quarantine_ids: List[str]) -> Dict[str, Any]:
        return self.executor.move_quarantine_to_trash(quarantine_ids)

    def settings(self) -> Dict[str, Any]:
        return {
            "theme": self.store.get_setting("theme", "system"),
            "retentionDays": self.store.get_setting("retentionDays", 30),
            "historyLimit": self.store.get_setting("historyLimit", 200),
            "redactPaths": self.store.get_setting("redactPaths", True),
            "notifyOnComplete": self.store.get_setting("notifyOnComplete", True),
        }

    def update_settings(self, values: Dict[str, Any]) -> Dict[str, Any]:
        for key, value in values.items():
            self.store.set_setting(key, value)
        return self.settings()

    def export_diagnostics(self, destination: str) -> Dict[str, Any]:
        output = Path(destination).expanduser().absolute()
        if output.exists():
            raise EngineError(
                "TARGET_CONFLICT", "The diagnostic archive already exists.",
                {"path": str(output)},
            )
        output.parent.mkdir(parents=True, exist_ok=True)
        failures = self.store.recent_failures()
        if self.store.get_setting("redactPaths", True):
            home = str(Path.home())
            for item in failures:
                detail = item.get("error_detail")
                if isinstance(detail, str):
                    item["error_detail"] = detail.replace(home, "~")
        manifest = {
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "app": self.version(),
            "system": {
                "platform": platform.platform(),
                "python": sys.version,
            },
            "settings": self.settings(),
            "database": self.store.database_health(),
            "recentFailures": failures,
        }
        try:
            with zipfile.ZipFile(str(output), "x", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(
                    "diagnostics.json",
                    json.dumps(manifest, ensure_ascii=False, indent=2),
                )
                logs = self.data_dir / "logs"
                if logs.is_dir():
                    for log in sorted(logs.glob("*.log")):
                        if log.is_file() and log.stat().st_size <= 5 * 1024 * 1024:
                            archive.write(str(log), "logs/%s" % log.name)
        except FileExistsError as exc:
            raise EngineError("TARGET_CONFLICT", "The diagnostic archive already exists.") from exc
        return {"path": str(output), "size": output.stat().st_size}
