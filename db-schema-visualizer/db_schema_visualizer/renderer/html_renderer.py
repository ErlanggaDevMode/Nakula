"""
Interactive HTML renderer.

Generates a single self-contained HTML file combining:
- A Jinja2 template (``templates/interactive.html``)
- The graph data serialised as JSON
- D3.js loaded from CDN (with an inline warning if offline)

The output file can be opened directly in any modern browser without
a web server.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from db_schema_visualizer import config
from db_schema_visualizer.graph.builder import GraphDict
from db_schema_visualizer.renderer.base import AbstractRenderer

logger = logging.getLogger(__name__)

# Directory that holds ``interactive.html``
_TEMPLATE_DIR = Path(__file__).parent / "templates"


class HtmlRenderer(AbstractRenderer):
    """Renders an ERD as an interactive, standalone HTML file.

    The generated file embeds the graph data as JSON and uses D3.js
    (loaded from CDN) for pan, zoom, drag, and search interactions.

    Example::

        renderer = HtmlRenderer()
        path = renderer.render(graph, "output/diagram.html")
    """

    def __init__(
        self,
        title: str = config.HTML_TITLE,
        d3_cdn: str = config.D3_CDN_URL,
    ) -> None:
        """Initialise the renderer.

        Args:
            title: Page title shown in the browser tab and top bar.
            d3_cdn: CDN URL for the D3.js library.  Override for
                offline/intranet environments.
        """
        self.title = title
        self.d3_cdn = d3_cdn
        self._env = Environment(
            loader=FileSystemLoader(str(_TEMPLATE_DIR)),
            autoescape=select_autoescape(enabled_extensions=()),
        )

    def render(self, graph: GraphDict, output_path: str) -> str:
        """Render the graph and write the HTML file.

        Args:
            graph: Abstract graph dict from :class:`GraphBuilder`.
            output_path: Destination path.  ``.html`` extension is
                appended if not already present.

        Returns:
            Path of the written HTML file.
        """
        # Ensure .html extension
        if not output_path.lower().endswith(".html"):
            output_path = output_path + ".html"

        # Enrich nodes with display colours before serialising
        enriched_graph = self._enrich_graph(graph)

        graph_json = json.dumps(enriched_graph, ensure_ascii=False, indent=None)

        template = self._env.get_template("interactive.html")
        html_content = template.render(
            title=self.title,
            d3_cdn=self.d3_cdn,
            graph_json=graph_json,
        )

        # Ensure output directory exists
        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as fh:
            fh.write(html_content)

        logger.info("Interactive HTML saved to: %s", output_path)
        return output_path

    # ------------------------------------------------------------------

    @staticmethod
    def _enrich_graph(graph: GraphDict) -> Dict[str, Any]:
        """Add display-only fields (e.g. header colours) to node dicts.

        The original ``graph`` dict is not mutated; a shallow copy with
        enriched nodes is returned.
        """
        enriched_nodes = []
        for node in graph["nodes"]:
            enriched = dict(node)
            enriched["header_color"] = config.get_header_color(node.get("schema"))
            enriched_nodes.append(enriched)

        return {**graph, "nodes": enriched_nodes}
