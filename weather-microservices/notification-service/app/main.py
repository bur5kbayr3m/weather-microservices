# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportUnusedFunction=false, reportUnusedVariable=false
import json
import logging
import os
import threading
import time

import pika
from flask import Flask, jsonify
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_flask_exporter import PrometheusMetrics
from pythonjsonlogger import jsonlogger


recent_notifications: list[dict[str, object]] = []


def configure_logging() -> None:
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))
    root_logger.handlers = [handler]


def configure_tracing() -> None:
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")
    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: "notification-service"}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True)))
    trace.set_tracer_provider(provider)


def consume_events() -> None:
    logger = logging.getLogger(__name__)
    host = os.getenv("RABBITMQ_HOST", "rabbitmq")
    queue_name = os.getenv("WEATHER_EVENTS_QUEUE", "weather.events")

    while True:
        connection = None
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=host))
            channel = connection.channel()
            channel.queue_declare(queue=queue_name, durable=True)

            for method_frame, properties, body in channel.consume(queue=queue_name, inactivity_timeout=1):
                if body is None:
                    continue
                payload = json.loads(body.decode("utf-8"))
                recent_notifications.append(payload)
                if len(recent_notifications) > 25:
                    recent_notifications.pop(0)
                logger.info("Notification event processed", extra={"payload": payload})
                channel.basic_ack(delivery_tag=method_frame.delivery_tag)
        except Exception as exc:
            logger.warning("Notification consumer reconnecting due to: %s", exc)
            time.sleep(2)
        finally:
            if connection and connection.is_open:
                connection.close()


def create_app() -> Flask:
    configure_logging()
    configure_tracing()

    app = Flask(__name__)
    PrometheusMetrics(app)
    FlaskInstrumentor().instrument_app(app)

    if os.getenv("DISABLE_CONSUMER", "false").lower() != "true":
        worker = threading.Thread(target=consume_events, daemon=True)
        worker.start()

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "notification-service"}, 200

    @app.get("/notifications")
    def notifications():
        return jsonify({"items": recent_notifications}), 200

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
