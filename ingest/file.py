import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import re

from .base import AbstractLogSource
from core.log_event import LogEvent

logger = logging.getLogger(__name__)

class FileIngest(AbstractLogSource):
    """Local file log ingestion source."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.file_path = config['path']
        self.last_position = 0
        self.categories = config.get('categories', ['all'])
    
    def validate_config(self) -> bool:
        """Validate file source configuration."""
        required_fields = ['path']
        if not all(field in self.config for field in required_fields):
            return False
        
        # Check if file exists
        try:
            path = Path(self.file_path)
            return path.exists() and path.is_file()
        except Exception:
            return False
    
    async def fetch_logs(self, start_time: datetime = None, end_time: datetime = None) -> List[LogEvent]:
        """
        Fetch logs from the local file.
        
        Args:
            start_time: Start time for log fetching (not used for file source)
            end_time: End time for log fetching (not used for file source)
            
        Returns:
            List of LogEvent objects
        """
        if not self.validate_config():
            raise ValueError("Invalid file configuration")
        
        try:
            events = []
            path = Path(self.file_path)
            
            # Read new lines since last position
            with open(path, 'r') as f:
                f.seek(self.last_position)
                new_lines = f.readlines()
                self.last_position = f.tell()
            
            # Parse each line into a LogEvent
            for line in new_lines:
                try:
                    event = self._parse_line(line.strip())
                    if event:
                        events.append(event)
                except Exception as e:
                    logger.error(f"Error parsing log line: {str(e)}")
                    continue
            
            return events
                
        except Exception as e:
            logger.error(f"Error reading log file: {str(e)}")
            return []
    
    def _parse_line(self, line: str) -> LogEvent:
        """Parse a single log line into a LogEvent."""
        # Try to parse as JSON first
        try:
            data = json.loads(line)
            return self._create_event_from_json(data)
        except json.JSONDecodeError:
            # If not JSON, try to parse as structured log
            return self._create_event_from_text(line)
    
    def _create_event_from_json(self, data: Dict[str, Any]) -> LogEvent:
        """Create LogEvent from JSON data."""
        return LogEvent(
            timestamp=datetime.fromisoformat(data.get('timestamp', datetime.utcnow().isoformat())),
            source='file',
            category=data.get('category', 'unknown'),
            severity=data.get('severity', 'info'),
            message=data.get('message', ''),
            event_id=data.get('event_id'),
            user=data.get('user'),
            ip_address=data.get('ip_address'),
            raw_data=data
        )
    
    def _create_event_from_text(self, line: str) -> LogEvent:
        """Create LogEvent from text log line."""
        # Common log patterns
        timestamp_pattern = r'(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)'
        severity_pattern = r'(ERROR|WARN|INFO|DEBUG|CRITICAL)'
        
        # Extract timestamp
        timestamp_match = re.search(timestamp_pattern, line)
        timestamp = datetime.fromisoformat(timestamp_match.group(1)) if timestamp_match else datetime.utcnow()
        
        # Extract severity
        severity_match = re.search(severity_pattern, line)
        severity = severity_match.group(1).lower() if severity_match else 'info'
        
        return LogEvent(
            timestamp=timestamp,
            source='file',
            category='system',
            severity=severity,
            message=line,
            raw_data={'raw_line': line}
        ) 