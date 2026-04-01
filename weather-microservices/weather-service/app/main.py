# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportUnusedFunction=false, reportPossiblyUnboundVariable=false, reportConstantRedefinition=false
import logging
import os

from flask import Flask, jsonify, request
from prometheus_flask_exporter import PrometheusMetrics
from pythonjsonlogger import jsonlogger

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.flask import FlaskInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    OTEL_ENABLED = True
except Exception:
    OTEL_ENABLED = False

from app.core.use_cases import GetWeatherUseCase
from app.infrastructure.open_meteo_provider import OpenMeteoWeatherProvider
from app.infrastructure.rabbitmq_publisher import RabbitMQPublisher


def configure_logging() -> None:
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))
    root_logger.handlers = [handler]


def configure_tracing() -> None:
    if not OTEL_ENABLED:
        return
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")
    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: "weather-service"}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True)))
    trace.set_tracer_provider(provider)


def create_app() -> Flask:
    configure_logging()
    configure_tracing()

    app = Flask(__name__)
    PrometheusMetrics(app)
    if OTEL_ENABLED:
        FlaskInstrumentor().instrument_app(app)
        RequestsInstrumentor().instrument()

    use_case = GetWeatherUseCase(OpenMeteoWeatherProvider(), RabbitMQPublisher())

    @app.get("/")
    def index():
        return {
            "service": "weather-service",
            "message": "Use /weather?city=Istanbul or /health",
        }, 200

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "weather-service"}, 200

    @app.get("/weather")
    def weather():
        city = request.args.get("city", "Istanbul")
        notify_target = request.args.get("notify")
        try:
            weather_data = use_case.execute(city=city, notify_target=notify_target)
            return jsonify(weather_data.to_dict()), 200
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 404
        except Exception as exc:
            logging.exception("Unexpected error in weather endpoint")
            return jsonify({"error": str(exc)}), 500

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
