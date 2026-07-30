# fastapi-ci

[![CI Pipeline](https://github.com/VenuKXN-95/fastapi-ci/actions/workflows/ci.yml/badge.svg)](https://github.com/VenuKXN-95/fastapi-ci/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![Security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Production-grade FastAPI service with a 16-stage DevSecOps CI pipeline powered by GitHub Actions.

---

## Table of Contents

- [Project Structure](#project-structure)
- [CI/CD Pipeline Overview](#cicd-pipeline-overview)
- [Pipeline Stages Explained](#pipeline-stages-explained)
- [GitHub Repository Configuration](#github-repository-configuration)
- [Required GitHub Secrets](#required-github-secrets)
- [Branch Protection Rules](#branch-protection-rules)
- [Local Development Setup](#local-development-setup)
- [Running Tests Locally](#running-tests-locally)
- [Docker Build Locally](#docker-build-locally)
- [Future CD Integration](#future-cd-integration)
- [Assumptions & Design Decisions](#assumptions--design-decisions)

---

## Project Structure

```
/
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI application entry point
│   ├── config.py             # Pydantic Settings — reads from env vars
│   └── routers/
│       ├── __init__.py
│       ├── health.py         # /api/v1/health  /api/v1/ready
│       └── items.py          # /api/v1/items   (example CRUD)
├── tests/
│   ├── __init__.py
│   ├── test_health.py        # Health & readiness endpoint tests
│   └── test_items.py         # Items CRUD endpoint tests
├── .github/
│   └── workflows/
│       └── ci.yml            # ← THE CI PIPELINE (16 stages)
├── requirements.txt          # Runtime dependencies (pinned)
├── requirements-dev.txt      # CI/dev-only tools (pinned)
├── Dockerfile                # Multi-stage production image
├── .dockerignore             # Build context exclusions
├── .gitignore                # Git exclusions
├── .env.example              # Template for environment variables
├── .gitleaks.toml            # Gitleaks secret scanning config
├── pyproject.toml            # All tooling config (pytest/black/ruff/mypy/bandit)
├── sonar-project.properties  # SonarQube scanner configuration
└── README.md
```

---

## CI/CD Pipeline Overview

The pipeline is defined in [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

### Trigger Events

| Event | Branches |
|-------|----------|
| Pull Request (opened / synchronize / reopened) | `main`, `develop`, `feature/**`, `bugfix/**`, `hotfix/**`, `release/**` |
| Push | `main`, `develop`, `feature/**`, `bugfix/**`, `hotfix/**`, `release/**` |
| Manual (`workflow_dispatch`) | Any branch |

### Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     CI Job  (ubuntu-latest)                         │
│                                                                     │
│  Stage 1  │ Checkout (full history for Gitleaks)                    │
│  Stage 2  │ Setup Python 3.12 + pip cache                           │
│  Stage 3  │ Install requirements.txt + requirements-dev.txt         │
│  Stage 4  │ Validate mandatory GitHub Secrets → fail if missing     │
│           │                                                         │
│  ┌──────────────── Quality Gate ──────────────────────┐             │
│  │ Stage 5  │ black --check  │ isort --check-only     │             │
│  │ Stage 6  │ flake8         │ ruff                   │             │
│  │ Stage 7  │ mypy (strict)                            │             │
│  │ Stage 8  │ pytest (≥80% coverage) + JUnit XML       │             │
│  └──────────────────────────────────────────────────────┘             │
│           │                                                         │
│  ┌──────────────── Security Gate ─────────────────────┐             │
│  │ Stage 9  │ Bandit (SAST — medium/high/critical)    │             │
│  │ Stage 10 │ pip-audit (dependency CVEs)              │             │
│  │ Stage 11 │ Gitleaks (secret history scan)           │             │
│  └──────────────────────────────────────────────────────┘             │
│           │                                                         │
│  Stage 12 │ SonarQube analysis + Quality Gate                      │
│           │                                                         │
│  ┌──────────────── Container Gate ────────────────────┐             │
│  │ Stage 13 │ Docker buildx (SHA + latest tags, cache)│             │
│  │ Stage 14 │ Trivy scan (OS + libs) → SARIF upload   │             │
│  └──────────────────────────────────────────────────────┘             │
│           │                                                         │
│  Stage 15 │ Upload artifacts (coverage, junit, bandit, trivy)      │
│  Stage 16 │ GitHub Job Summary                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Pipeline Stages Explained

### Stage 1 — Checkout Repository
Uses `actions/checkout@v4` with `fetch-depth: 0` (full history) so that **Gitleaks** (Stage 11) can scan every commit, not just the current one.

### Stage 2 — Setup Python
Uses `actions/setup-python@v5` with Python **3.12**.  
Pip dependency caching is enabled, keyed on both `requirements.txt` and `requirements-dev.txt`. Cache hits save ~30–60 seconds per run.

### Stage 3 — Install Dependencies
- `pip install --upgrade pip` — always runs to avoid pip version mismatches.
- `pip install --no-cache-dir --requirement requirements.txt` — runtime deps.
- `pip install --no-cache-dir --requirement requirements-dev.txt` — CI tools.

Both files use **pinned versions** (`==`) for complete reproducibility.

### Stage 4 — Validate Environment Variables
A bash script checks every **mandatory secret** (`DATABASE_URL`, `SECRET_KEY`, `JWT_SECRET`, `API_KEY`, `POSTGRES_URI`, `MONGODB_URI`).  
If any are empty or absent it prints a clear error with remediation instructions and **exits 1** immediately.

### Stage 5 — Code Formatting
| Tool | Command | Failure condition |
|------|---------|-----------------|
| `black` | `black --check --diff --color app/ tests/` | Any file differs from Black's format |
| `isort` | `isort --check-only --diff --color app/ tests/` | Import order is wrong |

Developers should run `black app/ tests/ && isort app/ tests/` before committing.

### Stage 6 — Linting
| Tool | Rule set | Notes |
|------|---------|-------|
| `flake8` | PEP 8, bugbear, simplify, comprehensions | `--max-complexity=10` |
| `ruff` | E, W, F, UP, B, SIM, I, N, S, C4, PTH, RUF | GitHub annotation output |

All rules are configured in `pyproject.toml` for IDE parity.

### Stage 7 — Static Type Checking
`mypy` runs in **strict** mode (`--strict`) on the `app/` directory.  
Pydantic V2 plugin is enabled for full model type inference.  
Third-party libraries without stubs (e.g., `motor`, `jose`) are excluded via `[[tool.mypy.overrides]]`.

### Stage 8 — Unit Testing
`pytest` with:
- `--cov=app --cov-fail-under=80` — **fails if coverage drops below 80%**
- `--cov-report=xml:coverage.xml` — for SonarQube
- `--cov-report=html:htmlcov` — for human review
- `--junitxml=junit.xml` — for SonarQube test results
- Test environment uses a local SQLite DB so no real database is required in CI.

### Stage 9 — Security Scan (Bandit)
`bandit --recursive app/ --severity-level medium --confidence-level medium`  
The JSON output is parsed inline and the step **fails if any Medium, High, or Critical issue is found**.  
Configuration lives in `[tool.bandit]` in `pyproject.toml`.

### Stage 10 — Dependency Vulnerability Scan (pip-audit)

**Why pip-audit over Safety?**

| Criterion | pip-audit | Safety (v3+) |
|-----------|-----------|-------------|
| Maintainer | Python Packaging Authority (PyPA) | PyUp.io (commercial) |
| Database | OSV (Google) + PyPI Advisory DB | Safety DB (proprietary) |
| API key required | ❌ No | ✅ Yes (for full DB) |
| Open source | ✅ Yes (Apache 2.0) | ⚠️ CLI is open; DB is proprietary |
| CI integration | Native JSON, pip ecosystem | Requires API key in Secrets |
| CVE sources | NVD, GitHub Advisories, OSV | Safety-specific DB |

`pip-audit` is the **official PyPA recommendation** for Python dependency scanning and is free for unlimited use without API keys.

### Stage 11 — Secret Scanning (Gitleaks)
Uses `gitleaks/gitleaks-action@v2` which wraps the Gitleaks CLI.  
Configuration in `.gitleaks.toml`:
- Extends the default upstream ruleset.
- Custom rules for **JWT tokens**, **Bearer tokens in source**, and **database URIs with embedded passwords**.
- Allowlist for placeholder values in `.env.example` and tests.
- Scans the **full git history** (made possible by `fetch-depth: 0`).

### Stage 12 — SonarQube Analysis
Uses `SonarSource/sonarqube-scan-action@v5` followed by `SonarSource/sonarqube-quality-gate-action@v1`.  
- `coverage.xml` and `junit.xml` are uploaded to SonarQube for coverage and test metrics.
- The Quality Gate step **polls the SonarQube server** and **fails the pipeline** if the gate is not met.
- For Pull Requests, PR decoration is enabled via `sonar.pullrequest.*` parameters.
- Skipped automatically if `SONAR_TOKEN` or `SONAR_HOST_URL` secrets are absent.

### Stage 13 — Docker Build
| Feature | Detail |
|---------|--------|
| Action | `docker/build-push-action@v6` |
| BuildKit | Enabled via Buildx driver |
| Layer cache | `type=gha` (GitHub Actions cache) |
| Tags | `sha-<short>`, `latest` (main only), branch name, PR ref |
| Push | ❌ Never in CI — push happens in CD |
| Provenance | ✅ SLSA provenance attestation |
| SBOM | ✅ Software Bill of Materials |
| Multi-arch | `linux/amd64` (add `linux/arm64` for Apple Silicon / Graviton) |

### Stage 14 — Docker Image Scan (Trivy)
Uses `aquasecurity/trivy-action@0.30.0` to scan the freshly built image.  
- **Table output** — human-readable log (does not fail).
- **SARIF output** — uploaded to the **GitHub Security tab** via `github/codeql-action/upload-sarif@v3`.
- **Fails the pipeline** on `CRITICAL` or `HIGH` severity vulnerabilities.
- Scans both `os` packages and `library` (Python) packages.

### Stage 15 — Upload Build Artifacts
All reports are uploaded as GitHub Actions artifacts with a **14-day retention**:
- `test-reports-*` — `coverage.xml`, `junit.xml`, `htmlcov/`
- `bandit-report-*` — JSON + TXT
- `pip-audit-report-*` — JSON
- `trivy-report-*` — TXT + SARIF
- `lint-reports-*` — flake8, mypy

### Stage 16 — Job Summary
Generates a Markdown summary table in the **GitHub Actions Job Summary** UI showing the result of every stage — Python version, package count, lint/format/type/test/security/docker status, image digest, and tags.

---

## GitHub Repository Configuration

### 1. Fork / Clone

```bash
git clone https://github.com/VenuKXN-95/fastapi-ci.git
cd fastapi-ci
```

### 2. Push all files

```bash
git add .
git commit -m "feat: add production CI pipeline"
git push origin main
```

---

## Required GitHub Secrets

Navigate to **Repository → Settings → Secrets and variables → Actions → New repository secret**.

| Secret Name | Description | Required |
|-------------|-------------|----------|
| `DATABASE_URL` | Primary DB connection string | ✅ |
| `SECRET_KEY` | Application secret key (≥32 chars) | ✅ |
| `JWT_SECRET` | JWT signing secret (≥32 chars) | ✅ |
| `API_KEY` | Internal API key | ✅ |
| `POSTGRES_URI` | PostgreSQL async connection string | ✅ |
| `MONGODB_URI` | MongoDB connection string | ✅ |
| `OPENAI_API_KEY` | OpenAI API key | ⚠️ Optional |
| `SONAR_TOKEN` | SonarQube / SonarCloud auth token | ⚠️ Optional (skipped if absent) |
| `SONAR_HOST_URL` | `https://sonarcloud.io` or self-hosted URL | ⚠️ Optional (skipped if absent) |
| `GITLEAKS_LICENSE` | Gitleaks commercial licence key | ⚠️ Optional (OSS repos use free tier) |

> **Tip:** For local test runs, CI uses a SQLite fallback (`sqlite:///./test.db`).  
> In CI, set `DATABASE_URL` to any non-empty string if no real DB is available for the pipeline itself.

---

## Branch Protection Rules

Navigate to **Repository → Settings → Branches → Add rule** for `main` and `develop`.

### Recommended settings:

```
Branch name pattern: main

☑ Require a pull request before merging
  ☑ Require approvals: 1
  ☑ Dismiss stale pull request approvals when new commits are pushed

☑ Require status checks to pass before merging
  ☑ Require branches to be up to date before merging
  Status checks to add:
    → "🔬 CI — Quality, Security & Build"   (from ci.yml)

☑ Require conversation resolution before merging
☑ Require signed commits
☑ Do not allow bypassing the above settings
☑ Restrict who can push to matching branches  → add your release team
```

Repeat for `develop` (you may relax the signed-commits requirement on `develop`).

---

## Local Development Setup

```bash
# 1. Create & activate virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. Install all dependencies
pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt

# 3. Copy env template and fill in your values
cp .env.example .env
# edit .env with your local secrets

# 4. Start the dev server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000/docs for the Swagger UI.

---

## Running Tests Locally

```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/test_health.py -v

# Run with parallel execution (faster on large test suites)
pytest -n auto

# Check formatting
black --check app/ tests/
isort --check-only app/ tests/

# Run linters
flake8 app/ tests/
ruff check app/ tests/

# Run type checker
mypy app/

# Run security scan
bandit --recursive app/ --severity-level medium

# Run dependency audit
pip-audit --requirement requirements.txt
```

---

## Docker Build Locally

```bash
# Build the image
DOCKER_BUILDKIT=1 docker build \
  --build-arg BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
  --build-arg VCS_REF=$(git rev-parse --short HEAD) \
  --build-arg VERSION=1.0.0 \
  -t fastapi-ci:local \
  .

# Run locally
docker run --rm \
  --env-file .env \
  -p 8000:8000 \
  fastapi-ci:local

# Scan locally with Trivy
trivy image --severity CRITICAL,HIGH fastapi-ci:local
```

---

## Future CD Integration

The CI pipeline **builds but never pushes** the image. Below are recommended CD integration patterns once you're ready to deploy.

### Option 1 — Google Cloud Run

```yaml
# Add to a separate cd.yml, triggered after ci.yml succeeds on main
- name: Authenticate to Google Cloud
  uses: google-github-actions/auth@v2
  with:
    workload_identity_provider: ${{ secrets.GCP_WORKLOAD_IDENTITY_PROVIDER }}
    service_account: ${{ secrets.GCP_SERVICE_ACCOUNT }}

- name: Push to Google Artifact Registry
  uses: docker/build-push-action@v6
  with:
    push: true
    tags: ${{ vars.GAR_REGION }}-docker.pkg.dev/${{ vars.GCP_PROJECT }}/fastapi/${{ env.IMAGE_NAME }}:${{ github.sha }}

- name: Deploy to Cloud Run
  uses: google-github-actions/deploy-cloudrun@v2
  with:
    service: fastapi-ci
    image: ${{ vars.GAR_REGION }}-docker.pkg.dev/${{ vars.GCP_PROJECT }}/fastapi/${{ env.IMAGE_NAME }}:${{ github.sha }}
    region: ${{ vars.GCP_REGION }}
```

### Option 2 — AWS ECS (Fargate)

```yaml
- name: Configure AWS credentials (OIDC)
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
    aws-region: ${{ vars.AWS_REGION }}

- name: Push to Amazon ECR
  uses: aws-actions/amazon-ecr-login@v2

- name: Deploy to ECS
  uses: aws-actions/amazon-ecs-deploy-task-definition@v2
  with:
    task-definition: .aws/task-definition.json
    service: fastapi-ci-service
    cluster: fastapi-ci-cluster
    wait-for-service-stability: true
```

### Option 3 — GKE (Kubernetes)

```yaml
- name: Deploy to GKE
  uses: google-github-actions/get-gke-credentials@v2
  with:
    cluster_name: ${{ vars.GKE_CLUSTER }}
    location: ${{ vars.GKE_ZONE }}

- name: Kubectl rollout
  run: |
    kubectl set image deployment/fastapi-ci \
      fastapi-ci=${{ vars.GAR_REGION }}-docker.pkg.dev/${{ vars.GCP_PROJECT }}/fastapi/${{ env.IMAGE_NAME }}:${{ github.sha }}
    kubectl rollout status deployment/fastapi-ci
```

### Option 4 — Azure Container Apps

```yaml
- name: Azure Login (OIDC)
  uses: azure/login@v2
  with:
    client-id: ${{ secrets.AZURE_CLIENT_ID }}
    tenant-id: ${{ secrets.AZURE_TENANT_ID }}
    subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

- name: Deploy to Azure Container Apps
  uses: azure/container-apps-deploy-action@v2
  with:
    resourceGroup: ${{ vars.AZURE_RG }}
    containerAppName: fastapi-ci
    imageToDeploy: ${{ vars.ACR_LOGIN_SERVER }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
```

### Option 5 — Docker Hub / GHCR

```yaml
- name: Login to GHCR
  uses: docker/login-action@v3
  with:
    registry: ghcr.io
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}

- name: Push to GHCR
  uses: docker/build-push-action@v6
  with:
    push: true
    tags: ghcr.io/${{ github.repository }}:${{ github.sha }}
```

> **Security recommendation:** In all CD scenarios, use **OIDC Workload Identity Federation** instead of long-lived access keys. This eliminates the need to store cloud credentials as GitHub Secrets.

---

## Assumptions & Design Decisions

| Decision | Rationale |
|----------|-----------|
| Single CI job (no matrix) | The service is a monorepo with one language; parallel jobs would add orchestration overhead without meaningful time savings on a 30-minute timeout. |
| `pip` instead of Poetry/PDM | Matches the stated project stack. Poetry/PDM can be added later without changing the pipeline structure. |
| `--require-hashes` on pip install (attempted) | Provides supply-chain integrity. Fallback to non-hashed install if a hash-pinned lockfile is not yet generated. |
| `push: false` on Docker build | CI only validates the image; pushing is a CD concern. This enforces separation of concerns. |
| Trivy fails on CRITICAL/HIGH only | MEDIUM vulnerabilities are reported but do not gate the release, to avoid blocking on unfixable OS-level issues. Adjust `severity` as your policy dictates. |
| SonarQube is optional | Teams without SonarQube access should not be blocked. The step is auto-skipped if secrets are absent. |
| `fetch-depth: 0` | Required by Gitleaks for full history scanning and by SonarQube for blame information. |
| `concurrency: cancel-in-progress` | Prevents resource waste when multiple pushes land on the same branch quickly. |
| 14-day artifact retention | Balances storage cost vs. debugging window. Adjust to 30 days for regulated environments. |
