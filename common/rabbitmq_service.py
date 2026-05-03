import json
import logging
import pika

from django.conf import settings

logger = logging.getLogger(__name__)

class RabbitMQService:
    def __init__(self):
        self.connection = None
        self.channel = None

    def connect(self):
        credentials = pika.PlainCredentials(
            settings.RABBITMQ_USER,
            settings.RABBITMQ_PASS
        )

        parameters = pika.ConnectionParameters(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300,
        )

        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()

        self._declare_infrastructure()

        logger.info("RabbitMQ connected")

    def _declare_infrastructure(self):
        self.channel.exchange_declare(
            exchange=settings.RABBITMQ_EXCHANGE,
            exchange_type="direct",
            durable=True,
        )

        self.channel.exchange_declare(
            exchange=settings.RABBITMQ_DLX,
            exchange_type="direct",
            durable=True,
        )

        self.channel.queue_declare(
            queue=settings.QUEUE_USER_REGISTERED,
            durable=True,
            arguments={
                "x-dead-letter-exchange": settings.RABBITMQ_DLX,
                "x-dead-letter-routing-key": "user.registered",
            },
        )

        self.channel.queue_bind(
            queue=settings.QUEUE_USER_REGISTERED,
            exchange=settings.RABBITMQ_EXCHANGE,
            routing_key="user.registered",
        )

        self.channel.queue_declare(
            queue=f"{settings.QUEUE_USER_REGISTERED}.dlq",
            durable=True,
        )

        self.channel.queue_bind(
            queue=f"{settings.QUEUE_USER_REGISTERED}.dlq",
            exchange=settings.RABBITMQ_DLX,
            routing_key="user.registered",
        )

    def publish(self, routing_key: str, payload: dict):
        if not self.connection or self.connection.is_closed:
            self.connect()

        self.channel.basic_publish(
            exchange=settings.RABBITMQ_EXCHANGE,
            routing_key=routing_key,
            body=json.dumps(payload),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type="application/json",
            ),
        )

        logger.info(f"Event published to RabbitMQ: {routing_key}")

    def close(self):
        if self.connection and not self.connection.is_closed:
            self.connection.close()

rabbitmq_service = RabbitMQService()