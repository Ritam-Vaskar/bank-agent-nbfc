# NBFC Loan Platform - Technical Documentation

## 1. Document Purpose

This document is the technical reference for the bank-agent project. It explains:
- System architecture and runtime boundaries
- Agent and workflow orchestration
- Backend and frontend design
- Data model and persistence strategy
- Security, compliance, and observability
- Deployment topology and operations

It is written against the current implementation in this repository.

---

## 2. System Overview

The platform implements a conversational lending journey for retail loans, with deterministic underwriting engines and a staged workflow.

### Core capabilities
- OTP + JWT based authentication
- Guided loan application through chat
- Deterministic KYC, bureau, policy, affordability, risk, pricing, and EMI calculations
- Stage-wise confirmation gating before moving to next underwriting step
- Sanction letter PDF generation and simulated disbursement
- Admin analytics and audit log access

### Primary runtime components
- Frontend: Next.js 14 (App Router)
- Backend: FastAPI (async)
- Orchestration: LangGraph state machine + LangChain tools
- Datastores: MongoDB + Redis
- Document generation: ReportLab

---

## 3. Technology Stack

## Backend
- Python 3.11+
- FastAPI, Uvicorn
- Pydantic v2 + pydantic-settings
- LangGraph, LangChain, langchain-groq
- Motor (async MongoDB), Redis (async)
- Cryptography (Fernet), python-jose, PyJWT, passlib
- ReportLab + Pillow

## Frontend
- Next.js 14
- React 18
- Axios
- Zustand
- Tailwind CSS
- lucide-react

## DevOps
- Docker, Docker Compose
- Production compose profile in docker-compose.prod.yml

---

## 4. High-Level Architecture

The platform is split into four layers:

1) Presentation layer (frontend)
- Login, dashboard, chat, loan details
- Stateless API consumption with token-based auth

2) Application/API layer (backend routes)
- Auth routes: OTP and JWT lifecycle
- Loan routes: conversational state transitions and loan records
- Admin routes: analytics and audit retrieval

3) Orchestration + domain logic layer
- Loan workflow state machine
- Deterministic engine calls through tool wrappers
- Stage messages and confirmation checkpoints

4) Persistence layer
- MongoDB: source of truth for users, applications, loans, audit logs
- Redis: OTP, JWT blacklist, cache and fallback in-memory adapter

---

## 5. Backend Technical Design

