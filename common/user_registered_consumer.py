import json
import logging

from django.conf import settings

from common.cache_service import cache_service
from common.email_service import send_welcome_email
from common.rabbitmq_service import rabbitmq_service

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3

def handle_user_registered(ch, method, properties, body):
    message = json.loads(body.decode("utf-8"))

    event_id = message.get("eventId")
    payload = message.get("payload", {})
    metadata = message.get("metadata", {})

    attempt = int(metadata.get("attempt", 1))

    cache_key = f"wp:events:processed:{event_id}"

    if cache_service.get(cache_key):
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return

    try:
        send_welcome_email(
            to_email=payload["email"],
            display_name=payload.get("displayName", payload["email"]),
            user_id=payload["userId"],
        )

        cache_service.set(cache_key, True, ttl=24 * 60 * 60)

        ch.basic_ack(delivery_tag=method.delivery_tag)
        logger.info(f"Welcome email sent for event {event_id}")

    except Exception as e:
        logger.error(f"Failed to process event {event_id}: {e}")

        if attempt >= MAX_ATTEMPTS:
            ch.basic_nack(
                delivery_tag=method.delivery_tag,
                requeue=False,
            )
            logger.error(f"Event {event_id} sent to DLQ")
            return

        message["metadata"]["attempt"] = attempt + 1

        rabbitmq_service.publish(
            routing_key="user.registered",
            payload=message,
        )

        ch.basic_ack(delivery_tag=method.delivery_tag)
        logger.warning(f"Event {event_id} retry {attempt + 1}")

def start_user_registered_consumer():
    rabbitmq_service.connect()

    channel = rabbitmq_service.channel

    channel.basic_qos(prefetch_count=1)

    channel.basic_consume(
        queue=settings.QUEUE_USER_REGISTERED,
        on_message_callback=handle_user_registered,
        auto_ack=False,
    )

    logger.info("User registered consumer started")
    channel.start_consuming()