# Log Forwarder

A robust log forwarding system that collects logs from various sources and forwards them to a TCP server in different formats (JSON, CEF, CSV).

## Features

- Multiple log source support (Jira, File-based)
- Configurable log formatting (JSON, CEF, CSV)
- Rate limiting and backoff handling
- Robust error handling and logging
- Asynchronous operation for better performance

## Installation

1. Clone the repository:

```bash
git clone https://github.com/darkling10/log-forwarder-etl.git
cd log-forwarder
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

Create a `config.json` file in the `config` directory with the following structure:

```json
{
  "tcp_server": {
    "host": "localhost",
    "port": 514,
    "reconnect_interval": 30
  },
  "log_sources": {
    "jira": {
      "enabled": true,
      "api_url": "https://your-jira-instance.atlassian.net",
      "username": "your-email@example.com",
      "api_token": "your-api-token",
      "categories": ["all"]
    },
    "file": {
      "enabled": true,
      "path": "logs/audit.log",
      "format": "json"
    }
  },
  "formatter": {
    "type": "json",
    "options": {
      "timestamp_format": "%Y-%m-%d %H:%M:%S"
    }
  },
  "logging": {
    "level": "INFO",
    "file": "logs/forwarder.log"
  }
}
```

### Configuration Options

#### TCP Server

- `host`: TCP server hostname
- `port`: TCP server port
- `reconnect_interval`: Seconds to wait before reconnecting

#### Log Sources

- `jira`: Jira audit log configuration
  - `api_url`: Jira instance URL
  - `username`: Jira username/email
  - `api_token`: Jira API token
  - `categories`: List of categories to fetch
- `file`: File-based log source
  - `path`: Path to log file
  - `format`: Log file format (json, cef, csv)

#### Formatter

- `type`: Output format (json, cef, csv)
- `options`: Format-specific options

#### Logging

- `level`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `file`: Path to log file

## Usage

Run the log forwarder:

```bash
python main.py
```

The system will:

1. Initialize configured log sources
2. Connect to the TCP server
3. Start collecting and forwarding logs
4. Handle reconnections automatically
5. Apply rate limiting and backoff as needed

## Log Formats

### JSON Format

```json
{
  "timestamp": "2024-03-20 10:30:45",
  "source": "jira",
  "category": "security",
  "severity": "info",
  "message": "User login successful",
  "event_id": "12345",
  "user": "john.doe",
  "ip_address": "192.168.1.1"
}
```

### CEF Format

```
CEF:0|Jira|Audit|1.0|100|User Login|5|suser=john.doe src=192.168.1.1
```

### CSV Format

```
2024-03-20 10:30:45,jira,security,info,"User login successful",12345,john.doe,192.168.1.1
```

## Error Handling

The system includes robust error handling:

- Automatic reconnection to TCP server
- Rate limiting with exponential backoff
- Log rotation and size management
- Detailed error logging

## Docker Support

The application is containerized using Docker. To run with Docker:

```bash
# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down
```

### Docker Configuration Verification

TODO: Verify the following Docker configurations:

1. Volume Mounts:

   - [ ] Verify config directory mount
   - [ ] Verify logs directory mount
   - [ ] Check permissions on mounted volumes

2. Network Configuration:

   - [ ] Verify log-network bridge creation
   - [ ] Test TCP connectivity to target server
   - [ ] Check container DNS resolution

3. Health Checks:

   - [ ] Verify health check endpoint
   - [ ] Test automatic restart on failure
   - [ ] Validate health check parameters

4. Resource Limits:

   - [ ] Set appropriate memory limits
   - [ ] Configure CPU constraints
   - [ ] Define restart policies

5. Security:
   - [ ] Verify non-root user execution
   - [ ] Check file permissions
   - [ ] Validate environment variables

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
