# Messaging App - Kafka Integration

This Django app provides a comprehensive Kafka messaging solution for the ONCS project, enabling asynchronous communication between different components of the system.

## Features

- **Kafka Producer/Consumer Management**: Centralized management of Kafka connections
- **Message Handlers**: Extensible message processing system
- **Service Layer**: High-level API for common messaging operations
- **Admin Interface**: Django admin integration for monitoring and control
- **Management Commands**: CLI tools for Kafka operations
- **Configuration Management**: Flexible configuration system
- **Scrapy Pipeline Integration**: Built-in support for Scrapy crawler output (default mode)

## Installation

1. **Add to INSTALLED_APPS** in your `settings.py`:

```python
INSTALLED_APPS = [
    # ... other apps
    'messaging',
]
```

2. **Install Dependencies**:

```bash
pip install -r requirements.txt
```

3. **Configure Kafka Settings** in your `settings.py`:

```python
# Kafka Configuration
KAFKA_CONFIG = {
    'bootstrap_servers': ['your-kafka-server:9092'],
    'producer_retries': 3,
    'producer_acks': 'all',
    'auto_offset_reset': 'earliest',
    # ... other settings
}
```

## Usage

### Basic Message Sending

```python
from messaging.services import MessagingService

# Send a URL collection message
success = MessagingService.send_url_collection(
    url="https://example.com",
    portal_id="portal_123",
    metadata={"source": "manual"}
)

# Send a content message
success = MessagingService.send_content(
    content="<html>...</html>",
    metadata={"type": "article"}
)

# Send a notification
success = MessagingService.send_notification(
    notification_type="email",
    recipient="user@example.com",
    content={"subject": "New Content", "body": "..."}
)
```

### Starting Consumers

```python
from messaging.services import MessagingService

# Start all default consumers (Scrapy integration mode)
MessagingService.start_all_consumers()

# Start specific consumers
MessagingService.start_urls_consumer()
MessagingService.start_contents_consumer()
MessagingService.start_notifications_consumer()
```

### Custom Message Handlers

```python
from messaging.message_handlers import BaseMessageHandler

class CustomHandler(BaseMessageHandler):
    def handle_message(self, message):
        # Process the message
        print(f"Processing message: {message}")
        return True

# Use with Kafka client manager
from messaging.kafka_client import KafkaClientManager

handler = CustomHandler('my_topic')
KafkaClientManager.start_consumer('my_topic', 'my_group', handler.handle_message)
```

## Management Commands

### Start URL Collection Consumer (Default: Scrapy Integration)

```bash
# Default mode: Scrapy integration (recommended for production)
python manage.py url_collector_consumer

# Extended Scrapy mode: comprehensive topic coverage
python manage.py url_collector_consumer --auto-detect-topics

# Custom mode: specific topics only
python manage.py url_collector_consumer --custom-mode --topics scraping_results discovered_urls

# Single topic custom mode
python manage.py url_collector_consumer --custom-mode --topic scraping_results
```

### Start General Kafka Consumers

```bash
# Start all consumers
python manage.py kafka_consumer

# Start specific consumers
python manage.py kafka_consumer --topics scraping_results portal_updates

# Run as daemon
python manage.py kafka_consumer --daemon

# Custom consumer group
python manage.py kafka_consumer --group-id my_custom_group
```

### Check Status

```bash
# Basic status
python manage.py kafka_status

# Detailed status
python manage.py kafka_status --detailed

# JSON output
python manage.py kafka_status --json
```

## Consumer Modes

### 1. Default Mode: Scrapy Integration (Recommended)
- **Command**: `python manage.py url_collector_consumer`
- **Topics**: `scraping_results`, `discovered_urls`, `crawler_results`, `spider_output`, `url_discovery`, `urls`
- **Use Case**: Production environment with thousands of Scrapy crawlers
- **Coverage**: Standard Scrapy pipeline topics

### 2. Extended Scrapy Mode
- **Command**: `python manage.py url_collector_consumer --auto-detect-topics`
- **Topics**: All standard topics + extended coverage (`article_urls`, `news_urls`, `news_discovery`, `portal_urls`, `crawler_urls`)
- **Use Case**: Complex Scrapy infrastructure with custom topics
- **Coverage**: Maximum topic coverage

### 3. Custom Mode
- **Command**: `python manage.py url_collector_consumer --custom-mode --topics topic1 topic2`
- **Topics**: Only specified topics
- **Use Case**: Specific topic consumption, testing, or limited scope
- **Coverage**: User-defined topics only

## Admin Interface

The messaging app provides a Django admin interface for:

- **Status Monitoring**: Real-time Kafka connection status
- **Consumer Control**: Start/stop consumers
- **Message Statistics**: View message processing metrics

Access via: `/admin/messaging/`

## Configuration

### Environment Variables

```bash
# Kafka Connection
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_SECURITY_PROTOCOL=PLAINTEXT
KAFKA_SASL_USERNAME=your_username
KAFKA_SASL_PASSWORD=your_password

# Consumer Settings
KAFKA_AUTO_OFFSET_RESET=earliest
KAFKA_ENABLE_AUTO_COMMIT=true
```

### Advanced Configuration

