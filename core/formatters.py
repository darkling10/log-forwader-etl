import logging
import json
import csv
from io import StringIO
from datetime import datetime
from abc import ABC, abstractmethod

class BaseFormatter(ABC):
    @abstractmethod
    def format(self, log_event):
        pass

class CEFFormatter(BaseFormatter):
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.cef_version = "0"
        self.device_vendor = "LogForwarder"
        self.device_product = "LogForwarder"
        self.device_version = "1.0"

    def format(self, log_event):
        try:
            severity_map = {
                "critical": "10",
                "error": "8",
                "warning": "6",
                "info": "4",
                "debug": "2"
            }
            severity = severity_map.get(log_event.severity.lower(), "4")

            extension = {
                "msg": log_event.message,
                "cat": log_event.category,
                "src": log_event.ip_address,
                "duser": log_event.user,
                "eventId": log_event.event_id,
                "rt": log_event.timestamp.isoformat() if isinstance(log_event.timestamp, datetime) else log_event.timestamp
            }

            if log_event.raw_data:
                for key, value in log_event.raw_data.items():
                    extension[f"raw_{key}"] = str(value)

            extension_str = " ".join([f"{k}={v}" for k, v in extension.items()])

            return (
                f"CEF:{self.cef_version}|{self.device_vendor}|{self.device_product}|"
                f"{self.device_version}|{log_event.category}|{log_event.message}|"
                f"{severity}|{extension_str}"
            )

        except Exception as e:
            self.logger.error(f"Error formatting log to CEF: {str(e)}")
            return None

class CSVFormatter(BaseFormatter):
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.fieldnames = [
            'timestamp', 'category', 'severity', 'message', 
            'event_id', 'user', 'ip_address', 'raw_data'
        ]

    def format(self, log_event):
        try:
            raw_data_str = json.dumps(log_event.raw_data) if log_event.raw_data else ""

            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=self.fieldnames, quoting=csv.QUOTE_MINIMAL)
            row = {
                'timestamp': log_event.timestamp.isoformat() if isinstance(log_event.timestamp, datetime) else log_event.timestamp,
                'category': log_event.category,
                'severity': log_event.severity,
                'message': log_event.message,
                'event_id': log_event.event_id,
                'user': log_event.user,
                'ip_address': log_event.ip_address,
            }
            writer.writerow(row)
            return output.getvalue().strip()

        except Exception as e:
            self.logger.error(f"Error formatting log to CSV: {str(e)}")
            return None

class JSONFormatter(BaseFormatter):
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def format(self, log_event):
        try:
            return json.dumps(log_event.to_dict())
        except Exception as e:
            self.logger.error(f"Error formatting log to JSON: {str(e)}")
            return None

class FormatterFactory:
    @staticmethod
    def get_formatter(format_type: str) -> BaseFormatter:
        formatters = {
            'cef': CEFFormatter,
            'csv': CSVFormatter,
            'json': JSONFormatter
        }

        formatter_class = formatters.get(format_type.lower())
        if not formatter_class:
            raise ValueError(f"Unsupported format type: {format_type}")

        return formatter_class()
