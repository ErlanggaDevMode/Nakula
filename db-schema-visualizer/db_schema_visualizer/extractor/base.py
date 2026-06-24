"""Abstract base class for all database metadata extractors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from db_schema_visualizer.model.schema import DatabaseSchema


class AbstractExtractor(ABC):
    """Interface that every extractor implementation must fulfil.

    Concrete subclasses handle the database-specific connection details
    and translate the native metadata into the common ``DatabaseSchema``
    model understood by the rest of the tool.
    """

    @abstractmethod
    def extract(
        self,
        schemas: Optional[List[str]] = None,
        tables: Optional[List[str]] = None,
        include_many_to_many: bool = True,
    ) -> DatabaseSchema:
        """Extract metadata and return a populated ``DatabaseSchema``.

        Args:
            schemas: If provided, only extract tables from these schema
                names.  ``None`` means all schemas.
            tables: If provided, only extract these table names.
                ``None`` means all tables.
            include_many_to_many: When ``True``, detect junction tables
                and annotate them; when ``False``, skip that detection.

        Returns:
            A fully populated :class:`DatabaseSchema` instance.
        """
        ...
