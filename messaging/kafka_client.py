import json
import logging
from typing import Dict, Any, Optional, Callable
from django.conf import settings
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
import threading
import time

logger = logging.getLogger(__name__)


class KafkaClientManager:
    """Manages Kafka producer and consumer connections"""
    
    _producer: Optional[KafkaProducer] = None
    _consumers: Dict[str, KafkaConsumer] = {}
    _consumer_threads: Dict[str, threading.Thread] = {}
    _running = False
    
    @classmethod
    def initialize(cls):
        """Initialize Kafka connections"""
        try:
            cls._producer = cls._create_producer()
            cls._running = True
            logger.info("Kafka producer initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            cls._producer = None
    
    @classmethod
    def _create_producer(cls) -> KafkaProducer:
        """Create Kafka producer with configuration"""
        kafka_config = getattr(settings, 'KAFKA_CONFIG', {})
        
        producer_config = {
            'bootstrap_servers': kafka_config.get('bootstrap_servers', ['localhost:9092']),
            'value_serializer': lambda v: json.dumps(v).encode('utf-8'),
            'key_serializer': lambda k: k.encode('utf-8') if k else None,
            'retries': kafka_config.get('producer_retries', 3),
            'acks': kafka_config.get('producer_acks', 'all'),
            'compression_type': kafka_config.get('producer_compression', 'gzip'),
        }
        
        return KafkaProducer(**producer_config)
    
    @classmethod
    def _create_consumer(cls, topic: str, group_id: str) -> KafkaConsumer:
        """Create Kafka consumer for a specific topic"""
        kafka_config = getattr(settings, 'KAFKA_CONFIG', {})
        
        consumer_config = {
            'bootstrap_servers': kafka_config.get('bootstrap_servers', ['localhost:9092']),
            'group_id': group_id,
            'auto_offset_reset': kafka_config.get('auto_offset_reset', 'earliest'),
            'enable_auto_commit': kafka_config.get('enable_auto_commit', True),
            'auto_commit_interval_ms': kafka_config.get('auto_commit_interval_ms', 1000),
            'value_deserializer': lambda x: json.loads(x.decode('utf-8')) if x else None,
            'key_deserializer': lambda x: x.decode('utf-8') if x else None,
        }
        
        consumer = KafkaConsumer(topic, **consumer_config)
        return consumer
    
    @classmethod
    def send_message(cls, topic: str, message: Dict[str, Any], key: Optional[str] = None) -> bool:
        """Send a message to a Kafka topic"""
        if not cls._producer:
            logger.error("Kafka producer not initialized")
            return False
        
        try:
            future = cls._producer.send(topic, value=message, key=key)
            # Wait for the message to be sent
            record_metadata = future.get(timeout=10)
            logger.info(f"Message sent to {topic} partition {record_metadata.partition} offset {record_metadata.offset}")
            return True
        except KafkaError as e:
            logger.error(f"Failed to send message to {topic}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending message to {topic}: {e}")
            return False
    
    @classmethod
    def start_consumer(cls, topic: str, group_id: str, message_handler: Callable[[Dict[str, Any]], None]):
        """Start a consumer for a specific topic"""
        if topic in cls._consumers:
            logger.warning(f"Consumer for topic {topic} already running")
            return
        
        try:
            consumer = cls._create_consumer(topic, group_id)
            cls._consumers[topic] = consumer
            
            # Start consumer thread
            thread = threading.Thread(
                target=cls._consume_messages,
                args=(topic, consumer, message_handler),
                daemon=True
            )
            cls._consumer_threads[topic] = thread
            thread.start()
            
            logger.info(f"Started consumer for topic {topic} with group {group_id}")
        except Exception as e:
            logger.error(f"Failed to start consumer for topic {topic}: {e}")
    
    @classmethod
    def _consume_messages(cls, topic: str, consumer: KafkaConsumer, message_handler: Callable[[Dict[str, Any]], None]):
        """Consume messages from a topic"""
        try:
            for message in consumer:
                if not cls._running:
                    break
                
                try:
                    message_handler(message.value)
                    logger.debug(f"Processed message from {topic}: {message.value}")
                except Exception as e:
                    logger.error(f"Error processing message from {topic}: {e}")
                    
        except Exception as e:
            logger.error(f"Consumer error for topic {topic}: {e}")
        finally:
            consumer.close()
            logger.info(f"Consumer for topic {topic} stopped")
    
    @classmethod
    def stop_consumer(cls, topic: str):
        """Stop a specific consumer"""
        if topic in cls._consumers:
            consumer = cls._consumers[topic]
            consumer.close()
            del cls._consumers[topic]
            
            if topic in cls._consumer_threads:
                thread = cls._consumer_threads[topic]
                thread.join(timeout=5)
                del cls._consumer_threads[topic]
            
            logger.info(f"Stopped consumer for topic {topic}")
    
    @classmethod
    def stop_all_consumers(cls):
        """Stop all consumers"""
        for topic in list(cls._consumers.keys()):
            cls.stop_consumer(topic)
    
    @classmethod
    def shutdown(cls):
        """Shutdown all Kafka connections"""
        cls._running = False
        cls.stop_all_consumers()
        
        if cls._producer:
            cls._producer.close()
            cls._producer = None
        
        logger.info("Kafka client manager shutdown complete")
    
    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        """Get status of Kafka connections"""
        return {
            'producer_connected': cls._producer is not None,
            'consumers_running': list(cls._consumers.keys()),
            'total_consumers': len(cls._consumers),
            'running': cls._running
        }
