import errno
import hashlib
import os
import shutil
import stat
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Set, Tuple

from .errors import EngineError


TEMP_SUFFIXES = (".crdownload", ".part", ".download")
SYSTEM_NAMES = {".ds_store", ".localized", "desktop.ini", "thumbs.db"}


def absolute_path(value: str) -> Path:
    """Resolve a literal user path without expanding environment variables."""
    return Path(value).expanduser().absolute()


def path_key(path: Path) -> str:
    return os.path.normcase(str(path.resolve(strict=False)))


def is_within(path: Path, parent: Path) -> bool:
    try:
        Path(path_key(path)).relative_to(Path(path_key(parent)))
        return True
    except ValueError:
        return False


def should_skip_name(name: str) -> Optional[str]:
    lowered = name.casefold()
    if lowered in SYSTEM_NAMES or lowered.startswith("~$"):
        return "SYSTEM_FILE"
    if lowered.endswith(TEMP_SUFFIXES):
        return "INCOMPLETE_DOWNLOAD"
    return None


def fingerprint(path: Path) -> Dict[str, int]:
    info = path.stat()
    return {
        "size": int(info.st_size),
        "mtimeNs": int(info.st_mtime_ns),
        "device": int(info.st_dev),
        "inode": int(info.st_ino),
    }


def same_fingerprint(path: Path, expected: Dict[str, Any]) -> bool:
    try:
        current = fingerprint(path)
    except OSError:
        return False
    return all(current.get(key) == expected.get(key) for key in current)


def hash_file(path: Path, first_bytes: Optional[int] = None) -> str:
    digest = hashlib.sha256()
    remaining = first_bytes
    with path.open("rb") as handle:
        while True:
            size = 1024 * 1024
            if remaining is not None:
                if remaining <= 0:
                    break
                size = min(size, remaining)
            block = handle.read(size)
            if not block:
                break
            digest.update(block)
            if remaining is not None:
                remaining -= len(block)
    return digest.hexdigest()


def unique_destination(destination: Path, occupied: Set[str]) -> Tuple[Path, bool]:
    candidate = destination
    counter = 2
    renamed = False
    while candidate.exists() or path_key(candidate) in occupied:
        candidate = destination.with_name(
            "%s %d%s" % (destination.stem, counter, destination.suffix)
        )
        counter += 1
        renamed = True
    occupied.add(path_key(candidate))
    return candidate, renamed


def ensure_parent(path: Path) -> Iterable[Path]:
    missing = []
    current = path.parent
    while not current.exists():
        missing.append(current)
        if current.parent == current:
            break
        current = current.parent
    path.parent.mkdir(parents=True, exist_ok=True)
    return reversed(missing)


def _copy_to_handle(source: Path, handle: Any) -> None:
    with source.open("rb") as src:
        shutil.copyfileobj(src, handle, length=1024 * 1024)
    handle.flush()
    os.fsync(handle.fileno())


def safe_copy(source: Path, destination: Path, operation_id: str) -> None:
    """Copy without overwriting an existing destination.

    Data is first written to a deterministic partial path, then installed using a
    hard link where possible.  The fallback still uses O_EXCL, so it never replaces
    a file created after preview.
    """
    ensure_parent(destination)
    if destination.exists():
        raise EngineError(
            "TARGET_CONFLICT",
            "The target already exists.",
            {"path": str(destination)},
        )
    partial = destination.with_name(
        ".%s.organize-%s.partial" % (destination.name, operation_id)
    )
    if partial.exists():
        partial.unlink()
    try:
        with partial.open("xb") as handle:
            _copy_to_handle(source, handle)
        shutil.copystat(str(source), str(partial), follow_symlinks=False)
        try:
            os.link(str(partial), str(destination))
        except OSError:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            descriptor = os.open(str(destination), flags, stat.S_IMODE(source.stat().st_mode))
            try:
                with os.fdopen(descriptor, "wb") as handle:
                    _copy_to_handle(partial, handle)
                shutil.copystat(str(source), str(destination), follow_symlinks=False)
            except BaseException:
                try:
                    destination.unlink()
                except OSError:
                    pass
                raise
        partial.unlink()
    except FileExistsError as exc:
        raise EngineError(
            "TARGET_CONFLICT",
            "The target already exists.",
            {"path": str(destination)},
        ) from exc
    finally:
        if partial.exists():
            try:
                partial.unlink()
            except OSError:
                pass


def safe_move(source: Path, destination: Path, operation_id: Optional[str] = None) -> None:
    if destination.exists():
        raise EngineError(
            "TARGET_CONFLICT",
            "The target already exists.",
            {"path": str(destination)},
        )
    ensure_parent(destination)
    operation_id = operation_id or uuid.uuid4().hex
    try:
        os.link(str(source), str(destination))
    except FileExistsError as exc:
        raise EngineError(
            "TARGET_CONFLICT",
            "The target already exists.",
            {"path": str(destination)},
        ) from exc
    except OSError as exc:
        if exc.errno not in (
            errno.EXDEV,
            errno.EPERM,
            errno.EACCES,
            errno.ENOTSUP,
            getattr(errno, "EOPNOTSUPP", errno.ENOTSUP),
        ):
            raise
    else:
        try:
            source.unlink()
        except BaseException as exc:
            # The hard link is already a complete second name for the file. Keep
            # both names for recovery; never remove a destination we created after
            # the source deletion failed.
            raise EngineError(
                "SOURCE_REMOVE_FAILED",
                "The file was linked but the source could not be removed.",
                {"source": str(source), "target": str(destination)},
            ) from exc
        return
    safe_copy(source, destination, operation_id)
    try:
        source.unlink()
    except BaseException:
        # The copy is complete but the move is not.  Keeping both is safer than
        # deleting either; recovery can reconcile the journal on next startup.
        raise EngineError(
            "SOURCE_REMOVE_FAILED",
            "The file was copied but the source could not be removed.",
            {"source": str(source), "target": str(destination)},
        )
