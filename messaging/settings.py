from dotenv import load_dotenv
import os

load_dotenv()

# Kafka Configuration
KAFKA_CONFIG = {
    # Bootstrap servers (list of Kafka broker addresses)
    'bootstrap_servers': [os.getenv('KAFKA_BOOTSTRAP_SERVERS').split(',')],
    
    # Producer Configuration
    'producer_retries': 3,
    'producer_acks': 'all',  # 'all', '1', or '0'
    'producer_compression': 'gzip',  # 'gzip', 'snappy', 'lz4', or None
    
    # Consumer Configuration
    'auto_offset_reset': 'earliest',  # 'earliest' or 'latest'
    'enable_auto_commit': True,
    'auto_commit_interval_ms': 1000,
    
    # Connection Configuration
    'request_timeout_ms': 30000,
    'session_timeout_ms': 30000,
    'heartbeat_interval_ms': 3000,
    
    # Security Configuration (if using SASL/SSL)
    'security_protocol': 'PLAINTEXT',  # 'PLAINTEXT', 'SSL', 'SASL_PLAINTEXT', 'SASL_SSL'
    'sasl_mechanism': None,  # 'PLAIN', 'SCRAM-SHA-256', 'SCRAM-SHA-512'
    'sasl_username': None,
    'sasl_password': None,
    
    # SSL Configuration (if using SSL)
    'ssl_cafile': None,
    'ssl_certfile': None,
    'ssl_keyfile': None,
    'ssl_password': None,
    
    # Topic Configuration
    'default_topics': {
        'urls': os.getenv('KAFKA_TOPIC_URLS'),
        'contents': os.getenv('KAFKA_TOPIC_CONTENTS')
    },
    
    # Consumer Group Configuration
    'default_consumer_groups': {
        'urls': os.getenv('KAFKA_CONSUMER_GROUP_URLS'),
        'contents': os.getenv('KAFKA_CONSUMER_GROUP_CONTENTS')
    },
    
    # Message Configuration
    'message_retention_days': 7,
    'max_message_size': 1048576,  # 1MB in bytes
    
    # Error Handling
    'max_retry_attempts': 3,
    'retry_backoff_ms': 1000,
    'dead_letter_topic': os.getenv('KAFKA_DEAD_LETTER_TOPIC'),
    
    # Monitoring
    'enable_metrics': True,
    'metrics_interval_seconds': 60,
}

# Message Handler Configuration
MESSAGE_HANDLER_CONFIG = {
    'enable_logging': True,
    'log_level': 'INFO',
    'enable_metrics': True,
    'batch_processing': False,
    'batch_size': 100,
    'batch_timeout_ms': 5000,
}

# Consumer Configuration
CONSUMER_CONFIG = {
    'auto_start': False,  # Set to True to auto-start consumers on Django startup
    'max_workers': 4,  # Maximum number of consumer worker threads
    'worker_timeout': 300,  # Worker timeout in seconds
    'enable_graceful_shutdown': True,
    'shutdown_timeout': 30,  # Shutdown timeout in seconds
}

# Producer Configuration
PRODUCER_CONFIG = {
    'enable_async': False,  # Enable async message sending
    'max_in_flight_requests': 5,
    'linger_ms': 0,  # Batch messages for this many milliseconds
    'batch_size': 16384,  # Batch size in bytes
    'enable_idempotence': True,  # Prevent duplicate messages
}

# Health Check Configuration
HEALTH_CHECK_CONFIG = {
    'enable_health_checks': True,
    'health_check_interval': 30,  # seconds
    'health_check_timeout': 10,  # seconds
    'unhealthy_threshold': 3,  # consecutive failures before marking unhealthy
}
