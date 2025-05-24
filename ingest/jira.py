import aiohttp
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging
import json
from pathlib import Path
from .base import AbstractLogSource
from core.log_event import LogEvent

logger = logging.getLogger(__name__)


JIRA_MAX_RESULTS = 1000          # Jira Cloud hard-limit per request
MAX_RETRIES      = 5             # after that we give up
BASE_BACKOFF     = 2.0           # seconds

class JiraIngest(AbstractLogSource):
    """Jira audit log ingestion source."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_url = config['api_url']
        self.username = config['username']
        self.password = config['password']
        self.categories = config.get('categories', ['all'])
        self.session = None
        self.last_fetch_time = self._load_last_fetch_time()
    
    def _load_last_fetch_time(self) -> datetime | None:
        """Load last fetch time from config file."""
        try:
            config_path = Path('config/config.json')
            if config_path.exists():
                with open(config_path) as f:
                    config = json.load(f)
                    if 'jira' in config.get('log_sources', {}):
                        last_fetch = config['log_sources']['jira'].get('last_fetch_time')
                        if last_fetch:
                            return datetime.fromisoformat(last_fetch)
        except Exception as e:
            logger.error(f"Error loading last fetch time: {str(e)}")
        return None

    def _save_last_fetch_time(self, fetch_time: datetime):
        """Save last fetch time to config file."""
        try:
            config_path = Path('config/config.json')
            if config_path.exists():
                with open(config_path) as f:
                    config = json.load(f)
                
                # Ensure the structure exists
                if 'log_sources' not in config:
                    config['log_sources'] = {}
                if 'jira' not in config['log_sources']:
                    config['log_sources']['jira'] = {}
                
                # Update the last fetch time
                config['log_sources']['jira']['last_fetch_time'] = fetch_time.isoformat()
                
                # Save the updated config
                with open(config_path, 'w') as f:
                    json.dump(config, f, indent=2)
                
                logger.debug(f"Saved last fetch time: {fetch_time.isoformat()}")
        except Exception as e:
            logger.error(f"Error saving last fetch time: {str(e)}")

    def validate_config(self) -> bool:
        """Validate Jira configuration."""
        required_fields = ['api_url', 'api_token']
        return all(field in self.config for field in required_fields)
    

    async def _init_session(self):
        """Create an aiohttp session (lazy-init) that authenticates with
        Jira using basic auth:  username:password  →  Base-64 →  Authorization: Basic …"""
        
        if self.session is None:
            # self.username and self.password should already be set on the class
            auth = aiohttp.BasicAuth(self.username, self.password)

            # No explicit Authorization header needed; aiohttp will add it.
            self.session = aiohttp.ClientSession(
                auth=auth,
                headers={
                    "Accept": "application/json"
                },
                timeout=aiohttp.ClientTimeout(total=30)   # optional: good default
            )

        
    async def _close_session(self):
        """Close aiohttp session if exists."""
        if self.session:
            await self.session.close()
            self.session = None
    
    # ------------------------------------------------------------------ #
    async def _request_with_backoff(self, url: str, **kwargs) -> Dict:
        """GET wrapper that respects Jira rate-limit responses."""
        retry = 0
        while retry <= MAX_RETRIES:
            async with self.session.get(url, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()

                # 429 or custom headers ⇒ back-off
                if resp.status == 429 or resp.headers.get("X-RateLimit-Remaining") == "0":
                    retry_after = resp.headers.get("Retry-After")
                    wait = float(retry_after) if retry_after else BASE_BACKOFF * 2 ** retry
                    wait += random.uniform(0, 0.5)            # jitter
                    logger.warning(f"Rate-limited – sleeping {wait:.1f}s (retry {retry}/{MAX_RETRIES})")
                    await asyncio.sleep(wait)
                    retry += 1
                    continue

                logger.error(f"Jira HTTP {resp.status}: {await resp.text()}")
                return {}

        logger.error("Exceeded max retries while fetching Jira logs")
        return {}

    # ------------------------------------------------------------------ #
    async def fetch_logs(
        self,
        start_time: datetime | None = None,
        end_time  : datetime | None = None
    ) -> List[LogEvent]:

        if not self.validate_config():
            raise ValueError("Invalid Jira configuration")

        end_time = end_time or datetime.utcnow()
        
        # If this is the first fetch (last_fetch_time is None), get last 5 hours
        # Otherwise, only get logs since the last fetch
        if self.last_fetch_time is None:
            start_time = start_time or (end_time - timedelta(hours=5))
            logger.info(f"Initial fetch: getting logs from last 5 hours ({start_time} to {end_time})")
        else:
            start_time = start_time or self.last_fetch_time
            logger.info(f"Fetching new logs since last fetch ({start_time} to {end_time})")

        await self._init_session()

        try:
            base_url = f"{self.api_url}/rest/api/3/auditing/record"
            params = {
                "maxResults": JIRA_MAX_RESULTS,
                "from": start_time.isoformat(),
                "to": end_time.isoformat(),
                "orderBy": "created",  # Sort by creation time
                "order": "desc"        # Most recent first
            }

            logs: list[LogEvent] = []

            while True:
                data = await self._request_with_backoff(base_url, params=params)
                if not data:                       # error already logged
                    break

                logs.extend(self._parse_logs(data))

                # ---------------- pagination ---------------- #
                next_page = data.get("nextPage")
                if not next_page:
                    break

                # Jira returns full URL in nextPage for Cloud; for DC you may need offset/limit
                base_url = next_page
                params = {}                     # nextPage already contains query items

            # Update last fetch time if we successfully got logs
            if logs:
                self.last_fetch_time = end_time
                self._save_last_fetch_time(end_time)
                logger.debug(f"Updated last fetch time to {self.last_fetch_time}")

            return logs

        finally:
            await self._close_session()
            
    def _parse_logs(self, data: Dict[str, Any]) -> List[LogEvent]:
        """Parse Jira audit log data into LogEvent objects."""
        events = []
        
        for record in data.get('records', []):
            try:
                event = LogEvent(
                    timestamp=datetime.fromisoformat(record['created']),
                    source='jira',
                    category=record.get('category', 'unknown'),
                    severity=self._determine_severity(record),
                    message=record.get('summary', ''),
                    event_id=record.get('id'),
                    user=record.get('author', {}).get('displayName'),
                    ip_address=record.get('remoteAddress'),
                    raw_data=record
                )
                events.append(event)
            except Exception as e:
                logger.error(f"Error parsing Jira log record: {str(e)}")
                continue
        
        return events
    
    def _determine_severity(self, record: Dict[str, Any]) -> str:
        """Determine log severity based on record data."""
        # Map Jira event types to severity levels
        severity_map = {
            'SECURITY': 'critical',
            'ADMIN': 'warning',
            'USER': 'info'
        }
        return severity_map.get(record.get('category', '').upper(), 'info') 