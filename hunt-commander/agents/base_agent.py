"""Base agent class for all agents in the system."""
from abc import ABC, abstractmethod
from typing import Any, Dict
from utils.logger import log

class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the agent.

        Args:
            config: Configuration dictionary for the agent
        """
        self.config = config
        self.name = self.__class__.__name__
        log.info(f"Initialized {self.name}")

    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """Execute the agent's main functionality.

        Returns:
            Result of the agent's execution
        """
        pass

    def log_info(self, message: str):
        """Log an info message.

        Args:
            message: Message to log
        """
        log.info(f"[{self.name}] {message}")

    def log_error(self, message: str):
        """Log an error message.

        Args:
            message: Message to log
        """
        log.error(f"[{self.name}] {message}")

    def log_debug(self, message: str):
        """Log a debug message.

        Args:
            message: Message to log
        """
        log.debug(f"[{self.name}] {message}")
