import socket, logging, json, time, threading
from typing import List, Any, Dict
from datetime import datetime


try:
    from web.app import add_log
except ImportError:      # web UI optional
    def add_log(*_, **__):
        pass

logger = logging.getLogger(__name__)

class TCPSender:
    def __init__(self, cfg: Dict[str, Any]):
        self.host = cfg['host']
        self.port = cfg['port']
        self.timeout = cfg.get('timeout', 5)
        self.reconnect_interval = cfg.get('reconnect_interval', 30)
        self.socket: socket.socket | None = None
        self._lock = threading.Lock()
        self._last_connect = 0.0

    # ------------------------------------------------------------------ #
    def connect(self) -> bool:
        now = time.time()
        if now - self._last_connect < self.reconnect_interval:
            return False                     # too soon to retry
        self._last_connect = now

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(self.timeout)
            s.connect((self.host, self.port))
            self.socket = s
            logger.info(f'Connected to {self.host}:{self.port}')
            return True
        except Exception as exc:
            logger.error(f'Connect failed: {exc}')
            self.socket = None
            return False

    # ------------------------------------------------------------------ #
    def disconnect(self):
        if self.socket:
            try:
                self.socket.close()
            except Exception as exc:
                logger.debug(f'Disconnect error: {exc}')
        self.socket = None
        logger.info('Disconnected from TCP server')

    # ------------------------------------------------------------------ #
    def _send(self, data: str):
        if not self.socket and not self.connect():
            return False

        try:
            self.socket.sendall(data.encode('utf-8', 'replace'))
            return True
        except (BrokenPipeError, OSError) as exc:
            logger.warning(f'Send failed ({exc}); reconnecting...')
            self.disconnect()
            return False

    # ------------------------------------------------------------------ #
    def send_log(self, entry: Any) -> bool:
        log_str = json.dumps(entry) if isinstance(entry, dict) else str(entry)
        if not log_str.endswith('\n'):
            log_str += '\n'

        with self._lock:
            ok = self._send(log_str)
            if ok:
                add_log({
                    'timestamp': datetime.utcnow().isoformat(timespec='seconds'),
                    'data': log_str.strip(),
                    'raw': entry,
                })
            return ok

    # ------------------------------------------------------------------ #
    def send_logs(self, entries: List[Any]) -> bool:
        return all(self.send_log(e) for e in entries)
