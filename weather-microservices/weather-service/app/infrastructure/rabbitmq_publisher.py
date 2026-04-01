import json
import logging
import os

import pika

from app.domain.ports import EventPublisher


class RabbitMQPublisher(EventPublisher):
    def __init__(self) -> None:
        self.host = os.getenv("RABBITMQ_HOST", "rabbitmq")
        self.queue_name = os.getenv("WEATHER_EVENTS_QUEUE", "weather.events")
        self.logger = logging.getLogger(__name__)

    def publish_weather_requested(self, payload: dict) -> None:
        connection = None
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host))
            channel = connection.channel()
            channel.queue_declare(queue=self.queue_name, durable=True)
            channel.basic_publish(
                exchange="",
                routing_key=self.queue_name,
                body=json.dumps(payload),
                properties=pika.BasicProperties(delivery_mode=2),
            )
        except Exception as exc:
            self.logger.warning("Weather event publish failed: %s", exc)
        finally:
            if connection and connection.is_open:
                connection.close()
