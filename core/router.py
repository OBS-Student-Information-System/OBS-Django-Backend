"""
Core Router Module.
Handles dynamic action dispatching to Service methods.
Implements Command Pattern / Dispatcher to adhere to OCP.
"""
import logging
from typing import Dict, Any, Callable

logger = logging.getLogger(__name__)

class ActionDispatcher:
    """
    Registry for mapping action strings to handler functions.
    Eliminates the need for long if-elif chains in the main handler.
    """
    def __init__(self):
        self._handlers: Dict[str, Callable] = {}

    def register(self, action: str, handler: Callable):
        """Registers a handler function for a specific action."""
        self._handlers[action] = handler
        logger.debug(f"Registered handler for action: {action}")

    def dispatch(self, action: str, body: Dict[str, Any], context: Any) -> Any:
        """
        Dispatches the request to the registered handler.
        
        Args:
            action: The action string (e.g., 'login', 'get_grades').
            body: The parsed JSON body of the request.
            context: The RequestHandler instance (for sending responses).
            
        Returns:
            The result from the handler, or None if handled internally.
        """
        handler = self._handlers.get(action)
        
        if not handler:
            logger.warning(f"Unknown action: {action}")
            context._send_response(400, {"status": "error", "message": f"Unknown action: {action}"})
            return None

        try:
            # Execute handler
            return handler(body, context)
        except Exception as e:
            logger.exception(f"Exception during dispatch of action '{action}'")
            context._send_response(500, {"status": "error", "message": str(e)})
            return None
