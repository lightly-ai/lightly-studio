"""Service to manage an in-process REPL."""

from __future__ import annotations

import asyncio
import io
import logging
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import Any, AsyncGenerator

logger = logging.getLogger(__name__)


class REPLService:
    """Manages an in-process Python REPL."""

    def __init__(self) -> None:
        self._globals: dict[str, Any] = {}
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._initialized = False

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        
        try:
            from lightly_studio import db_manager
            from lightly_studio.resolvers import dataset_resolver
            
            # Initialize globals with useful context
            self._globals["db_manager"] = db_manager
            self._globals["dataset_resolver"] = dataset_resolver
            self._globals["session"] = None  # Placeholder
            
            self._initialized = True
            logger.info("In-process REPL initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize REPL context: {e}")

    async def start(self) -> None:
        """Ensure the REPL context is initialized."""
        self._ensure_initialized()

    async def execute(self, code: str) -> AsyncGenerator[dict[str, Any], None]:
        """Execute code in a separate thread and yield output."""
        self._ensure_initialized()

        loop = asyncio.get_running_loop()
        
        def _run_code() -> tuple[str, str | None]:
            output_buffer = io.StringIO()
            
            # Custom print to capture output
            def custom_print(*args: Any, **kwargs: Any) -> None:
                kwargs['file'] = output_buffer
                # Use the built-in print implementation but direct to our buffer
                __builtins__['print'](*args, **kwargs)

            # Inject custom print
            self._globals['print'] = custom_print
            
            error_traceback = None
            try:
                # Execute code with persistent globals
                exec(code, self._globals)
            except Exception:
                error_traceback = traceback.format_exc()
            
            return output_buffer.getvalue(), error_traceback

        # Run in thread to avoid blocking the main event loop
        stdout, tb = await loop.run_in_executor(self._executor, _run_code)

        if stdout:
            yield {"type": "stream", "name": "stdout", "text": stdout}
        
        if tb:
            yield {
                "type": "error",
                "ename": "ExecutionError",
                "evalue": "Error executing code",
                "traceback": tb.splitlines()
            }

# Global instance
repl_service = REPLService()

