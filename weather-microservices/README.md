# Weather Microservices Project (Flask)

Bu proje, girilen konuma gore hava durumu gosteren web tabanli Flask mikroservis sistemidir.

## Neler Var?

- Clean Architecture yaklasimi (weather-service katmanli)
- REST API tasarimi
- API Gateway deseni
- Auth Service (JWT)
- Service-to-service iletisim:
  - Senkron REST (Gateway -> Auth/Weather)
  - Asenkron mesajlasma (Weather -> Notification, RabbitMQ)
- Docker Compose ile container orchestration
- CI/CD pipeline (GitHub Actions)
- Otomatik testler (pytest)
- Observability:
  - Metrics: Prometheus
  - Dashboard: Grafana
  - Distributed tracing: OpenTelemetry + Jaeger
  - Centralized logging: Loki + Promtail
- Health checks ve temel failure handling (retry + queue durability)

## Mimari

Mimari diyagram: [docs/architecture.md](docs/architecture.md)
API dokumani: [docs/api.md](docs/api.md)

## Hizli Baslangic

1. Ortam degiskenlerini hazirla:

```powershell
Copy-Item .env.example .env
```

2. Sistemi ayağa kaldir:

```powershell
docker compose up --build
```

3. Giris token'i al:

```powershell
$body = '{"username":"student","password":"student123"}'
$login = Invoke-RestMethod -Method Post -Uri http://localhost:8080/api/v1/login -Body $body -ContentType "application/json"
$token = $login.access_token
```

4. Hava durumunu ve kombin onerilerini sorgula (internetten Open-Meteo verisi ceker):

```powershell
Invoke-RestMethod -Method Get -Uri "http://localhost:8080/api/v1/weather?city=Istanbul&notify=ogrenci@example.com" -Headers @{ Authorization = "Bearer $token" }
```

Bu istegin cevabinda `outfit_recommendation` alanı da doner; renkler, kiyafet parcasi ve havaya uygun stil notu icerdir.

## Arayuzler

- API Gateway: http://localhost:8080
- RabbitMQ UI: http://localhost:15672
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)
- Jaeger: http://localhost:16686

## Temel Endpointler

- `POST /api/v1/login`
- `GET /api/v1/weather?city=<name>&notify=<target>`
- `GET /health` (tum servislerde)
- `GET /notifications` (notification-service)

## CI/CD

Pipeline dosyasi: [.github/workflows/ci-cd.yml](.github/workflows/ci-cd.yml)

Asamalar:
1. Her servis icin test
2. Docker image build
3. Compose validasyonu
4. (Opsiyonel) Kubernetes deploy

## Kubernetes Deploy

Manifest: [deploy/k8s/weather-stack.yaml](deploy/k8s/weather-stack.yaml)

```bash
kubectl apply -f deploy/k8s/weather-stack.yaml
```

## Guvenlik Notlari

- JWT secret degeri `.env` ile yonetilir.
- Prod ortaminda secrets manager kullanilmalidir.
- Demo kullanici kimlik bilgileri sadece egitim amaclidir.

## Reliability Report (Ozet)

- API Gateway tarafinda upstream cagrilar icin retry mevcut.
- RabbitMQ kuyruklari durable oldugu icin event kaybi riski azalir.
- Her serviste `/health` endpointi var.
- Merkezi log + metric + trace ile ariza tespiti hizlanir.
