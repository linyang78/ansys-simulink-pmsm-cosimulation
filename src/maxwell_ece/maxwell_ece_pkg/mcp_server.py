"""Thin local MCP server exposing the same core workflow functions.

The server is optional: offline CLI use has no MCP dependency.  No shared AEDT
MCP session is used; live jobs still follow the isolated PyAEDT process path.
"""

from __future__ import annotations

from typing import Any

from .core import (
    batch_run,
    draft_config,
    inspect_project,
    prepare_project,
    run_project,
    validate_config,
)


def create_server():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:  # pragma: no cover - optional local dependency
        raise RuntimeError("install/use the pmsm environment with mcp to serve MCP") from exc
    server = FastMCP("maxwell-ece")

    @server.tool()
    def inspect(project: str) -> dict[str, Any]:
        return inspect_project(project)

    @server.tool()
    def draft(inspection: dict[str, Any], design: str | None = None, setup: str | None = None, output_dir: str | None = None) -> dict[str, Any]:
        return draft_config(inspection, design=design, setup=setup, output_dir=output_dir)

    @server.tool()
    def validate(config: dict[str, Any], inspection: dict[str, Any] | None = None) -> dict[str, Any]:
        return validate_config(config, inspection)

    @server.tool()
    def prepare(config: dict[str, Any], destination: str | None = None) -> dict[str, Any]:
        return prepare_project(config, destination=destination)

    @server.tool()
    def run(config: dict[str, Any], live: bool = True) -> dict[str, Any]:
        return run_project(config, live=live)

    @server.tool()
    def batch(configs: list[dict[str, Any]], max_parallel: int = 1, total_cores: int | None = None, live: bool = True) -> list[dict[str, Any]]:
        return batch_run(configs, max_parallel=max_parallel, total_cores=total_cores, live=live)

    return server


def serve() -> None:
    create_server().run(transport="stdio")
