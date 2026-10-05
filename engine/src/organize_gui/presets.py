from typing import Any, Dict, List


CATEGORIES = {
    "documents": {
        "label": "文档",
        "extensions": [
            "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "md", "csv"
        ],
    },
    "images": {
        "label": "图片",
        "extensions": ["jpg", "jpeg", "png", "gif", "webp", "heic", "tif", "tiff"],
    },
    "videos": {
        "label": "视频",
        "extensions": ["mp4", "mov", "mkv", "avi", "webm", "m4v"],
    },
    "audio": {
        "label": "音频",
        "extensions": ["mp3", "m4a", "wav", "flac", "aac", "ogg"],
    },
    "archives": {
        "label": "压缩包",
        "extensions": ["zip", "7z", "rar", "tar", "gz", "bz2", "xz"],
    },
    "installers": {
        "label": "安装包",
        "extensions": ["exe", "msi", "msix", "dmg", "pkg"],
    },
    "other": {"label": "其他文件", "extensions": []},
}

IMAGE_EXTENSIONS = set(CATEGORIES["images"]["extensions"])
INSTALLER_EXTENSIONS = {"exe", "msi", "msix", "dmg", "pkg"}


def all_presets() -> List[Dict[str, Any]]:
    return [
        {
            "id": "by-type",
            "name": "文件按类型整理",
            "description": "文档、图片、视频等各归一处。",
            "operation": "move",
        },
        {
            "id": "by-date",
            "name": "图片按日期归档",
            "description": "按年和月整理照片与截图。",
            "operation": "move",
        },
        {
            "id": "old-installers",
            "name": "旧安装包清理",
            "description": "腾出被旧安装包占用的空间。",
            "operation": "quarantine",
        },
        {
            "id": "duplicates",
            "name": "重复文件查找",
            "description": "内容逐字节相同才算重复。",
            "operation": "quarantine",
        },
        {
            "id": "similar-photos",
            "name": "相似照片",
            "description": "找出完全相同和看起来相似的照片，包括旋转或翻转的副本。",
            "operation": "quarantine",
        },
    ]


def category_for_extension(extension: str, enabled: List[str]) -> str:
    normalized = extension.casefold().lstrip(".")
    for key in enabled:
        category = CATEGORIES.get(key)
        if category and normalized in category["extensions"]:
            return key
    return "other" if "other" in enabled else ""
