"""AgentField routers and schemas for linkedin-outreach-agent."""

from __future__ import annotations

from typing import Any

__all__ = ["committee_router", "specialists_router"]


def __getattr__(name: str) -> Any:
    if name == "committee_router":
        from .committee import router as committee_router

        return committee_router
    if name == "specialists_router":
        from .specialists import router as specialists_router

        return specialists_router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
