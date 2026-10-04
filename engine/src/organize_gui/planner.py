import os
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple

from .errors import Cancelled, EngineError
from .paths import (
    absolute_path,
    fingerprint,
    hash_file,
    is_within,
    path_key,
    should_skip_name,
    unique_destination,
)
from .presets import (
    CATEGORIES,
    IMAGE_EXTENSIONS,
    INSTALLER_EXTENSIONS,
    category_for_extension,
)
from .store import Store


Progress = Optional[Callable[[Dict[str, Any]], None]]
CancelledCheck = Optional[Callable[[], bool]]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime) -> str:
    return value.isoformat()


def validate_profile(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    sources = [absolute_path(item) for item in profile.get("sourceFolders", [])]
    if not sources:
        issues.append({"code": "SOURCE_NOT_FOUND", "field": "sourceFolders"})
    for source in sources:
        if not source.exists() or not source.is_dir():
            issues.append({"code": "SOURCE_NOT_FOUND", "path": str(source)})
        elif not os.access(str(source), os.R_OK | os.X_OK):
            issues.append({"code": "SOURCE_NOT_READABLE", "path": str(source)})

    preset = profile.get("presetType")
    if preset not in {"by-type", "by-date", "old-installers", "duplicates"}:
        issues.append({"code": "INVALID_PRESET", "field": "presetType"})

    target_value = profile.get("targetFolder")
    if preset not in {"old-installers", "duplicates"}:
        if not target_value:
            issues.append({"code": "TARGET_NOT_WRITABLE", "field": "targetFolder"})
        else:
            target = absolute_path(target_value)
            nearest = target
            while not nearest.exists() and nearest.parent != nearest:
                nearest = nearest.parent
            if not nearest.exists() or not os.access(str(nearest), os.W_OK | os.X_OK):
                issues.append({"code": "TARGET_NOT_WRITABLE", "path": str(target)})
            for source in sources:
                if path_key(source) == path_key(target) or is_within(target, source):
                    issues.append(
                        {
                            "code": "SOURCE_TARGET_OVERLAP",
                            "path": str(target),
                            "source": str(source),
                        }
                    )
    if preset == "by-type" and not profile.get("parameters", {}).get("categories"):
        issues.append({"code": "NO_CATEGORIES", "field": "parameters.categories"})
    return issues


def scan_files(
    sources: List[Path],
    recursive: bool,
    progress: Progress = None,
    cancelled: CancelledCheck = None,
) -> Iterator[Tuple[Path, Path, Optional[str]]]:
    count = 0
    stack: List[Tuple[Path, Path]] = [(source, source) for source in reversed(sources)]
    while stack:
        root, folder = stack.pop()
        if cancelled and cancelled():
            raise Cancelled()
        try:
            with os.scandir(str(folder)) as entries:
                children = sorted(list(entries), key=lambda entry: entry.name.casefold())
        except OSError as exc:
            if progress:
                progress({"type": "warning", "code": "SOURCE_NOT_READABLE", "path": str(folder), "detail": str(exc)})
            continue
        for entry in children:
            if cancelled and cancelled():
                raise Cancelled()
            try:
                if entry.is_symlink():
                    continue
                if entry.is_dir(follow_symlinks=False):
                    if recursive and entry.name.casefold() not in {".git", ".svn"}:
                        stack.append((root, Path(entry.path)))
                    continue
                if not entry.is_file(follow_symlinks=False):
                    continue
            except OSError:
                continue
            path = Path(entry.path)
            count += 1
            reason = should_skip_name(path.name)
            if progress and (count == 1 or count % 100 == 0):
                progress({"type": "progress", "checked": count, "path": str(path)})
            yield root, path, reason


class Planner:
    def __init__(self, store: Store, quarantine_root: Path) -> None:
        self.store = store
        self.quarantine_root = quarantine_root

    def create(
        self,
        profile: Dict[str, Any],
        progress: Progress = None,
        cancelled: CancelledCheck = None,
    ) -> Dict[str, Any]:
        issues = validate_profile(profile)
        if issues:
            raise EngineError("PROFILE_INVALID", "The profile is invalid.", {"issues": issues})
        now = utc_now()
        plan_id = uuid.uuid4().hex
        preset = profile["presetType"]
        if preset == "duplicates":
            items = self._duplicates(plan_id, profile, progress, cancelled)
        else:
            items = self._regular(plan_id, profile, progress, cancelled)
        summary = self._summary(items)
        self.store.save_profile(profile, iso(now))
        self.store.save_plan(
            plan_id,
            profile,
            iso(now),
            iso(now + timedelta(minutes=30)),
            summary,
            items,
        )
        result = self.store.get_plan(plan_id)
        if progress:
            progress({"type": "completed", "planId": plan_id, "summary": summary})
        return result

    def _regular(
        self,
        plan_id: str,
        profile: Dict[str, Any],
        progress: Progress,
        cancelled: CancelledCheck,
    ) -> List[Dict[str, Any]]:
        sources = [absolute_path(item) for item in profile["sourceFolders"]]
        target = absolute_path(profile.get("targetFolder", str(self.quarantine_root)))
        recursive = bool(profile.get("includeSubfolders", False))
        occupied: Set[str] = set()
        items: List[Dict[str, Any]] = []
        params = profile.get("parameters", {})
        age_days = int(params.get("olderThanDays", 90))
        cutoff = utc_now().timestamp() - age_days * 86400
        enabled_categories = params.get("categories", list(CATEGORIES.keys()))

        for root, source, skip_reason in scan_files(sources, recursive, progress, cancelled):
            item: Optional[Dict[str, Any]] = None
            if skip_reason:
                item = self._item(plan_id, len(items), source, None, "skip", False, skip_reason)
            elif profile["presetType"] == "by-type":
                category = category_for_extension(source.suffix, enabled_categories)
                if category:
                    destination = target / CATEGORIES[category]["label"] / source.name
                    destination, renamed = unique_destination(destination, occupied)
                    item = self._item(plan_id, len(items), source, destination, "move", True)
                    item["metadata"]["category"] = category
                    if renamed:
                        item["warningCode"] = "TARGET_CONFLICT"
            elif profile["presetType"] == "by-date":
                extension = source.suffix.casefold().lstrip(".")
                if extension in IMAGE_EXTENSIONS:
                    modified = datetime.fromtimestamp(source.stat().st_mtime)
                    destination = target / ("%d年" % modified.year) / ("%02d月" % modified.month) / source.name
                    destination, renamed = unique_destination(destination, occupied)
                    item = self._item(plan_id, len(items), source, destination, "move", True)
                    if renamed:
                        item["warningCode"] = "TARGET_CONFLICT"
            elif profile["presetType"] == "old-installers":
                extension = source.suffix.casefold().lstrip(".")
                include_archives = bool(params.get("includeArchives", False))
                allowed = INSTALLER_EXTENSIONS | ({"zip"} if include_archives else set())
                if extension in allowed and source.stat().st_mtime < cutoff:
                    destination = self._quarantine_destination(plan_id, root, source)
                    item = self._item(plan_id, len(items), source, destination, "quarantine", True)
                    item["reason"] = "旧安装包，%d 天未修改" % age_days
            if item is not None:
                items.append(item)
        return items

    def _duplicates(
        self,
        plan_id: str,
        profile: Dict[str, Any],
        progress: Progress,
        cancelled: CancelledCheck,
    ) -> List[Dict[str, Any]]:
        sources = [absolute_path(item) for item in profile["sourceFolders"]]
        recursive = bool(profile.get("includeSubfolders", True))
        minimum = int(profile.get("parameters", {}).get("minimumBytes", 1024 * 1024))
        by_size: Dict[int, List[Tuple[Path, Path]]] = defaultdict(list)
        for root, path, reason in scan_files(sources, recursive, progress, cancelled):
            if not reason:
                size = path.stat().st_size
                if size >= minimum:
                    by_size[size].append((root, path))
        by_chunk: Dict[Tuple[int, str], List[Tuple[Path, Path]]] = defaultdict(list)
        for size, paths in by_size.items():
            if len(paths) < 2:
                continue
            for root, path in paths:
                if cancelled and cancelled():
                    raise Cancelled()
                by_chunk[(size, hash_file(path, 64 * 1024))].append((root, path))
        by_hash: Dict[str, List[Tuple[Path, Path]]] = defaultdict(list)
        hashed = 0
        for paths in by_chunk.values():
            if len(paths) < 2:
                continue
            for root, path in paths:
                if cancelled and cancelled():
                    raise Cancelled()
                by_hash[hash_file(path)].append((root, path))
                hashed += 1
                if progress:
                    progress({"type": "progress", "stage": "full", "hashed": hashed, "path": str(path)})
        items: List[Dict[str, Any]] = []
        group_index = 0
        for digest, paths in sorted(by_hash.items()):
            if len(paths) < 2:
                continue
            group_index += 1
            group_id = "%s-g%d" % (plan_id, group_index)
            recommended = min(paths, key=lambda pair: (pair[1].stat().st_mtime_ns, str(pair[1])))
            for root, source in paths:
                destination = self._quarantine_destination(plan_id, root, source)
                item = self._item(plan_id, len(items), source, destination, "quarantine", False)
                item["groupId"] = group_id
                item["metadata"].update(
                    {
                        "digest": digest,
                        "recommendedKeep": source == recommended[1],
                        "decision": "undecided",
                    }
                )
                item["reason"] = "重复文件"
                items.append(item)
        return items

    def _quarantine_destination(self, plan_id: str, root: Path, source: Path) -> Path:
        try:
            relative = source.relative_to(root)
        except ValueError:
            relative = Path(source.name)
        destination = self.quarantine_root / plan_id / uuid.uuid4().hex[:8] / relative
        if not is_within(destination, self.quarantine_root):
            raise EngineError("INVALID_PATH", "Quarantine path escaped its root.")
        return destination

    @staticmethod
    def _item(
        plan_id: str,
        sequence: int,
        source: Path,
        target: Optional[Path],
        operation: str,
        selected: bool,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "itemId": uuid.uuid4().hex,
            "planId": plan_id,
            "sequence": sequence,
            "operation": operation,
            "sourcePath": str(source),
            "targetPath": str(target) if target else None,
            "size": source.stat().st_size,
            "fingerprint": fingerprint(source),
            "selected": selected,
            "status": "planned" if operation != "skip" else "skipped",
            "warningCode": None,
            "reason": reason,
            "metadata": {},
        }

    @staticmethod
    def _summary(items: List[Dict[str, Any]]) -> Dict[str, Any]:
        selected = [item for item in items if item.get("selected")]
        return {
            "total": len(items),
            "selected": len(selected),
            "selectedBytes": sum(item["size"] for item in selected),
            "move": sum(item["operation"] == "move" for item in selected),
            "quarantine": sum(item["operation"] == "quarantine" for item in selected),
            "skip": sum(item["status"] == "skipped" for item in items),
            "conflict": sum(bool(item.get("warningCode")) for item in items),
            "groups": len({item.get("groupId") for item in items if item.get("groupId")}),
        }

