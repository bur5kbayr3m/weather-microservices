# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportUnusedFunction=false, reportPossiblyUnboundVariable=false, reportConstantRedefinition=false
import datetime
import os

import jwt
from flask import Flask, jsonify, request
from prometheus_flask_exporter import PrometheusMetrics

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.flask import FlaskInstrumentor
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    OTEL_ENABLED = True
except Exception:
    OTEL_ENABLED = False


JWT_SECRET = os.getenv("JWT_SECRET", "change-me")
DEMO_USER = os.getenv("DEMO_USER", "student")
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "student123")


def configure_tracing() -> None:
    if not OTEL_ENABLED:
        return
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")
    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: "auth-service"}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True)))
    trace.set_tracer_provider(provider)


def create_app() -> Flask:
    configure_tracing()
    app = Flask(__name__)
    PrometheusMetrics(app)
    if OTEL_ENABLED:
        FlaskInstrumentor().instrument_app(app)

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "auth-service"}, 200

    @app.post("/login")
    def login():
        payload = request.get_json(silent=True) or {}
        username = payload.get("username")
        password = payload.get("password")

        if username != DEMO_USER or password != DEMO_PASSWORD:
            return jsonify({"error": "invalid credentials"}), 401

        exp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
        token = jwt.encode({"sub": username, "role": "user", "exp": exp}, JWT_SECRET, algorithm="HS256")
        return jsonify({"access_token": token, "token_type": "bearer"}), 200

    @app.post("/verify")
    def verify():
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"valid": False, "reason": "missing bearer token"}), 401

        token = auth_header.split(" ", maxsplit=1)[1]
        try:
            decoded = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            return jsonify({"valid": True, "claims": decoded}), 200
        except jwt.ExpiredSignatureError:
            return jsonify({"valid": False, "reason": "token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"valid": False, "reason": "token invalid"}), 401

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
