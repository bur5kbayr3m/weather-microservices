# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportUnusedFunction=false, reportPossiblyUnboundVariable=false, reportConstantRedefinition=false
import os

import requests
from flask import Flask, jsonify, render_template, request
from prometheus_flask_exporter import PrometheusMetrics
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

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


# Local-first defaults make manual Flask startup work without Docker.
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://127.0.0.1:5001")
WEATHER_SERVICE_URL = os.getenv("WEATHER_SERVICE_URL", "http://127.0.0.1:5002")
RECOMMENDATION_SERVICE_URL = os.getenv("RECOMMENDATION_SERVICE_URL", "http://127.0.0.1:5004")


def json_or_text(resp: requests.Response):
    try:
        return resp.json()
    except ValueError:
        return {"raw": resp.text}


def configure_tracing() -> None:
    if not OTEL_ENABLED:
        return
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")
    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: "api-gateway"}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True)))
    trace.set_tracer_provider(provider)


def create_retry_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=0.3, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    return session


def create_app() -> Flask:
    configure_tracing()
    app = Flask(__name__)
    PrometheusMetrics(app)
    if OTEL_ENABLED:
        FlaskInstrumentor().instrument_app(app)
        RequestsInstrumentor().instrument()

    session = create_retry_session()

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "api-gateway"}, 200

    @app.get("/")
    def index() -> str:
        return render_template("index.html")

    @app.post("/api/v1/login")
    def login():
        try:
            upstream_response = session.post(
                f"{AUTH_SERVICE_URL}/login", json=request.get_json(silent=True) or {}, timeout=5
            )
        except requests.RequestException as exc:
            return jsonify({"error": "auth service unavailable", "details": str(exc)}), 503

        return jsonify(json_or_text(upstream_response)), upstream_response.status_code

    @app.get("/api/v1/weather")
    def get_weather():
        auth_header = request.headers.get("Authorization", "")

        try:
            verify_response = session.post(
                f"{AUTH_SERVICE_URL}/verify", headers={"Authorization": auth_header}, timeout=5
            )
        except requests.RequestException as exc:
            return jsonify({"error": "auth service unavailable", "details": str(exc)}), 503

        if verify_response.status_code != 200:
            return jsonify({"error": "unauthorized", "details": json_or_text(verify_response)}), 401

        city = request.args.get("city", "Istanbul")
        notify_target = request.args.get("notify")
        try:
            upstream_response = session.get(
                f"{WEATHER_SERVICE_URL}/weather",
                params={"city": city, "notify": notify_target},
                timeout=10,
            )
        except requests.RequestException as exc:
            return jsonify({"error": "weather service unavailable", "details": str(exc)}), 503

        weather_data = json_or_text(upstream_response)
        if upstream_response.status_code >= 400:
            return jsonify(weather_data), upstream_response.status_code

        outfit_payload = None
        try:
            outfit_response = session.post(
                f"{RECOMMENDATION_SERVICE_URL}/api/v1/outfit",
                json=weather_data,
                timeout=10,
            )
            if outfit_response.status_code == 200:
                outfit_payload = outfit_response.json()
        except Exception:
            outfit_payload = None

        combined_response = dict(weather_data)
        if outfit_payload:
            combined_response["outfit_recommendation"] = outfit_payload

        return jsonify(combined_response), upstream_response.status_code

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
