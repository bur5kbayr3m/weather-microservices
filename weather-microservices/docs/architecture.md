# Architecture Diagram

```mermaid
flowchart LR
  Client[Web Client / Browser] --> Gateway[API Gateway Flask]
  Gateway --> Auth[Auth Service Flask]
  Gateway --> Weather[Weather Service Flask]
  Weather --> OpenMeteo[Open-Meteo API]
  Weather --> Rabbit[(RabbitMQ)]
  Rabbit --> Notify[Notification Service Flask]

  Gateway --> OTel[OpenTelemetry Collector]
  Auth --> OTel
  Weather --> OTel
  Notify --> OTel
  OTel --> Jaeger[Jaeger Trace UI]

  Gateway --> Prom[Prometheus]
  Auth --> Prom
  Weather --> Prom
  Notify --> Prom
  Prom --> Grafana[Grafana Dashboards]

  Gateway -. logs .-> Promtail[Promtail]
  Auth -. logs .-> Promtail
  Weather -. logs .-> Promtail
  Notify -. logs .-> Promtail
  Promtail --> Loki[Loki]
  Loki --> Grafana
```

## Communication Design

- Synchronous: API Gateway -> Auth Service and Weather Service via REST.
- Asynchronous: Weather Service -> Notification Service via RabbitMQ queue `weather.events`.
- Security: JWT-based authentication and token verification via Auth Service.
- Fault tolerance: retry strategy in API Gateway; queue durability in RabbitMQ.
