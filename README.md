<div align="center">
  <h1>Automated Receipt Extraction & Expense Categorization Ecosystem</h1>
  <p><i>An asynchronous, microservice-driven backend architecture for financial metadata isolation 🧾✨</i></p>

  <p>
    <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
    <img src="https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi" alt="FastAPI"/>
    <img src="https://img.shields.io/badge/RabbitMQ-FF6600?style=for-the-badge&logo=rabbitmq&logoColor=white" alt="RabbitMQ"/>
    <img src="https://img.shields.io/badge/MinIO-C7202C?style=for-the-badge&logo=minio&logoColor=white" alt="MinIO"/>
    <img src="https://img.shields.io/badge/PyTorch-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white" alt="PyTorch"/>
    <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker"/>
    <img src="https://img.shields.io/badge/Jaeger-60DF9A?style=for-the-badge&logo=jaeger&logoColor=black" alt="Jaeger"/>
  </p>
</div>

> **Project Overview:** An asynchronous, microservice-driven backend architecture designed to ingest receipt images, perform optical character recognition (OCR), isolate financial metadata via an optimized LLM pipeline, and maintain an observable distributed tracing matrix.

---

## 📑 Table of Contents

- [🏗️ Architectural Overview & Component Topology](#%EF%B8%8F-architectural-overview--component-topology)
- [⚙️ Async Distributed Workflow Mechanics](#%EF%B8%8F-async-distributed-workflow-mechanics)
- [🔀 Inter-Service Communication Mechanisms](#-inter-service-communication-mechanisms)
- [🕸️ Network Communication & Isolation Policy Matrix](#%EF%B8%8F-network-communication--isolation-policy-matrix)
- [🔌 Port Allocation Framework](#-port-allocation-framework)
- [🔒 Zero Trust Network Policies & Isolation](#-zero-trust-network-policies--isolation)
- [📦 Component Directory & Deployment Specifications](#-component-directory--deployment-specifications)
- [🔭 Distributed Tracing with Jaeger](#-distributed-tracing-with-jaeger)
- [🚀 System Execution Blueprint](#-system-execution-blueprint)

---

## 🏗️ Architectural Overview & Component Topology

The system is engineered as an event-driven collection of isolated runtime environments interacting asynchronously through RabbitMQ and decoupled storage layers.

```text
              [ External HTTP Traffic ]
                          │
                          ▼
                 ┌──────────────────┐
                 │  Traefik Ingress │ (Port 8000)
                 └────────┬─────────┘
                          │ (Routing via PathPrefix)
                          ▼
                 ┌────────────────────┐ ◄──────── Reads Final Result ─────────┐
                 │  Gateway Service   │                                       │
                 └─┬─────────┬──────┬─┘                                       │
                   │         │      │ Publishes Upload Job                    │
      Writes Image │         │      ▼                                         │
                   ▼         │  [ RabbitMQ Broker ] ──────────────────────────┘
          ┌────────┴────────┐│    │               ▲  │ ◄── Publishes AI Result ─┐
          │  MinIO Storage  ││    │ Dispatches    │  │                          │
          └────────▲────────┘│    │ OCR Task      │  │ Dispatches Text Task     │
                   │         │    ▼               │  ▼                          │
                   │         │ ┌────────────────┐ │  ┌────────────────┐         │
                   └─────────┼─┤  OCR Worker    ├─┘  │ AI Categorizer ├─────────┘
                 Fetches     │ └───────┬────────┘    └───────┬────────┘
                 Image       │         │                     │
                             ▼         ▼                     ▼
         [================ OpenTelemetry Tracing Pipeline ================]
                                       │
                                       ▼
                                ┌─────────────┐
                                │   Jaeger    │ (UI Port 16686)
                                └─────────────┘
```


---

## ⚙️ Async Distributed Workflow Mechanics

Our architecture is split into primary application logic components and underlying structural infrastructure to ensure maximum scalability.

### 🧩 Primary Application Services

1. **Gateway Service (Ingestion Tier):** 
   * A FastAPI-based HTTP edge router. 
   * It acts as the primary interface for users, validating incoming receipt images, storing them securely, and tracking job statuses via in-memory dictionaries connected to RabbitMQ response queues.
2. **OCR Worker (Compute Tier):** 
   * A continuous, async background processor running PyTorch and EasyOCR. 
   * It connects directly to object storage to fetch uploaded receipts, extracts text mapped from pixels to string primitives, and pushes the raw text forward for AI parsing.
3. **AI Categorizer (Inference Tier):** 
   * A Python worker bridging into Large Language Models. 
   * It digests the raw text from the OCR worker, identifies financial fields (Merchants, Totals, Dates), maps them to user-defined expense categories, logs them to a Supabase database, and returns the final payload back to the Gateway.

### 🏛️ Structural Infrastructure

* **MinIO:** An S3-compatible object storage bucket acting as an immutable holding pen for high-volume binary images.
* **Traefik:** A dynamic reverse proxy that load-balances incoming web traffic and routes API calls securely without heavy manual configurations.
* **Jaeger:** A distributed tracing UI and OTLP collector that records milliseconds-level execution times across the entire network boundary using OpenTelemetry headers.

---

## 🔀 Inter-Service Communication Mechanisms

To ensure high availability and prevent process-blocking, this architecture utilizes distinct communication protocols across different network layers.

### 🚦 Traefik (Edge Gateway Routing)
* Acts as the single public entry point to the system, capturing traffic on an external port.
* Dynamically routes incoming web requests to the correct internal containers using Docker socket labels.
* Keeps internal databases and message brokers completely isolated and invisible to the public internet, mitigating massive security vulnerabilities.

### ⚡ FastAPI (Synchronous HTTP Layer)
* Powers the frontend edge-router (Gateway Service) to ingest external user requests and file payloads.
* Utilizes highly concurrent `async/await` patterns to validate receipt images and handle network I/O quickly.
* Instantly returns a "202 Accepted" response to the client while seamlessly passing the heavy lifting down the pipeline via broker messages.

### 🐇 RabbitMQ (Asynchronous Message Queues)
* Entirely decouples the fast HTTP ingestion process from the slow, compute-heavy GPU (OCR) and LLM processes.
* Utilizes highly durable, asynchronous message queues (`llm_task_queue`, `results_queue`) to pass context headers and tasks between microservices.
* Ensures strict fault tolerance—background workers consume tasks at their own safe pace, preventing server timeouts and guaranteeing zero dropped data during severe traffic spikes.

---

## 🕸️ Network Communication & Isolation Policy Matrix

Below is the structural validation blueprint representing connection vectors:

| Active Service | Outbound Connections ("Talks to") | Inbound Listeners ("Listens to") | Network Layer Vector |
| :--- | :--- | :--- | :--- |
| `traefik` | `gateway_service:8000` | External Host Boundary Requests | `public_net` |
| `rabbitmq` | None | `gateway_service`, `ocr_worker`, `ai_categorizer` | `gateway_net`, `ocr_net`, `ai_net` |
| `minio` | None | `gateway_service`, `ocr_worker` | `gateway_net`, `ocr_net` |
| `gateway_service` | `rabbitmq:5672`, `minio:9000`, `jaeger:4317` | `traefik_ingress` | `public_net`, `gateway_net`, `tracing_net` |
| `ocr_worker` | `rabbitmq:5672`, `minio:9000`, `jaeger:4317` | None | `ocr_net`, `tracing_net` |
| `ai_categorizer` | `rabbitmq:5672`, External LLM Endpoint, `jaeger:4317` | None | `ai_net`, `tracing_net` |
| `jaeger` | None | `gateway_service`, `ocr_worker`, `ai_categorizer` | `public_net`, `tracing_net` |

---

## 🔌 Port Allocation Framework

| Service Container Name | Internal Port | Exposed Host Port | Purpose / Functionality |
| :--- | :--- | :--- | :--- |
| `traefik_ingress` | `8000`, `8080` | `8000`, `8088` | HTTP Edge Router / Dashboard UI |
| `message_broker` | `5672`, `15672` | `None`, `${RABBITMQ_MANAGEMENT_PORT}` | AMQP Message Pipeline / Broker Management Portal |
| `minio_storage` | `9000`, `9001` | `${MINIO_API_PORT}`, `${MINIO_CONSOLE_PORT}` | S3-Compatible Object Store API / Storage Web Console |
| `gateway_service` | `8000` | `None` (Routed via Traefik)| HTTP Ingestion Engine Entrance API |
| `ocr_worker` | `None` | `None` | Continuous Asynchronous OCR Computation Processor |
| `ai_categorizer` | `None` | `None` | Asynchronous Natural Language Parsing Worker |
| `jaeger_tracing` | `4317`, `16686` | `4317`, `16686` | OTLP gRPC Span Ingestion Endpoint / Query Analytics Dashboard UI |

---

## 🔒 Zero Trust Network Policies & Isolation

To maximize architectural hardening and security, this environment heavily utilizes Docker's custom bridge networks to enforce a Zero Trust / Least Privilege communication policy. Containers are explicitly granted access only to the VLANs they require to function:

| Network Name | Accessibility Profile | Security Benefit |
| :--- | :--- | :--- |
| `public_net` | Traefik, Gateway, Jaeger | Isolates external routing. The internal workers are completely invisible to web traffic. |
| `gateway_net` | Gateway, MinIO, RabbitMQ | Allows the Gateway to store images and drop tasks, while hiding the message broker from the public web. |
| `ocr_net` | OCR Worker, MinIO, RabbitMQ | Allows the OCR layer to fetch images and read tasks. It intentionally lacks access to the public web and the AI engine. |
| `ai_net` | AI Categorizer, RabbitMQ | Prevents the AI worker from seeing MinIO storage. The AI engine only processes text and has no access to sensitive raw user image files. |
| `tracing_net` | All custom python services, Jaeger | A dedicated, hidden pipeline used solely for transmitting OpenTelemetry analytics without interfering with business logic traffic. |

*By segmenting connections, if the Gateway is ever compromised via the web API, the attacker still has zero direct network access to the AI Categorizer or the internal OCR engine.*

---

## 📦 Component Directory & Deployment Specifications

Every node operationalized inside this topology is defined within the active orchestration template according to specific structural parameters:

### Traefik Ingress (`traefik`)
```yaml
traefik:
  image: traefik:v3.0
  container_name: traefik_ingress
  command:
    - "--api.insecure=true"
    - "--providers.docker=true"
    - "--providers.docker.exposedbydefault=false"
    - "--entrypoints.web.address=:8000"
  ports:
    - "8000:8000"    
    - "8088:8080"    
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro
  networks:
    - public_net
```
* **Purpose:** Edge reverse proxy mapping internal rules to incoming connections.
* **Security:** Operates with `exposedbydefault=false` to enforce explicit, safe opt-in container routing via local tags.

### RabbitMQ Message Broker (`rabbitmq`)
```yaml
rabbitmq:
  image: rabbitmq:3-management
  container_name: message_broker
  ports:
    - "${RABBITMQ_MANAGEMENT_PORT}:15672"   
  networks:
    - gateway_net
    - ocr_net
    - ai_net
  healthcheck:
    test: ["CMD", "rabbitmq-diagnostics", "check_running"]
    interval: 10s
    timeout: 5s
    retries: 5
```
* **Purpose:** Orchestrates AMQP queues. 
* **Startup Order:** Shell directives force dependencies to wait until the broker is fully initialized and healthy.

### MinIO Storage Server (`minio`)
```yaml
minio:
  image: minio/minio
  container_name: minio_storage
  ports:
    - "${MINIO_API_PORT}:9000" 
    - "${MINIO_CONSOLE_PORT}:9001" 
  environment:
    - MINIO_ROOT_USER=${MINIO_ACCESS_KEY}
    - MINIO_ROOT_PASSWORD=${MINIO_SECRET_KEY}
  command: server /data --console-address ":9001"
  networks:
    - gateway_net
    - ocr_net
```
* **Purpose:** Ephemeral object store holding incoming receipt images before compute nodes request them.

### Ingestion Service Gateway (`gateway_service`)
```yaml
gateway_service:
  build: ./gateway_service
  container_name: gateway_service
  environment:
    - RABBITMQ_HOST=rabbitmq
    - MINIO_ENDPOINT=http://minio:9000
    - MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY}
    - MINIO_SECRET_KEY=${MINIO_SECRET_KEY}
    - OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
    - OTEL_SERVICE_NAME=gateway_service
  command: uvicorn main:app --host 0.0.0.0 --port 8000
  depends_on:
    rabbitmq:
      condition: service_healthy
  labels:
    - "traefik.enable=true"
    - "traefik.http.routers.gateway.rule=PathPrefix(\"/\")"
    - "traefik.http.services.gateway.loadbalancer.server.port=8000" 
    - "traefik.docker.network=public_net"
  networks:
    - public_net   
    - gateway_net  
    - tracing_net 
```
* **Traefik Binding:** Uses local docker labels (`PathPrefix("/")`) to inform Traefik how to link external traffic dynamically.

### OCR Compute Node (`ocr_worker`)
```yaml
ocr_worker:
  build: ./ocr_worker
  container_name: ocr_worker
  shm_size: '2gb'
  environment:
    - RABBITMQ_HOST=rabbitmq
    - MINIO_ENDPOINT=http://minio:9000
    - MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY}
    - MINIO_SECRET_KEY=${MINIO_SECRET_KEY}
    - OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
    - OTEL_SERVICE_NAME=ocr_worker
  command: python main.py
  depends_on:
    rabbitmq:
      condition: service_healthy
  networks:
    - ocr_net
    - tracing_net     
  volumes:
    - easyocr_cache:/root/.EasyOCR/model 
```
* **Hardware Ceiling:** Explicitly requests `shm_size: '2gb'` to avoid local container segmentation faults during PyTorch rendering.
* **Volume Persistence:** Caches heavy local AI detection models inside a named volume (`easyocr_cache`) to speed up server boots.

### AI Categorization Engine (`ai_categorizer`)
```yaml
ai_categorizer:
  build: ./ai_categorizer
  container_name: ai_categorizer
  environment:
    - RABBITMQ_HOST=rabbitmq
    - GROQ_API_KEY=${GROQ_API_KEY}
    - OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
    - OTEL_SERVICE_NAME=ai_categorizer
  command: python main.py
  depends_on:
    rabbitmq:
      condition: service_healthy
  networks:
    - ai_net
    - tracing_net       
```
* **Telemetry Setup:** Passes localized tracer endpoint environment variables to explicitly trace async pipeline calls in code.

### Jaeger Distributed Tracer (`jaeger`)
```yaml
jaeger:
  image: jaegertracing/all-in-one:latest
  container_name: jaeger_tracing
  ports:
    - "16686:16686" 
    - "4317:4317"   
  networks:
    - public_net    
    - tracing_net   
```
* **Purpose:** Provides a visual query interface for resolving OpenTelemetry context identifiers transmitted through the `tracing_net`.

---

## 🔭 Distributed Tracing with Jaeger

To maintain true observability across our decoupled, asynchronous network, we utilize **OpenTelemetry** combined with **Jaeger**. Since tasks are passed from an HTTP endpoint into a RabbitMQ queue, and later picked up by disconnected background workers, standard terminal logging is insufficient to track a request's lifecycle.

We solve this by extracting context IDs directly from RabbitMQ message headers. When a worker (like the AI Categorizer) picks up a task, it establishes a continuous trace and creates explicit, named spans for each major operation. This allows us to visualize the exact millisecond duration of LLM inference versus database insertions directly within the Jaeger UI.

Below is an example of how manual telemetry instrumentation is achieved in the AI Categorizer node (`main.py`):

```python
# Initialize manual OpenTelemetry pipeline
resource = Resource(attributes={"service.name": "ai_categorizer"})
provider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="http://jaeger:4317", insecure=True))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)

def process_agent_workflow(ch, method, properties, body):
    # 1. Extract context from incoming RabbitMQ headers to maintain trace continuity across microservices
    headers = properties.headers or {}
    parent_context = TraceContextTextMapPropagator().extract(carrier=headers)
    
    # 2. Start a master workflow block tracking span tied to the parent request
    with tracer.start_as_current_span("Categorize_Expense_Workflow", context=parent_context, kind=SpanKind.CONSUMER) as main_span:
        payload = json.loads(body)
        job_id = payload.get("job_id")
        main_span.set_attribute("job.id", job_id)

        # 3. Create an explicit sub-span dedicated specifically to LLM receipt extraction time
        with tracer.start_as_current_span("LLM_Metadata_Extraction") as extract_span:
            metadata = brain.extract_receipt_metadata(extracted_text)
            
        # ... processing ...
        
        # 4. Create an explicit sub-span tracking Supabase DB insertion network footprint
        with tracer.start_as_current_span("Supabase_Insert_Operation"):
            db_client.add_expense(job_id, date, merchant, amount, final_category)
```

---

## 🚀 System Execution Blueprint

Follow this structural deployment sequence to boot up the entire microservice ecosystem:

### Step 1: Initialize System Configuration Elements
Ensure a standard `.env` configuration file is properly written and sitting in your project root directory containing the required system variables:
```env
RABBITMQ_MANAGEMENT_PORT=15672
MINIO_API_PORT=9000
MINIO_CONSOLE_PORT=9001
MINIO_ACCESS_KEY=your_secure_access_key
MINIO_SECRET_KEY=your_secure_secret_key
```

### Step 2: Build the Core Microservices
To compile application logic frameworks, force-pull modern runtime stacks, and provision Python binaries, execute the following command:
```bash
docker compose build --no-cache
```

### Step 3: Launch the Infrastructure Matrix
Bring up all system containers in a detached background state:
```bash
docker compose up -d
```

### Step 4: Validate Active Orchestration Lifecycles
Verify that every microservice container node has established successful connections with its adjacent components:
```bash
# Verify overall status profiles
docker compose ps

# Monitor execution tracing output on the AI parsing engine
docker compose logs -f ai_categorizer
```

### Step 5: Interface and Dashboard Access
Once running, you can interact with the environment through the following local endpoints:
* **API Gateway Edge:** `http://localhost:8000/`
* **Jaeger Distributing Dashboard:** `http://localhost:16686/`
* **MinIO Console Dashboard:** `http://localhost:9001/`
* **RabbitMQ Portal Management:** `http://localhost:15672/`
