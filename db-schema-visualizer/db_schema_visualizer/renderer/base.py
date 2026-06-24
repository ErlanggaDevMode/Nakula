"""Abstract base class for all output renderers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from db_schema_visualizer.graph.builder import GraphDict


class AbstractRenderer(ABC):
    """Interface every renderer must implement.

    Renderers receive the abstract :class:`GraphDict` produced by
    :class:`GraphBuilder` and write the final artefact (file or string)
    to ``output_path``.
    """

    @abstractmethod
    def render(self, graph: GraphDict, output_path: str) -> str:
        """Render the graph and write it to ``output_path``.

        Args:
            graph: Abstract graph dict from :class:`GraphBuilder`.
            output_path: Filesystem path (without extension for some
                formats – the renderer may append the correct extension).

        Returns:
            The actual path of the written file (may differ from
            ``output_path`` if an extension was appended).
        """
        ...
