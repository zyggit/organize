"""Adapter between the desktop workflow and the organize v3 core."""

from pathlib import Path
from typing import Iterator, List, Optional

from organize.__version__ import __version__ as CORE_VERSION
from organize.filters.duplicate import Duplicate
from organize.filters.extension import Extension
from organize.filters.hash import Hash
from organize.filters.lastmodified import LastModified
from organize.filters.size import Size
from organize.resource import Resource
from organize.walker import Walker


class SilentOutput:
    """Output implementation for filters used by the non-interactive GUI engine."""

    def start(self, simulate, config_path, working_dir) -> None:
        pass

    def msg(self, res, msg, sender, level="info") -> None:
        pass

    def confirm(self, res, msg, default, sender) -> bool:
        return bool(default)

    def end(self, success_count, error_count) -> None:
        pass


OUTPUT = SilentOutput()


def walk_files(sources: List[Path], recursive: bool) -> Iterator[Resource]:
    """Yield v3 resources in deterministic breadth-first order."""

    walker = Walker(
        max_depth=None if recursive else 0,
        method="breadth",
        exclude_dirs={".git", ".svn"},
    )
    for source in sources:
        for path in walker.files(str(source)):
            yield Resource(path=path, basedir=source)


def matches_extension(resource: Resource, extensions) -> bool:
    return Extension(extensions=extensions).pipeline(resource, output=OUTPUT)


def extension_filter(extensions) -> Extension:
    return Extension(extensions=extensions)


def last_modified_filter(days: int = 0) -> LastModified:
    return LastModified(days=days, mode="older")


def size_filter(minimum_bytes: int) -> Size:
    return Size(conditions=[">=%db" % minimum_bytes])


def duplicate_filter() -> Duplicate:
    return Duplicate(detect_original_by="lastmodified", hash_algorithm="sha256")


def hash_filter() -> Hash:
    return Hash(algorithm="sha256")


def apply(filter_instance, resource: Resource) -> bool:
    return filter_instance.pipeline(resource, output=OUTPUT)


def resource_for(path: Path, basedir: Optional[Path] = None) -> Resource:
    return Resource(path=path, basedir=basedir)
