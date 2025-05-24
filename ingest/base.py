from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import datetime

class AbstractLogSource(ABC):
    """Abstract base class for all log sources."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the log source with configuration.
        
        Args:
            config (Dict[str, Any]): Configuration dictionary for this source
        """
        self.config = config
    
    @abstractmethod
    async def fetch_logs(self, start_time: datetime = None, end_time: datetime = None) -> List[Dict[str, Any]]:
        """
        Fetch logs from the source.
        
        Args:
            start_time (datetime, optional): Start time for log fetching
            end_time (datetime, optional): End time for log fetching
            
        Returns:
            List[Dict[str, Any]]: List of log events
        """
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """
        Validate the source configuration.
        
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        pass 