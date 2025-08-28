from django.apps import AppConfig


class MessagingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'messaging'
    verbose_name = 'Messaging & Kafka'
    
    def ready(self):
        """Initialize Kafka clients when Django starts"""
        try:
            from .kafka_client import KafkaClientManager
            KafkaClientManager.initialize()
        except Exception as e:
            # Log error but don't fail startup
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to initialize Kafka clients: {e}")
