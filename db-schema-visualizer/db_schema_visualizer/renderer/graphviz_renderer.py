"""
Graphviz renderer – produces PNG, SVG, or PDF static diagrams.

Uses the ``graphviz`` Python package to avoid requiring a separately
installed Graphviz binary on most platforms (the wheel bundles the
binaries).  A helpful error is raised when the binary is missing.
"""

from __future__ import annotations

import logging
import os
from typing import Literal

import graphviz

from db_schema_visualizer.graph.builder import GraphDict
from db_schema_visualizer.graph.layout import graph_to_dot
from db_schema_visualizer.renderer.base import AbstractRenderer

logger = logging.getLogger(__name__)

OutputFormat = Literal["png", "svg", "pdf"]


class GraphvizRenderer(AbstractRenderer):
    """Renders an ERD as a static image file using Graphviz.

    Supported output formats: ``png``, ``svg``, ``pdf``.

    Example::

        renderer = GraphvizRenderer(fmt="svg")
        path = renderer.render(graph, "output/diagram")
        # → writes output/diagram.svg
    """

    def __init__(
        self,
        fmt: OutputFormat = "png",
        direction: str = "LR",
        engine: str = "dot",
    ) -> None:
        """Initialise the renderer.

        Args:
            fmt: Output file format – ``"png"``, ``"svg"``, or ``"pdf"``.
            direction: Graph rank direction: ``"LR"`` or ``"TB"``.
            engine: Graphviz layout engine (``"dot"``, ``"neato"``,
                ``"fdp"``, etc.).  ``"dot"`` produces the cleanest
                hierarchical layouts for ERDs.
        """
        self.fmt = fmt
        self.direction = direction
        self.engine = engine

    def render(self, graph: GraphDict, output_path: str) -> str:
        """Render the graph and save to ``output_path``.

        Args:
            graph: Abstract graph dict.
            output_path: Destination path.  The format extension is
                appended automatically if not already present.

        Returns:
            Path of the rendered file.

        Raises:
            RuntimeError: When the Graphviz binary cannot be found.
            graphviz.ExecutableNotFound: Same underlying cause.
        """
        dot_source = graph_to_dot(graph, direction=self.direction)
        logger.debug("DOT source (%d chars) generated", len(dot_source))

        # Strip extension from output_path – graphviz adds it itself
        base = output_path
        if base.lower().endswith(f".{self.fmt}"):
            base = base[: -(len(self.fmt) + 1)]

        # Ensure output directory exists
        out_dir = os.path.dirname(base)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        src = graphviz.Source(dot_source, engine=self.engine)
        src.format = self.fmt

        try:
            rendered_path = src.render(
                filename=base,
                cleanup=True,   # remove the intermediate .dot file
                quiet=True,
            )
        except graphviz.ExecutableNotFound as exc:
            raise RuntimeError(
                "Graphviz executable not found.  Install the graphviz package "
                "or ensure the Graphviz binaries are on your PATH.\n"
                f"Original error: {exc}"
            ) from exc

        logger.info("Diagram saved to: %s", rendered_path)
        return rendered_path

    def get_dot_source(self, graph: GraphDict) -> str:
        """Return the raw DOT source without rendering.

        Useful for debugging or piping to external tools.

        Args:
            graph: Abstract graph dict.

        Returns:
            DOT language string.
        """
        return graph_to_dot(graph, direction=self.direction)
