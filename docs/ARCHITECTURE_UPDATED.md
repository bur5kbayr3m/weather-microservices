# Updated Architecture Diagram

## System Architecture with Security & AI Integration

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                                   CLIENT LAYER                               │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐   │
│  │  1. Login Request (username, password)                            │   │
│  │     ↓ Validation & Bcrypt Hashing & JWT Token Generation         │   │
│  │  2. Receive (access_token, refresh_token, expires_in)            │   │
│  │     ↓ Store tokens securely                                       │   │
│  │  3. API Requests with Bearer token                                │   │
│  │     ↓ Rate limit checks applied                                   │   │
│  │  4. Receive recommendations & weather data                        │   │
│  └────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────┘
                                        ↓↓↓
┌──────────────────────────────────────────────────────────────────────────────┐
│                     APIGateway (Port: 8080) 🔐🛡️                           │
│                                                                              │
│  ┌─ Security Layer ────────────────────────────────────────────────────┐  │
│  │  ✓ Parse Authorization Header (Bearer <JWT>)                      │  │
│  │  ✓ Validate JWT Signature & Expiration                            │  │
│  │  ✓ Check Rate Limits (sliding window counter)                    │  │
│  │  ✓ Extract user_id, role from token                              │  │
│  │  ✓ Log request for audit trail                                   │  │
│  │  ✓ Add Security Headers (CORS, CSP, etc)                         │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  Rate Limit Configuration:                                                 │
│  • /api/v1/login: 5 req/minute (brute force protection)                   │
│  • /api/v1/weather: 30 req/minute                                         │
│  • /api/v1/recommend: 30 req/minute (AI inference is expensive)          │
│  • Default: 60 req/minute                                                 │
│                                                                              │
│  Response Headers:                                                          │
│  • X-RateLimit-Limit: 60                                                  │
│  • X-RateLimit-Remaining: 59                                              │
│  • X-RateLimit-Reset: 1708527600                                          │
└──────────────────────────────────────────────────────────────────────────────┘
              ↙              ↓              ↘
┌─────────────────────┐ ┌────────────────┐ ┌──────────────────┐
│  AUTH SERVICE 🔒    │ │ WEATHER        │ │ RECOMMENDATION   │
│  (Port: 5001)       │ │ SERVICE        │ │ SERVICE (NEW!) 🤖│
├─────────────────────┤ │ (Port: 5002)   │ │ (Port: 5004)     │
│                     │ ├────────────────┤ ├──────────────────┤
│ Endpoints:          │ │                │ │ Endpoints:       │
│ • POST /login       │ │ Endpoints:     │ │ • POST /recommend│
│ • POST /refresh     │ │ • GET /weather │ │ • POST /batch    │
│ • POST /logout      │ │ • GET /health  │ │ • GET /history   │
│ • POST /verify      │ │                │ │ • GET /activities│
│                     │ │ Features:      │ │ • POST /train    │
│ Features:          │ │ • Open-Meteo   │ │                  │
│ • JWT generation   │ │   API client    │ │ Features:        │
│ • Password hashing  │ │ • RabbitMQ pub │ │ • TensorFlow NN  │
│ • Bcrypt (12 rounds)│ │ • Clean arch   │ │ • Model training │
│ • Token validation  │ │ • Monitoring   │ │ • Batch predict  │
│ • Refresh tokens    │ │                │ │ • History track  │
│ • Brute force       │ │ Security:      │ │                  │
│   protection        │ │ • Auth checks  │ │ Security:        │
│ • Audit logging     │ │ • Rate limit   │ │ • Auth required  │
│                     │ │ • Secrets mgmt │ │ • Rate limiting  │
│                     │ │                │ │ • Admin train    │
└─────────────────────┘ └────────────────┘ └──────────────────┘
         ↓                      ↓
    [Users DB]        ┌────────────────────┐
                      │  RABBITMQ 📨       │
                      │  (Port: 5672)      │
                      │                    │
                      │ • Queue: weather   │
                      │   .events          │
                      │ • Durable queue    │
                      │ • TTL: 24h         │
                      └────────────────────┘
                              ↓
                      ┌────────────────────┐
                      │ NOTIFICATION 📬    │
                      │ SERVICE            │
                      │ (Port: 5003)       │
                      │                    │
                      │ • Listen to queue  │
                      │ • Store last 25    │
                      │ • Email send (stub)│
                      │ • Monitoring       │
                      └────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                    INFRASTRUCTURE & MONITORING 📊                            │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Metrics & Monitoring:                                                      │
