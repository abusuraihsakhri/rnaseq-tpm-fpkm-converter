# RNA-Seq TPM/FPKM Converter

> **Domain:** Bioinformatics & RNA-Seq Normalization

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)

</div>

---

## Overview

RNA-Seq TPM, FPKM & RPKM Normalization Engine. Converts raw gene read counts and transcript lengths into Transcripts Per Million (TPM) and FPKM values.

Zero-dependency Python implementation with single and batch evaluation modes.

Author: Dr. Abu Suraih Sakhri
License: MIT

---

## Features

- **Single evaluation mode:** Process individual measurements via CLI
- **Batch processing:** Process CSV files with multiple records
- **Multi-agent analysis:** Specialized workers for QC, safety, and protocol conformance
- **PHI protection:** Outbound guard preventing sensitive data leakage
- **Audit trail:** HMAC-SHA256 tamper-evident logging
- **REST API:** FastAPI-based web interface

---

## Installation

```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/rnaseq-tpm-fpkm-converter.git
cd rnaseq-tpm-fpkm-converter

# Install dependencies
pip install -e ".[web,test]"

# Set up environment variables
cp .env.example .env
# Edit .env and set AUDIT_SECRET_KEY
```

### Environment Variables

| Variable | Required | Description |
|:---------|:---------|:------------|
| `AUDIT_SECRET_KEY` | Yes | Secret key for HMAC-SHA256 audit signing |
| `MODEL_PROVIDER` | No | LLM provider: `mock`, `ollama`, `claude`, `openai` (default: `mock`) |

Generate a secure key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Usage

### CLI - Single Evaluation

```bash
python cli.py single --v1 14.5 --v2 4.2 --v3 1.8
```

### CLI - Batch Processing

```bash
python cli.py batch -i sample.csv -o results.csv
```

### CLI - Audit Mode

```bash
python cli.py audit --task-id TASK-001 --primary 28.5 --secondary 14.2
```

### Web API Server

```bash
python cli.py serve --host 127.0.0.1 --port 8000
```

### Docker Deployment

```bash
# Using docker-compose (requires .env file)
docker-compose up --build

# Or manually
docker build -t rnaseq-tpm-fpkm-converter .
docker run -p 8000:8000 --env-file .env rnaseq-tpm-fpkm-converter
```

---

## Input Data Format

CSV files should contain the following columns:

| Field | Description | Requirement |
|:------|:------------|:------------|
| `Patient_ID` | Patient/sample identifier | Required |
| `v1` | Primary measurement | Required |
| `v2` | Secondary measurement | Required |
| `v3` | Tertiary measurement | Required |

See `sample.csv` for an example.

---

## Testing

```bash
# Set test secret key
export AUDIT_SECRET_KEY=test-secret-for-testing

# Run all tests
pytest -v
```

---

## Project Structure

```
rnaseq-tpm-fpkm-converter/
├── agents/                  # Multi-agent analysis framework
│   ├── api.py              # FastAPI REST endpoints
│   ├── base.py             # Security, PHI guard, audit trail
│   ├── models.py           # Pydantic data models
│   ├── supervisor.py       # Agent orchestration
│   ├── workers.py          # Specialized analysis workers
│   └── ...
├── tests/                   # Test suite
├── cli.py                   # Command-line interface
├── rnaseq_norm.py          # Core normalization engine
├── enrichment.py           # Additional analysis modules
├── pyproject.toml          # Python package configuration
├── Dockerfile              # Container build
└── docker-compose.yml      # Container orchestration
```

---

## Security

- **PHI Guard:** AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers
- **Audit Trail:** Chained HMAC-SHA256 tamper-evident logs
- **Path Traversal Protection:** Input validation prevents directory traversal attacks
- **Secret Management:** No hardcoded secrets; all keys via environment variables