### 5.1 FastAPI App Composition
- Entry point: backend/main.py
- Lifespan startup initializes MongoDB, Redis, and strict identity/bureau registries.
- Routers mounted under /api:
  - /api + auth routes (request-otp, verify-otp, logout, me)
  - /api/loans/*
  - /api/admin/*
- Audit middleware wraps all HTTP requests.
- CORS origins loaded from config via CORS_ORIGINS.

### 5.2 Configuration Model
- File: backend/config.py
- Uses environment variables (with .env support) for:
  - MONGODB_URI, MONGODB_DB_NAME
  - REDIS_URL
  - JWT settings
  - GROQ_API_KEY
  - ENCRYPTION_KEY
  - FRONTEND_URL, BACKEND_URL, CORS_ORIGINS
  - ENVIRONMENT

### 5.3 Data Access Layer
- File: backend/database.py
- MongoDB connection manager exposes collection shortcuts.
- Redis client supports:
  - OTP set/get/attempt counters
  - JWT blacklist set/check
  - Bureau cache operations
- If Redis is unavailable, an async in-memory fallback is used.

---

## 6. Agent and Workflow Architecture

There are two agent patterns in the repository:

1) Active production path (used by backend API)
- LangGraph loan workflow in backend/workflows/loan_graph.py
- Triggered by loan routes in backend/routes/loans.py

2) Separate prototype orchestrator
- Flask-based multi-agent orchestrator in agents/master_agent.py
- Kept as an alternate design/prototype path and not mounted in FastAPI runtime

## 6.1 Active Loan Workflow (LangGraph)

### Workflow state
LoanWorkflowState includes:
- Identifiers: application_id, user_id, loan_type
- Stage marker: init, collect_info, verify_kyc, fetch_credit, check_policy, assess_affordability, assess_risk, generate_offer, explain_offer, await_acceptance, generate_sanction, simulate_disbursement, rejected, completed
- Data buckets: application_data, kyc_data, credit_data, policy_validation, affordability_result, risk_assessment, loan_offer, emi_schedule
- Decision flags: is_eligible, is_accepted, rejection_reason
- Conversation message history

### Node progression
1. init_application
2. collect_information
3. verify_kyc_node
4. fetch_credit_node
5. check_policy_node
6. assess_affordability_node
7. assess_risk_node
8. generate_offer_node
9. explain_offer_node
10. await_acceptance (chat interaction gate)
11. generate_sanction_node
12. simulate_disbursement_node
13. rejected/completed terminal handling

### Deterministic step-gating behavior
- The API processes one stage at a time using run_workflow_stepwise.
- User must explicitly confirm between stages with intent keywords.
- Confirmation intents include:
  - Continue: ok, okay, continue, next
  - Accept: accept, yes, agree, confirm
  - Reject: reject, decline, no, cancel
- Additional lifecycle controls:
  - terminate chat
  - reset chat

### Follow-up behavior
- If application is completed/rejected, follow-up Q&A is handled without changing underwriting decisions.

---

## 7. Deterministic Engines and Tool Wrappers

Engine wrappers are defined in backend/workflows/tools.py and mapped to engines in backend/engines.

## 7.1 KYC engine
- Validates Aadhaar and PAN formats
- Cross-checks against fixed mock identity registry
- Encrypts PAN/Aadhaar using Fernet
- Returns masked + structured verification payload

## 7.2 Bureau engine
- Fetches from fixed mock bureau dataset by PAN
- Returns credit score and repayment indicators
- Supports deterministic credit checks

## 7.3 Policy engine
- Loads policy JSON (personal_loan.json)
- Enforces eligibility boundaries and policy checks
- Determines pricing base rate

## 7.4 Affordability engine
- Uses FOIR-based calculations
- Computes eligibility/amount reduction outcomes

## 7.5 Risk engine
- Produces risk score and risk segment
- Uses credit + affordability + profile features

## 7.6 Pricing engine
- Generates final offer and charge breakdown
- Integrates processing fee and effective repayment details

## 7.7 EMI engine
- Generates amortization schedule
- Produces month-wise principal/interest components

## 7.8 PDF engine
- Generates sanction letter
- Persists file and links with loan record

---

## 8. Loan Route Lifecycle (API Orchestration)

Primary orchestrator endpoint:
- POST /api/loans/applications/{application_id}/chat

Request processing sequence:
1. Load application from MongoDB
2. Reconstruct LoanWorkflowState from persisted document
3. Append user message to conversation history
4. Parse user intent (continue, accept, reject, reset, terminate)
5. During collect_info stage, parse structured data from natural language
6. Run exactly one workflow step where applicable
7. Persist state snapshot back to loan_applications
8. On acceptance and first loan creation, insert loan document in loans collection

Additional endpoints:
- POST /api/loans/apply
- POST /api/loans/applications/{application_id}/terminate
- POST /api/loans/applications/{application_id}/reset
- GET /api/loans/applications
- GET /api/loans/applications/{application_id}
- GET /api/loans/active
- GET /api/loans/{loan_id}
- GET /api/loans/{loan_id}/emi-schedule
- GET /api/loans/{loan_id}/sanction-letter

Identity enrichment behavior:
- Active loan and loan detail responses include customer_identity.
- Identity fields are resolved from application_data, kyc_data, and registry fallback.

---

## 9. Frontend Technical Design

## 9.1 Routing
- frontend/app/page.js: landing and auth entry
- frontend/app/dashboard/page.js: loan requests, active loans, recent chats
- frontend/app/apply/[loanType]/page.js: chat workflow UI
- frontend/app/loans/[loanId]/page.js: loan details and EMI schedule

## 9.2 API layer
- frontend/lib/api.js provides Axios instance and typed API calls.
- JWT token is attached from localStorage via request interceptor.
- 401 responses clear session and redirect to landing page.

## 9.3 Client state
- frontend/lib/store.js
- Auth store:
  - user, token, isAuthenticated, initAuth lifecycle
- Application store (persisted in localStorage):
  - currentApplicationId
  - workflow stage and status
  - messages and progress
  - offer, loanId, completion flag

## 9.4 Identity rendering
- Dashboard renders identity details in Loan Requests and Recent Chats.
- Loan details page renders per-loan customer identity block.

---

## 10. Data Model (MongoDB)

## users
- user_id, email, role, is_verified, timestamps

## loan_applications
- application_id, user_id, loan_type, status
- workflow_stage
- application_data
- kyc_data, credit_data
- policy_validation, affordability_result, risk_assessment
- loan_offer, emi_schedule
- loan_id, sanction_letter_path
- conversation_messages
- progress object

## loans
- loan_id, application_id, user_id
- principal, tenure_months, interest_rate, monthly_emi
- total_interest, total_repayment
- disbursement_date, disbursement_amount
- emi_schedule
- customer_identity

## audit_logs
- action, decision, metadata, timestamp and user/application linkage

---

## 11. Security and Compliance Controls

- OTP-based login with bounded retries and TTL
- JWT-based API authorization
- Token blacklist support on logout
- Aadhaar/PAN encryption for storage
- PII masking for conversational and display pathways
- Stage-level deterministic checks reduce hallucination risk in lending decisions
- Audit logging middleware for sensitive operations
- CORS restrictions configurable via environment

Operational note:
- If any secret appears in logs, rotate immediately.

---

## 12. Reliability and Observability

- Health endpoint: /health reports app + datastore status
- Container health checks in compose/docker files
- Structured logging to backend/logs/app.log
- Deterministic failure paths:
  - KYC failure
  - credit threshold fail
  - policy fail
  - affordability fail
  - user rejection/termination

---

## 13. Deployment Topology

### Local development
- docker-compose.yml runs MongoDB, Redis, backend, frontend in dev mode

### Production on EC2
- docker-compose.prod.yml
- backend/.env for production secrets and endpoints
- frontend built with NEXT_PUBLIC_API_URL build argument
- full runbook: docs/EC2_DOCKER_DEPLOYMENT.md

Recommended hardening:
- reverse proxy with TLS termination (Nginx + Let’s Encrypt)
- expose only 80/443 publicly
- close direct access to 27017 and 6379

---

## 14. Agent Flow Reference (Current)

### Customer flow summary
1. User starts application
2. System collects mandatory fields one-by-one
3. User confirms data summary
4. KYC check and confirmation
5. Bureau check and confirmation
6. Policy validation and confirmation
7. Affordability and confirmation
8. Risk scoring and confirmation
9. Offer generation and explanation
10. User accepts or rejects
11. On acceptance: sanction letter + disbursement simulation + loan creation

### Internal responsibility mapping
- Conversational framing and explanation: workflow messages
- Underwriting decisioning: deterministic engines
- State control and persistence: loan routes + MongoDB
- Display and continuation UX: frontend app pages + Zustand persistence

---

## 15. Known Gaps and Improvement Areas

- Optional API versioning and OpenAPI hardening
- Centralized retry/circuit breaker for external-like dependencies
- Expanded automated test coverage for full stage transitions
- Enhanced admin observability dashboards
- Optional unified architecture retirement plan for agents/master_agent.py prototype

---

## 16. Quick File Map

- Backend app bootstrap: backend/main.py
- Workflow orchestration: backend/workflows/loan_graph.py
- Tool wrappers: backend/workflows/tools.py
- Loan route orchestration: backend/routes/loans.py
- Auth routes: backend/routes/auth.py
- Admin routes: backend/routes/admin.py
- Engine modules: backend/engines/
- Frontend routes: frontend/app/
- Frontend state/api: frontend/lib/
- Production deployment files:
  - backend/Dockerfile
  - frontend/Dockerfile
  - docker-compose.prod.yml
  - docs/EC2_DOCKER_DEPLOYMENT.md

---

## 17. Revision Notes

- Includes deterministic stage-by-stage confirmation workflow
- Includes terminate/reset chat lifecycle
- Includes identity enrichment for loan and dashboard views
- Includes EC2 + Docker production deployment path
