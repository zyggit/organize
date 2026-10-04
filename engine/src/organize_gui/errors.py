from typing import Any, Dict, Optional


class EngineError(Exception):
    """An error that can be rendered by the UI without parsing its message."""

    def __init__(
        self,
        code: str,
        message: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.params = params or {}

    def as_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": str(self),
            "params": self.params,
        }


class PlanChanged(EngineError):
    def __init__(self, path: str) -> None:
        super().__init__(
            "PLAN_CHANGED",
            "The filesystem changed after the plan was created.",
            {"path": path},
        )


class Cancelled(EngineError):
    def __init__(self) -> None:
        super().__init__("CANCELLED", "The operation was cancelled.")

