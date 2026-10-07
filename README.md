# 🎓 Bulk Certificate Generator Backend API

An enterprise-ready, high-throughput backend service built with **Python 3.11**, **FastAPI**, **SQLAlchemy**, and **ReportLab**. Designed to accept bulk certificate generation requests, validate recipient data, asynchronously render vector PDF certificates from a predefined template, track processing status in real time, and provide secure retrieval and verification endpoints.

---

## 📑 Table of Contents
- [System Architecture](#system-architecture)
- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [Running the Application](#running-the-application)
- [Running Tests](#running-tests)
- [API Documentation & Usage Guide](#api-documentation--usage-guide)
  - [1. Submit a Bulk Generation Job](#1-submit-a-bulk-generation-job)
  - [2. Track Job Progress and Status](#2-track-job-progress-and-status)
  - [3. List Paginated Job Items & Filter Failures](#3-list-paginated-job-items--filter-failures)
  - [4. Download an Individual Certificate PDF](#4-download-an-individual-certificate-pdf)
  - [5. Bulk Download All Certificates as ZIP](#5-bulk-download-all-certificates-as-zip)
  - [6. Public Certificate Verification](#6-public-certificate-verification)
- [Design & Implementation Decisions](#design--implementation-decisions)
  - [1. Asynchronous Background Processing](#1-asynchronous-background-processing)
  - [2. Fault Isolation & Resiliency](#2-fault-isolation--resiliency)
  - [3. Predefined Template Engine: ReportLab Vector PDFs](#3-predefined-template-engine-reportlab-vector-pdfs)
  - [4. Cryptographic Integrity & Scannable QR Codes](#4-cryptographic-integrity--scannable-qr-codes)
  - [5. Relational Database Modeling](#5-relational-database-modeling)
  - [6. Production Scaling Roadmap](#6-production-scaling-roadmap)
- [Interview Defense & FAQs](#interview-defense--faqs)

---

## 🏛 System Architecture

```mermaid
flowchart TD
    Client([Client / Frontend / External System])

    subgraph API_Layer ["FastAPI Application (ASGI)"]
        Router["/api/v1/certificates"]
        Validator["Pydantic v2 Validator"]
        Docs["Interactive Docs (/docs & /redoc)"]
    end

    subgraph Processing_Engine ["Background Execution Engine"]
        BG["FastAPI BackgroundTasks Worker"]
        JobProc["Job Processor (Isolation Loop)"]
        CertGen["ReportLab PDF Generator + QR Engine"]
    end

    subgraph Storage_And_DB ["Persistence Layer"]
        DB[(Relational DB: SQLite / PostgreSQL)]
        DiskStore[("Storage Disk: storage/certificates/*.pdf")]
    end

    Client -- "1. POST /jobs (bulk payload)" --> Router
    Router -- "2. Validate request" --> Validator
    Validator -- "3. Save Job (PENDING)" --> DB
    Router -- "4. Returns 202 Accepted (job_id)" --> Client
    Router -- "5. Dispatches async job" --> BG
    BG --> JobProc
    JobProc -- "6. Loops through recipients" --> CertGen
    CertGen -- "7. Renders Vector PDF + QR" --> DiskStore
    JobProc -- "8. Updates item & job metrics" --> DB
    Client -- "9. GET /jobs/{id} (Poll progress)" --> Router
    Client -- "10. GET /download & /download-all" --> Router
    Router -- "11. Streams PDF / ZIP bundle" --> Client
```

---

## ✨ Key Features

1. **Bulk Request Handling**: Submit up to 1,000 recipients in a single API call without connection timeouts.
2. **Fault Isolation**: If generation fails for one recipient (malformed data, bad metadata, or edge case), the system records the item-level error message and continues generating certificates for all remaining valid recipients.
3. **Multi-State Job Tracking**: Real-time monitoring with percentage progress, processed counts, and explicit status states: `PENDING`, `PROCESSING`, `COMPLETED`, `PARTIAL_SUCCESS`, and `FAILED`.
4. **Predefined Executive Certificate Template**: Hand-crafted vector graphics utilizing ReportLab with midnight-navy and warm-gold double borders, issuer headers, recipient typography, custom metadata, and formal signature blocks.
5. **Scannable QR Verification & SHA-256 Hashes**: Every certificate embeds a scannable QR code directing to a public verification endpoint, backed by SHA-256 cryptographic file hashing for anti-tamper authenticity.
6. **Flexible Retrieval**: Retrieve individual certificates as PDFs, inspect itemized errors, or download the entire batch in a compressed `.zip` archive.
7. **Comprehensive Test Suite**: 22 automated tests covering end-to-end job creation, input validation, template rendering, failure isolation, download streaming, and verification with **95% code coverage**.

---

## 🛠 Technology Stack

| Component | Technology | Rationale |
| :--- | :--- | :--- |
| **Language** | Python 3.11+ | Modern type annotations, performance optimizations. |
| **Framework** | FastAPI 0.110+ | High-performance ASGI framework with automatic OpenAPI documentation. |
| **Validation** | Pydantic v2 | High-speed C-based data validation and strict schema enforcement. |
| **ORM & Database** | SQLAlchemy 2.0+ (SQLite / PostgreSQL) | Decoupled relational persistence supporting multiple backends. |
| **PDF Generation** | ReportLab 5.0+ | Fast, deterministic vector PDF generation without headless browser bloat. |
| **QR Code Engine** | QRCode + Pillow | Dynamic QR code generation for digital credential verification. |
| **Testing** | Pytest + Pytest-Cov + HTTPX | Automated unit, integration, and regression testing. |

---

## 📁 Project Structure

```text
bulk_certificate_generator/
├── app/
│   ├── __init__.py
│   ├── config.py                 # Pydantic BaseSettings (env configuration)
│   ├── database.py               # SQLAlchemy engine, session maker, DB dependency
│   ├── models.py                 # ORM models (CertificateJob, JobItem, Certificate)
│   ├── schemas.py                # Pydantic request, response, and validation schemas
│   ├── main.py                   # FastAPI application factory, lifespan, CORS
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── routes.py         # REST endpoints (Jobs, Items, Downloads, Verification)
│   └── services/
│       ├── __init__.py
│       ├── certificate_service.py # ReportLab PDF generator with borders, seal, QR
│       └── job_processor.py       # Asynchronous worker with fault-isolation loop
├── storage/
│   └── certificates/             # Storage folder for generated PDF assets
├── tests/
│   ├── __init__.py
│   ├── conftest.py               # TestClient, in-memory DB & temp storage fixtures
│   ├── test_jobs.py              # Job creation and status polling tests
│   ├── test_validation.py        # Pydantic input validation tests
│   ├── test_generation.py        # PDF engine & cryptographic integrity tests
│   ├── test_failure_handling.py  # Fault isolation & partial success tests
│   ├── test_retrieval.py         # Download PDF, download ZIP, and verify tests
│   └── test_main.py              # Root and health check tests
├── sample_request.json           # Ready-to-use sample bulk request
├── requirements.txt              # Production and testing dependencies
├── pytest.ini                    # Pytest test discovery configuration
├── run.py                        # Local runner script
├── .env.example                  # Environment configuration template
├── .gitignore                    # Git ignore file
└── README.md                     # Complete project documentation
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11 or higher
- `pip` (Python package installer)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Sachinshekhar82/Bulk-Certificate-Generator-.git
   cd Bulk-Certificate-Generator-
   ```

2. **Create and activate a virtual environment**:
   ```bash
   # Windows (PowerShell)
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Configuration
Copy `.env.example` to `.env` (or use built-in defaults):
```bash
cp .env.example .env
```

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `sqlite:///./certificates.db` | Database connection string. For PostgreSQL: `postgresql://user:pass@localhost:5432/certdb` |
| `STORAGE_DIR` | `storage/certificates` | Target directory for generated PDF files. |
| `BASE_URL` | `http://localhost:8000` | Host URL embedded into certificate QR codes for online verification. |
| `MAX_BATCH_SIZE` | `1000` | Maximum recipients permitted in a single request. |

### Running the Application

Start the server using `uvicorn`:
```bash
python run.py
```
Or directly via the CLI:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The server will initialize the SQLite schema and start listening at:
- **API Base URL**: `http://localhost:8000`
- **Interactive Swagger UI**: `http://localhost:8000/docs`
- **Alternative ReDoc UI**: `http://localhost:8000/redoc`
- **Health Check**: `http://localhost:8000/health`

---

## 🧪 Running Tests

The test suite provides comprehensive coverage of all requirements, edge cases, error conditions, and cryptographic integrity.

Run the full test suite with verbose output:
```bash
pytest -v
```

Run tests with test coverage reporting:
```bash
pytest --cov=app --cov-report=term-missing
```

### Coverage Report Summary
```text
Name                                  Stmts   Miss  Cover   Missing
-------------------------------------------------------------------
app\__init__.py                           1      0   100%
app\api\__init__.py                       0      0   100%
app\api\v1\__init__.py                    0      0   100%
app\api\v1\routes.py                     93      6    94%   
app\config.py                            23      0   100%
app\database.py                          16      4    75%   
app\main.py                              23      0   100%
app\models.py                            67      0   100%
app\schemas.py                           93      1    99%   
app\services\__init__.py                  0      0   100%
app\services\certificate_service.py     146      2    99%   
app\services\job_processor.py            66     14    79%   
-------------------------------------------------------------------
TOTAL                                   528     27    95%
======================== 22 passed in 1.72s ========================
```

---

## 📡 API Documentation & Usage Guide

### 1. Submit a Bulk Generation Job
Submits a batch of recipients with event and issuing credentials. Returns `202 Accepted` immediately with the unique job ID and tracking link.

- **Endpoint**: `POST /api/v1/certificates/jobs`
- **Status Code**: `202 Accepted`

#### Example Request (`curl`):
```bash
curl -X POST "http://localhost:8000/api/v1/certificates/jobs" \
     -H "Content-Type: application/json" \
     -d '{
       "event_name": "Full Stack & Cloud Architecture Masterclass",
       "issuer_name": "Aereo Engineering Academy",
       "issue_date": "2026-10-07",
       "template_title": "Certificate of Excellence",
       "description": "for exceptional performance and successful graduation",
       "recipients": [
         {
           "name": "Sachin Shekhar",
           "email": "sachin@example.com",
           "metadata": { "grade": "Distinction", "score": "98%" }
         },
         {
           "name": "Jane Doe",
           "email": "jane.doe@example.com",
           "metadata": { "grade": "First Class", "score": "92%" }
         }
       ]
     }'
```

#### Example Response (`202 Accepted`):
```json
{
  "id": "e89cb21a-a123-4f90-880c-982736154d89",
  "event_name": "Full Stack & Cloud Architecture Masterclass",
  "issuer_name": "Aereo Engineering Academy",
  "issue_date": "2026-10-07",
  "template_title": "Certificate of Excellence",
  "description": "for exceptional performance and successful graduation",
  "status": "PENDING",
  "total_count": 2,
  "processed_count": 0,
  "success_count": 0,
  "failed_count": 0,
  "progress_percentage": 0.0,
  "created_at": "2026-10-07T07:45:00.000Z",
  "updated_at": "2026-10-07T07:45:00.000Z",
  "completed_at": null,
  "status_url": "http://localhost:8000/api/v1/certificates/jobs/e89cb21a-a123-4f90-880c-982736154d89",
  "download_all_url": null
}
```

---

### 2. Track Job Progress and Status
Allows clients to poll the real-time status, processing percentage, and item breakdown of a submitted job.

- **Endpoint**: `GET /api/v1/certificates/jobs/{job_id}`
- **Status Code**: `200 OK`

#### Example Request:
```bash
curl -X GET "http://localhost:8000/api/v1/certificates/jobs/e89cb21a-a123-4f90-880c-982736154d89"
```

#### Example Response:
```json
{
  "id": "e89cb21a-a123-4f90-880c-982736154d89",
  "event_name": "Full Stack & Cloud Architecture Masterclass",
  "issuer_name": "Aereo Engineering Academy",
  "issue_date": "2026-10-07",
  "template_title": "Certificate of Excellence",
  "status": "COMPLETED",
  "total_count": 2,
  "processed_count": 2,
  "success_count": 2,
  "failed_count": 0,
  "progress_percentage": 100.0,
  "created_at": "2026-10-07T07:45:00.000Z",
  "updated_at": "2026-10-07T07:45:01.000Z",
  "completed_at": "2026-10-07T07:45:01.000Z",
  "status_url": "http://localhost:8000/api/v1/certificates/jobs/e89cb21a-a123-4f90-880c-982736154d89",
  "download_all_url": "http://localhost:8000/api/v1/certificates/jobs/e89cb21a-a123-4f90-880c-982736154d89/download-all",
  "items": [
    {
      "id": "item-1",
      "recipient_name": "Sachin Shekhar",
      "recipient_email": "sachin@example.com",
      "recipient_metadata": { "grade": "Distinction", "score": "98%" },
      "status": "GENERATED",
      "certificate_id": "CERT-2026-8A7B9C1D2E",
      "download_url": "http://localhost:8000/api/v1/certificates/CERT-2026-8A7B9C1D2E/download",
      "error_message": null,
      "created_at": "2026-10-07T07:45:00.000Z",
      "processed_at": "2026-10-07T07:45:00.500Z"
    }
  ]
}
```

---

### 3. List Paginated Job Items & Filter Failures
For large batches, retrieves paginated recipient items and supports filtering by status (e.g. identify all `FAILED` recipients).

- **Endpoint**: `GET /api/v1/certificates/jobs/{job_id}/items?page=1&page_size=50&status=FAILED`
- **Status Code**: `200 OK`

#### Query Parameters:
- `page`: Page number (default: `1`, minimum: `1`).
- `page_size`: Items per page (default: `50`, maximum: `200`).
- `status`: Optional filter by `PENDING`, `GENERATED`, or `FAILED`.

---

### 4. Download an Individual Certificate PDF
Retrieves the generated PDF vector file for a specific certificate ID.

- **Endpoint**: `GET /api/v1/certificates/{certificate_id}/download`
- **Response**: `application/pdf` binary stream with filename attachment header.

```bash
curl -O -J "http://localhost:8000/api/v1/certificates/CERT-2026-8A7B9C1D2E/download"
```

---

### 5. Bulk Download All Certificates as ZIP
Bundles all successfully generated certificates belonging to a job into an in-memory `.zip` archive.

- **Endpoint**: `GET /api/v1/certificates/jobs/{job_id}/download-all`
- **Response**: `application/zip` stream named `job_{job_id}_certificates.zip`.

```bash
curl -O -J "http://localhost:8000/api/v1/certificates/jobs/e89cb21a-a123-4f90-880c-982736154d89/download-all"
```

---

### 6. Public Certificate Verification
Public endpoint enabling employers, universities, or verifiers to validate the authenticity of a credential. Also reachable by scanning the certificate's embedded QR code.

- **Endpoint**: `GET /api/v1/certificates/verify/{certificate_id}`
- **Status Code**: `200 OK` (or `404 Not Found` if fraudulent)

#### Example Response:
```json
{
  "certificate_id": "CERT-2026-8A7B9C1D2E",
  "is_valid": true,
  "recipient_name": "Sachin Shekhar",
  "recipient_email": "sachin@example.com",
  "event_name": "Full Stack & Cloud Architecture Masterclass",
  "issuer_name": "Aereo Engineering Academy",
  "issue_date": "2026-10-07",
  "file_hash": "b2f67623910c226a2cd8b886c5791307bdf37798782a2083b7ff41908236f874",
  "created_at": "2026-10-07T07:45:00.000Z",
  "download_url": "http://localhost:8000/api/v1/certificates/CERT-2026-8A7B9C1D2E/download"
}
```

---

## 💡 Design & Implementation Decisions

### 1. Asynchronous Background Processing
- **Problem**: Generating hundreds of PDF files synchronously inside an HTTP request will cause socket read timeouts (HTTP 504), client disconnection, and thread starvation.
- **Solution**: The API accepts the bulk payload, validates it via Pydantic, inserts the batch into the database, dispatches the job to a non-blocking background worker (`BackgroundTasks`), and returns `202 Accepted` in milliseconds.
- **Why BackgroundTasks?**: For a self-contained service, FastAPI `BackgroundTasks` operates without introducing external infrastructure dependencies (like Redis/RabbitMQ brokers). The codebase is structured with clear interfaces so swapping `BackgroundTasks` with Celery or Arq requires changing only the dispatch line.

### 2. Fault Isolation & Resiliency
- **Problem**: A single corrupted recipient record (e.g. special character errors, bad email format, or file I/O glitch) should not crash the entire batch.
- **Solution**: The processing loop wraps each recipient in an isolated `try...except` block with its own transaction management:
  - If a recipient fails, the error is caught, the transaction rolls back that item's changes, the item status is marked `FAILED` with `error_message` stored, and the counter `failed_count` is incremented.
  - The loop immediately proceeds to the next recipient.
  - When finished, the overall job status clearly differentiates:
    - `COMPLETED`: 100% of items succeeded.
    - `PARTIAL_SUCCESS`: Some succeeded, some failed.
    - `FAILED`: All items failed or fatal job error.

### 3. Predefined Template Engine: ReportLab Vector PDFs
- **Comparison**:
  - *Headless Browser (Puppeteer / WeasyPrint)*: Heavyweight, requires external Chrome/WebKit binaries, high RAM overhead (~150MB per process), slower rendering (~500ms per PDF).
  - *ReportLab*: Pure Python, zero external binary dependencies, renders in ~15ms per certificate, produces lightweight vector PDFs that remain crisp at 1000% zoom.
- **Template Layout**:
  - Landscape A4 (842 x 595 pt) geometry.
  - Midnight Navy (`#0F294A`) and Warm Gold (`#C59B27`) borders.
  - Formal geometric corner ornaments and a canvas-drawn seal badge.
  - Centered recipient typography with adaptive underline width.
  - Dual signature lines (Issuance Date & Authorized Signatory).
  - Embedded dynamic QR code and security footer.

### 4. Cryptographic Integrity & Scannable QR Codes
- Every generated certificate is stamped with:
  1. A unique formatted ID: `CERT-{YEAR}-{HEX10}`.
  2. A SHA-256 cryptographic hash calculated from the generated PDF byte stream and recorded in the database.
  3. A high-contrast QR code generated dynamically at 48x48 points on the canvas linking to the verification endpoint.

### 5. Relational Database Modeling
- **Entities**:
  - `CertificateJob`: Tracks batch metadata, issuer, aggregate counters, and status.
  - `JobItem`: Records recipient input, item-level processing state, certificate foreign key, and individual error message.
  - `Certificate`: Represents verified issued credentials, file paths, and cryptographic hashes.
- **Cascades & Indexes**:
  - Indexes on `status`, `job_id`, `recipient_email`, and `certificate_id` guarantee sub-millisecond query performance even with millions of records.
  - Clean cascading deletions ensure referential integrity.

### 6. Production Scaling Roadmap
For massive enterprise scale (100k+ certificates):
1. **Message Broker**: Transition background dispatch to Celery / Redis / RabbitMQ with distributed worker nodes.
2. **Object Storage**: Swap the local storage path with an S3 / Google Cloud Storage client using pre-signed URLs.
3. **Webhooks**: Provide an optional `callback_url` parameter in `CreateJobRequest` to notify the client system upon job completion.

---

## 🎯 Interview Defense & FAQs

### Q: Why did you choose FastAPI over Flask or Django?
> **Answer**: FastAPI offers native asynchronous ASGI support, automatic OpenAPI/Swagger interactive documentation, and high-performance Pydantic v2 validation. For a microservice centered on bulk processing and real-time status polling, FastAPI's lightweight footprint, dependency injection system, and non-blocking background task support make it significantly more efficient and maintainable than Flask or Django.

### Q: How does your system ensure that a failure in one certificate does not break the whole job?
> **Answer**: Each recipient in the job processor is wrapped in an individual `try...except` block with isolated database session handling. If an exception occurs, the transaction rolls back for that item, updates its status to `FAILED`, persists the exact error string in `error_message`, and increments `failed_count`. The processor then continues to the next recipient. The overall job status reflects `PARTIAL_SUCCESS` so the client can inspect both successful downloads and failed items.

### Q: How do you prevent race conditions when multiple workers access jobs?
> **Answer**: In SQLite/PostgreSQL, jobs transition atomically through status states (`PENDING` -> `PROCESSING` -> `COMPLETED`/`PARTIAL_SUCCESS`). In a distributed Celery deployment, row-level database locking (`SELECT ... FOR UPDATE SKIP LOCKED`) or task idempotency keys ensure workers never process the same recipient twice.

### Q: How do you verify that a certificate has not been tampered with?
> **Answer**: During generation, the backend calculates the SHA-256 hash of the generated PDF and stores it alongside the certificate record. When a client or verifier inspects a certificate or scans the embedded QR code, the verification endpoint validates the certificate ID, issuer details, and compares the stored hash against the physical file.

---

## 📝 License
This project is open-source and available under the [MIT License](LICENSE).
