import asyncio
import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import time

# Add the project root directory to Python path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from ingest.jira import JiraIngest
from ingest.file import FileIngest
from core.log_event import LogEvent
from core.tcp_sender import TCPSender
from core.formatters import FormatterFactory

# Configure logging
def setup_logging(config: Dict[str, Any]):
    """Configure logging based on config."""
    log_config = config['logging']
    
    # Create logs directory if it doesn't exist
    log_path = Path(log_config['file'])
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    handler = logging.handlers.RotatingFileHandler(
        log_config['file'],
        maxBytes=log_config['max_size'],
        backupCount=log_config['backup_count']
    )
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(log_config['level'])
    root_logger.addHandler(handler)

async def load_config() -> Dict[str, Any]:
    """Load configuration from config.json."""
    config_path = project_root / 'config' / 'config.json'
    with open(config_path) as f:
        return json.load(f)

async def load_filters() -> Dict[str, Any]:
    """Load filters from filter.json."""
    filter_path = project_root / 'config' / 'filter.json'
    with open(filter_path) as f:
        return json.load(f)

async def initialize_sources(config: Dict[str, Any]) -> List[Any]:
    """Initialize enabled log sources."""
    sources = []
    for source_name, source_config in config['sources'].items():
        if not source_config.get('enabled', False):
            continue
            
        if source_name == 'jira':
            source = JiraIngest(source_config)
            if source.validate_config():
                sources.append(source)
            else:
                logging.error(f"Invalid configuration for {source_name}")
        elif source_name == 'file':
            source = FileIngest(source_config)
            if source.validate_config():
                sources.append(source)
            else:
                logging.error(f"Invalid configuration for {source_name}")
    
    return sources

async def main():
    """Main entry point."""
    # Initialize logger first
    logger = logging.getLogger(__name__)
    
    try:
        # Load configurations
        config = await load_config()
        filters = await load_filters()
        
        # Setup logging
        setup_logging(config)
        logger.info("Starting log forwarder")
        
        # Initialize TCP sender
        tcp_sender = TCPSender(config['tcp_server'])
        
        # Initialize formatter
        formatter = FormatterFactory.get_formatter(config['formatter']['type'])
        logger.info(f"Using {config['formatter']['type'].upper()} formatter")
        
        # Initialize sources
        sources = await initialize_sources(config)
        if not sources:
            logger.error("No valid sources configured")
            return
        
        # Connect to TCP server
        tcp_sender.connect()
        
        while True:
            try:
                # Fetch logs from all sources
                for source in sources:
                    logs = await source.fetch_logs()
                    logger.info(f"Fetched {len(logs)} logs from {source.__class__.__name__}")
                    
                    if logs:
                        # Format logs according to configured format
                        formatted_logs = []
                        for log in logs:
                            formatted_log = formatter.format(log)
                            if formatted_log:
                                formatted_logs.append(formatted_log)
                        
                        if formatted_logs:
                            # Send formatted logs
                            tcp_sender.send_logs(formatted_logs)
                            logger.info(f"Forwarded {len(formatted_logs)} logs in {config['formatter']['type'].upper()} format")
                
                # Wait for next polling interval
                await asyncio.sleep(config['sources']['file']['poll_interval'])
                
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                await asyncio.sleep(5)  # Wait before retrying
                
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        raise
    finally:
        if 'tcp_sender' in locals():
            tcp_sender.disconnect()

if __name__ == "__main__":
    asyncio.run(main()) 