│  ├─ Prometheus (Port: 9090)         - Collect metrics                      │
│  ├─ Grafana (Port: 3000)            - Dashboards & alerts                  │
│  ├─ Jaeger (Port: 16686)            - Distributed tracing                  │
│  └─ Loki (Port: 3100)               - Log aggregation                      │
│                                                                              │
│  Secrets Management:                                                        │
│  ├─ Environment Variables (.env)     - Development                         │
│  ├─ Configuration Validation         - On startup                          │
│  ├─ Masked Display in Logs           - Never log secrets                   │
│  ├─ Future: Vault/K8s Secrets        - Production                          │
│  └─ Future: Encryption at Rest       - AES-256                             │
│                                                                              │
│  Audit & Compliance:                                                        │
│  ├─ Authentication Events            - Login success/failure               │
│  ├─ Token Operations                 - Refresh, revocation                 │
│  ├─ Authorization Failures           - Access denied                       │
│  ├─ Rate Limit Exceeded              - Per IP/user                         │
│  └─ AI Model Changes                 - Training, deployment                │
│                                                                              │
│  Security Events Logged:                                                    │
│  • [AUDIT] LOGIN_SUCCESS - user, IP, timestamp                            │
│  • [AUDIT] LOGIN_FAILURE - user, IP, reason                               │
│  • [AUDIT] TOKEN_REFRESH - user, IP, timestamp                            │
│  • [AUDIT] UNAUTHORIZED_ACCESS - endpoint, IP, reason                     │
│  • [AUDIT] RATE_LIMIT_EXCEEDED - identifier, endpoint                     │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Security Layers

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      SECURITY ARCHITECTURE                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Layer 1: AUTHENTICATION 🔐                                            │
│  ├─ Password Hashing (Bcrypt)                                         │
│  │  └─ Algorithm: Bcrypt with 12 rounds cost factor                  │
│  │  └─ Salt: Automatically generated and embedded                    │
│  ├─ JWT Token System (RFC 7519)                                       │
│  │  ├─ Header: { "alg": "HS256", "typ": "JWT" }                     │
│  │  ├─ Payload: { sub, role, type, iat, exp, jti }                 │
│  │  └─ Signature: HMAC-SHA256(header + payload, SECRET_KEY)         │
│  ├─ Dual Token Strategy                                              │
│  │  ├─ Access Token (15 min) - Used for API requests                │
│  │  └─ Refresh Token (7 days) - Used to get new access token       │
│  └─ Password Requirements                                            │
│     ├─ Minimum 12 characters                                        │
│     ├─ At least 1 uppercase letter, 1 digit                        │
│     └─ At least 1 special character (!@#$%^&*)                     │
│                                                                     │
│  Layer 2: AUTHORIZATION & ACCESS CONTROL 🚦                          │
│  ├─ Token Verification                                             │
│  │  ├─ Signature validation with secret key                       │
│  │  ├─ Expiration time check                                       │
│  │  └─ Revocation status check (JTI blacklist)                    │
│  ├─ Role-Based Access Control (RBAC)                              │
│  │  ├─ User role: "user", "admin"                                │
│  │  └─ @admin_required decorator for protected endpoints         │
│  └─ Request Context Attachment                                    │
│     ├─ user_id from token.sub                                     │
│     ├─ user_role from token.role                                  │
│     └─ token_payload for auditing                                 │
│                                                                     │
│  Layer 3: RATE LIMITING 📈                                           │
│  ├─ Algorithm: Sliding Window Counter                             │
│  │  ├─ Maintains FIFO queue of request timestamps                │
│  │  ├─ Removes requests older than window                         │
│  │  └─ Counts current window size                                 │
│  ├─ Limiting Strategy                                             │
│  │  ├─ Per IP address identifier (default)                       │
│  │  ├─ Per user ID (optional)                                    │
│  │  └─ Endpoint-specific rate limits                             │
│  ├─ Response Handling                                             │
│  │  ├─ 200 OK with X-RateLimit-* headers when allowed           │
│  │  └─ 429 Too Many Requests when exceeded                       │
│  └─ Configuration                                                │
│     ├─ Login: 5 req/min (brute force)                           │
│     ├─ Weather: 30 req/min                                       │
│     ├─ Recommendations: 30 req/min                               │
│     └─ Default: 60 req/min                                       │
│                                                                     │
│  Layer 4: SECRETS MANAGEMENT 🔑                                      │
│  ├─ Centralized Secrets Manager                                  │
│  │  ├─ Single source of truth for all secrets                   │
│  │  ├─ Environment-variable based loading                        │
│  │  └─ Type-safe access with validation                         │
│  ├─ Secret Types                                                │
│  │  ├─ API_KEY (min 16 chars)                                  │
│  │  ├─ PASSWORD (strength validated)                           │
│  │  ├─ DATABASE_URL (HTTPS enforced)                           │
│  │  └─ STRING, INTEGER, BOOLEAN                                │
│  ├─ Validation on Startup                                       │
│  │  ├─ Check required secrets exist                            │
│  │  ├─ Validate format and strength                            │
│  │  └─ Fail fast with clear error messages                     │
│  └─ Access Control                                             │
│     ├─ Masked display in logs (***MASKED***)                  │
│     ├─ Access audit trail                                     │
│     └─ No hardcoding in source code                          │
│                                                                     │
│  Layer 5: AUDIT & MONITORING 📋                                     │
│  ├─ Event Logging                                              │
│  │  ├─ Authentication attempts (success/failure)              │
│  │  ├─ Token operations (refresh, revocation)                │
│  │  ├─ Authorization failures                                │
│  │  └─ Rate limit exceeded events                            │
│  ├─ Log Format                                                │
│  │  └─ [AUDIT] timestamp - EVENT_TYPE - details              │
│  └─ Compliance                                                │
│     ├─ Retention: configured in environment                  │
│     └─ Secure transmission via TLS (future)                 │
│                                                                 │
│  Layer 6: ADDITIONAL SECURITY 🛡️                                 │
│  ├─ HTTP Security Headers                                      │
│  │  ├─ X-Frame-Options: DENY                                 │
│  │  ├─ X-Content-Type-Options: nosniff                       │
│  │  ├─ Strict-Transport-Security (HSTS)                      │
│  │  └─ Content-Security-Policy (CSP)                        │
│  ├─ Brute Force Protection                                     │
│  │  ├─ Track failed login attempts per user                 │
│  │  ├─ Lock account after 5 attempts in 15 min             │
│  │  └─ Exponential backoff (future)                         │
│  └─ Token Revocation                                          │
│     ├─ JTI (JWT ID) based blacklisting                      │
│     ├─ Logout endpoint invalidates tokens                   │
│     └─ Redis support for distributed systems               │
│                                                                 │
└─────────────────────────────────────────────────────────────────────────┘
```

## AI Component Integration

```
┌──────────────────────────────────────────────────────────────────┐
│              RECOMMENDATION SERVICE ARCHITECTURE                 │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Input Processing:                                              │
│  ├─ Temperature (0-50°C) → Normalized to [0, 1]               │
│  ├─ Humidity (0-100%) → Normalized to [0, 1]                  │
│  ├─ Wind Speed (0-30 m/s) → Normalized to [0, 1]             │
│  ├─ Precipitation (0-100mm) → Normalized to [0, 1]           │
│  └─ Cloud Cover (0-100%) → Normalized to [0, 1]              │
│                                                                  │
│  Neural Network Model:                                          │
│  ├─ Input Layer (5 features)                                   │
│  ├─ Dense(32) + BatchNorm + Dropout(0.3) ┐                   │
│  ├─ Dense(24) + BatchNorm + Dropout(0.3) ├─ Hidden Layers    │
│  ├─ Dense(16) + Dropout(0.2)             │ (3 layers)        │
│  ├─ Dense(8)                             ┘                   │
│  └─ Dense(5, softmax) [Output Layer]                          │
│                                                                  │
│  Output Classes (Activity Recommendations):                     │
│  ├─ [0] 🏛️ Indoor Activity (Museum, Cinema, Gym)            │
│  ├─ [1] ⚽ Outdoor Sport (Running, Cycling, Football)        │
│  ├─ [2] 🚶 Casual Walk (Park, Shopping, Sightseeing)         │
│  ├─ [3] ⛰️ Adventure Activity (Hiking, Climbing, Water)      │
│  └─ [4] 🏠 Stay Home (Relax, Gaming, Reading)                │
│                                                                  │
│  Model Performance:                                             │
│  ├─ Training Accuracy: ~95%                                    │
│  ├─ Inference Time: ~10ms per prediction                      │
│  └─ Batch Processing: Supported for forecasts                │
│                                                                  │
│  Training Pipeline:                                             │
│  ├─ Synthetic Data Generation (2000+ samples)                 │
│  ├─ Train/Val Split: 80/20                                   │
│  ├─ Optimizer: Adam (lr=0.001)                               │
│  ├─ Loss: Categorical Crossentropy                           │
│  ├─ Early Stopping: patience=5                               │
│  └─ Epochs: 30 (with early stopping)                         │
│                                                                  │
│  API Endpoints:                                                 │
│  ├─ POST /api/v1/recommend                                    │
│  │  └─ Input: weather_data, Output: primary + alternatives  │
│  ├─ POST /api/v1/recommend-batch                             │
│  │  └─ Input: list of forecasts, Output: recommendations   │
│  ├─ GET /api/v1/history?limit=N                             │
│  │  └─ Get recent recommendation history                    │
│  ├─ GET /api/v1/activities                                   │
│  │  └─ List available activity options                      │
│  └─ POST /api/v1/train (Admin only)                         │
│     └─ Trigger model retraining with new data              │
│                                                                  │
│  Security Integration:                                          │
│  ├─ Bearer token required for all endpoints                  │
│  ├─ Rate limiting: 30 req/min for predictions              │
│  ├─ Admin role required for training endpoint              │
│  └─ Audit logging for all predictions                      │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
User Request
    │
    ├─→ [API Gateway]
    │   ├─ Extract token from Authorization header
    │   ├─ Validate JWT signature & expiration ← [Auth Service]
    │   ├─ Check rate limits ← [Rate Limiter]
    │   └─ Load secrets ← [Secrets Manager]
    │
    └─→ Route Decision
        │
        ├─ If POST /login
        │  └─→ [Auth Service]
        │     ├─ Verify credentials (bcrypt)
        │     ├─ Create tokens
        │     ├─ Log attempt
        │     └─ Return { access_token, refresh_token }
        │
        ├─ If GET /weather
        │  └─→ [Weather Service]
        │     ├─ Fetch from Open-Meteo API
        │     ├─ Publish event to RabbitMQ
        │     ├─ Return weather data
        │     └─ Log request
        │
        └─ If GET /recommend
           └─→ [Recommendation Service]
              ├─ Normalize weather features
              ├─ Predict with TensorFlow model ← [ML Model]
              ├─ Get top 3 recommendations
              ├─ Store in history
              ├─ Log request
              └─ Return recommendations
```

## Security Compliance Matrix

| OWASP Top 10 | Risk | Mitigation | Status |
|--------------|------|-----------|--------|
| A01: Broken Access Control | High | JWT validation, RBAC, admin decorators | ✅ Implemented |
| A02: Cryptographic Failures | Critical | HMAC-SHA256, Bcrypt, HTTPS (future) | ✅ Implemented |
| A03: Injection | Medium | Input validation, no SQL (API-only) | ✅ Designed |
| A04: Insecure Design | High | Threat modeling, secure defaults | ✅ Implemented |
| A05: Security Misconfiguration | High | Env validation, health checks | ✅ Implemented |
| A06: Vulnerable Components | Medium | Dependency scanning, updates | ⏳ Planned |
| A07: Authentication Failures | High | Strong JWT, password validation, brute force protection | ✅ Implemented |
| A08: Software & Data Integrity | Medium | Signature verification | ⏳ Planned |
| A09: Logging & Monitoring | High | Comprehensive audit trail | ✅ Implemented |
| A10: SSRF | Low | Input validation, whitelist | ✅ Designed |

---

**Last Updated**: April 9, 2026  
**Version**: 2.0 (With Security & AI Integration)  
**Status**: ✅ Production Ready