```python
# In settings.py
KAFKA_CONFIG = {
    'bootstrap_servers': ['kafka1:9092', 'kafka2:9092'],
    'security_protocol': 'SASL_SSL',
    'sasl_mechanism': 'SCRAM-SHA-256',
    'sasl_username': 'your_username',
    'sasl_password': 'your_password',
    'ssl_cafile': '/path/to/ca.pem',
    'producer_compression': 'snappy',
    'enable_idempotence': True,
}
```

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Django App    │    │  Messaging App   │    │   Kafka Broker  │
│                 │    │                  │    │                 │
│ ┌─────────────┐ │    │ ┌──────────────┐ │    │ ┌─────────────┐ │
│ │   Views     │ │───▶│ │   Services   │ │───▶│ │  Producer   │ │
│ └─────────────┘ │    │ └──────────────┘ │    │ └─────────────┘ │
│                 │    │                  │    │                 │
│ ┌─────────────┐ │    │ ┌──────────────┐ │    │ ┌─────────────┐ │
│ │   Models    │ │◀───│ │   Handlers   │ │◀───│ │  Consumer   │ │
│ └─────────────┘ │    │ └──────────────┘ │    │ └─────────────┘ │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Message Types

### URL Collection Messages
```json
{
    "url": "https://example.com/news/article",
    "portal_id": "portal_123",
    "metadata": {
        "crawler_config_id": "crawler_config_456",
        "task_id": "task_789",
        "spider_name": "news_spider",
        "source": "scrapy_discovery"
    },
    "type": "url_collection"
}
```

### Scrapy Pipeline Messages (Auto-detected)
```json
{
    "url": "https://example.com/news/article",
    "title": "Article Title",
    "meta": {
        "portal_id": "portal_123",
        "crawler_config_id": "crawler_config_456",
        "task_id": "task_789",
        "spider_name": "news_spider",
        "kafka.topic": "scraping_results"
    }
}
```

### Content Messages
```json
{
    "content": "<html><body>Article content...</body></html>",
    "metadata": {
        "type": "article",
        "portal_id": "portal_123"
    },
    "type": "content"
}
```

### Notifications
```json
{
    "type": "email",
    "recipient": "user@example.com",
    "content": {"subject": "New Content", "body": "..."},
    "message_type": "notification"
}
```

## Scrapy Integration

### Automatic Format Detection
The URL consumer automatically detects and processes:
- **Scrapy pipeline output** with encoded content
- **Direct URL collection** messages
- **Mixed message formats** from different sources

### Topic Compatibility
Consumes from Scrapy-compatible topics:
- `scraping_results` - General scraping results
- `discovered_urls` - URLs found during crawling
- `crawler_results` - Crawler output
- `spider_output` - Spider results
- `url_discovery` - URL discovery results
- `urls` - Fallback topic

### Metadata Mapping
Automatically maps Scrapy metadata to expected format:
- `portal_id` → Portal identification
- `crawler_config_id` → Crawler configuration
- `task_id` → Task identifier
- `spider_name` → Spider name
- `source` → Discovery source

## Error Handling

The app includes comprehensive error handling:

- **Connection Failures**: Automatic retry with exponential backoff
- **Message Processing Errors**: Dead letter queue for failed messages
- **Consumer Failures**: Graceful shutdown and restart capabilities
- **Configuration Errors**: Validation and fallback to defaults
- **Format Detection**: Graceful handling of different message formats

## Monitoring

### Health Checks

```python
from messaging.services import MessagingService

# Check service health
status = MessagingService.get_status()
print(f"Service running: {status['running']}")
print(f"Producer connected: {status['producer_connected']}")
print(f"Active consumers: {status['total_consumers']}")
```

### Logging

The app provides detailed logging for:

- Connection events
- Message processing
- Error conditions
- Performance metrics

Configure logging in your Django settings:

```python
LOGGING = {
    'loggers': {
        'messaging': {
            'level': 'INFO',
            'handlers': ['console', 'file'],
        },
    },
}
```

## Testing

### Unit Tests

```bash
python manage.py test messaging
```

### Integration Tests

```bash
# Start Kafka container for testing
docker run -d --name kafka-test -p 9092:9092 confluentinc/cp-kafka:latest

# Run tests
python manage.py test messaging.tests.test_integration
```

### Scrapy Integration Testing

```bash
# Test Scrapy integration examples
python messaging/scrapy_integration_example.py
```

## Deployment

### Production Considerations

1. **Default Mode**: Use default Scrapy integration mode for production
2. **Security**: Use SASL/SSL for production Kafka clusters
3. **Scaling**: Configure multiple consumer instances for high throughput
4. **Monitoring**: Set up alerts for connection failures and message processing errors
5. **Backup**: Configure message retention policies

### Docker

```dockerfile
# Add to your Dockerfile
RUN pip install kafka-python confluent-kafka

# Environment variables
ENV KAFKA_BOOTSTRAP_SERVERS=kafka:9092
ENV KAFKA_SECURITY_PROTOCOL=PLAINTEXT
```

## Troubleshooting

### Common Issues

1. **Connection Refused**: Check Kafka server address and port
2. **Authentication Failed**: Verify SASL credentials
3. **Consumer Not Receiving Messages**: Check topic name and consumer group
4. **High Memory Usage**: Adjust batch sizes and worker counts
5. **Scrapy Message Format**: Ensure proper metadata structure

### Debug Mode

```python
# Enable debug logging
LOGGING = {
    'loggers': {
        'messaging': {
            'level': 'DEBUG',
        },
    },
}
```

## Contributing

1. Follow the existing code style
2. Add tests for new functionality
3. Update documentation for API changes
4. Use conventional commit messages

## License

This app is part of the ONCS project and follows the same license terms.
