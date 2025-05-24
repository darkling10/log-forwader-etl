from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional

@dataclass
class LogEvent:
    """Standardized log event structure."""
    
    timestamp: datetime
    source: str
    category: str
    severity: str
    message: str
    raw_data: Dict[str, Any]
    event_id: Optional[str] = None
    user: Optional[str] = None
    ip_address: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the log event to a dictionary."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
            'category': self.category,
            'severity': self.severity,
            'message': self.message,
            'event_id': self.event_id,
            'user': self.user,
            'ip_address': self.ip_address,
            'raw_data': self.raw_data
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LogEvent':
        """Create a LogEvent instance from a dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data['timestamp']),
            source=data['source'],
            category=data['category'],
            severity=data['severity'],
            message=data['message'],
            event_id=data.get('event_id'),
            user=data.get('user'),
            ip_address=data.get('ip_address'),
            raw_data=data['raw_data']
        ) 