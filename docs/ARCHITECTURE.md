# System Architecture - NBFC Digital Lending Platform

## Overview

The NBFC Digital Lending Platform is built on a microservices-inspired architecture with clear separation between presentation (Next.js frontend), orchestration (LangGraph), business logic (deterministic engines), and persistence layers (MongoDB + Redis).

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│                         CLIENT LAYER                                     │
│                                                                          │
│  ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐  │
│  │   Web Browser    │   │  Mobile (Future) │   │   Admin Portal   │  │
│  │   (Next.js UI)   │   │   (React Native) │   │   (Dashboard)    │  │
│  └─────────┬────────┘   └─────────┬────────┘   └─────────┬────────┘  │
│            │                       │                       │            │
└────────────┼───────────────────────┼───────────────────────┼────────────┘
             │                       │                       │
             │        REST API / WebSocket (FastAPI)         │
             │                       │                       │
┌────────────┴───────────────────────┴───────────────────────┴────────────┐
│                                                                          │
│                      APPLICATION LAYER (FastAPI)                         │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────┐     │
│  │                    Authentication Middleware                   │     │
│  │          (JWT Verification, Role-Based Access Control)         │     │
│  └───────────────────────────────────────────────────────────────┘     │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────┐     │
│  │                       Route Handlers                           │     │
│  │  /auth  /loans  /kyc  /admin  /bureau  /documents            │     │
│  └───────────────────────────────────────────────────────────────┘     │
│                                                                          │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │
┌──────────────────────────────┴───────────────────────────────────────────┐
│                                                                           │
│                  ORCHESTRATION LAYER (LangGraph)                          │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                  Loan Application State Machine                   │  │
│  │                                                                    │  │
│  │   START                                                            │  │
│  │     ↓                                                              │  │
│  │   ┌────────────────────┐                                          │  │
│  │   │ Collect Basic Info │  (LLM Node)                              │  │
│  │   └─────────┬──────────┘                                          │  │
│  │             ↓                                                      │  │
│  │   ┌────────────────────┐                                          │  │
│  │   │   Verify KYC       │  (Tool Call: verify_kyc_tool)            │  │
│  │   └─────────┬──────────┘                                          │  │
│  │             ↓                                                      │  │
│  │      [Conditional Edge]                                            │  │
│  │       ├─ Failed → handle_rejection                                │  │
│  │       └─ Passed ↓                                                  │  │
│  │   ┌────────────────────┐                                          │  │
│  │   │ Fetch Credit Score │  (Tool Call: fetch_credit_tool)          │  │
│  │   └─────────┬──────────┘                                          │  │
│  │             ↓                                                      │  │
│  │      [Conditional Edge]                                            │  │
│  │       ├─ Score < Min → handle_rejection                           │  │
│  │       └─ Score OK ↓                                                │  │
│  │   ┌────────────────────┐                                          │  │
│  │   │Calculate Affordabil│  (Tool Call: calculate_affordability)    │  │
│  │   └─────────┬──────────┘                                          │  │
│  │             ↓                                                      │  │
│  │   ┌────────────────────┐                                          │  │
│  │   │  Risk Assessment   │  (Tool Call: assess_risk_tool)           │  │
│  │   └─────────┬──────────┘                                          │  │
│  │             ↓                                                      │  │
│  │   ┌────────────────────┐                                          │  │
│  │   │  Generate Offer    │  (Tool Call: generate_offer_tool)        │  │
│  │   └─────────┬──────────┘                                          │  │
│  │             ↓                                                      │  │
│  │   ┌────────────────────┐                                          │  │
│  │   │  Explain Offer     │  (LLM Node - Conversational)             │  │
│  │   └─────────┬──────────┘                                          │  │
│  │             ↓                                                      │  │
│  │   ┌────────────────────┐                                          │  │
│  │   │ Await Acceptance   │  (Human-in-the-loop)                     │  │
│  │   └─────────┬──────────┘                                          │  │
│  │             ↓                                                      │  │
│  │      [Conditional Edge]                                            │  │
│  │       ├─ Rejected → END                                            │  │
│  │       └─ Accepted ↓                                                │  │
│  │   ┌────────────────────┐                                          │  │
│  │   │Generate Sanction   │  (Tool Call: generate_sanction_pdf)      │  │
│  │   └─────────┬──────────┘                                          │  │
│  │             ↓                                                      │  │
│  │   ┌────────────────────┐                                          │  │
│  │   │Simulate Disbursemnt│  (Tool Call: simulate_disbursement)      │  │
│  │   └─────────┬──────────┘                                          │  │
│  │             ↓                                                      │  │
│  │           END                                                      │  │
│  │                                                                    │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  State Persistence: MongoDB Checkpointer                                 │
│                                                                           │
└───────────────────────────────┬───────────────────────────────────────────┘
                                │
┌───────────────────────────────┴───────────────────────────────────────────┐
│                                                                            │
│                    BUSINESS LOGIC LAYER (Engines)                          │
│                                                                            │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │
│  │  Policy Engine   │  │   KYC Engine     │  │   Bureau Engine      │  │
│  │                  │  │                  │  │                      │  │
│  │ - Load policies  │  │ - Validate docs  │  │ - Mock CIBIL fetch   │  │
│  │ - Validate rules │  │ - Encrypt PII    │  │ - Credit history     │  │
│  │ - Get violations │  │ - Mask sensitive │  │ - DPD calculation    │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────┘  │
│                                                                            │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │
│  │Affordability Eng │  │   Risk Engine    │  │   Pricing Engine     │  │
│  │                  │  │                  │  │                      │  │
│  │ - Calculate FOIR │  │ - Weighted model │  │ - Risk-based rates   │  │
│  │ - Max EMI calc   │  │ - Segment scores │  │ - Processing fees    │  │
│  │ - Eligible amt   │  │ - Explain factors│  │ - Total cost         │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────┘  │
│                                                                            │
│  ┌──────────────────┐  ┌──────────────────┐                             │
│  │   EMI Engine     │  │   PDF Engine     │                             │
│  │                  │  │                  │                             │
│  │ - Amortization   │  │ - Sanction PDF   │                             │
│  │ - Schedule gen   │  │ - Digital sign   │                             │
│  │ - Payment calc   │  │ - RBI compliance │                             │
│  └──────────────────┘  └──────────────────┘                             │
│                                                                            │
└────────────────────────────────┬───────────────────────────────────────────┘
                                 │
┌────────────────────────────────┴───────────────────────────────────────────┐
│                                                                             │
│                       PERSISTENCE LAYER                                     │
│                                                                             │
│  ┌─────────────────────────────────┐   ┌───────────────────────────────┐ │
│  │         MongoDB                  │   │          Redis                 │ │
│  │                                  │   │                                │ │
│  │  Collections:                    │   │  Keys:                         │ │
│  │  • users                         │   │  • otp:{email}                 │ │
│  │  • loan_applications             │   │  • session:{user_id}           │ │
│  │  • loans                         │   │  • blacklist:{token_id}        │ │
│  │  • audit_logs                    │   │  • cache:bureau:{pan}          │ │
│  │  • consent_records               │   │  • rate_limit:{ip}:{endpoint}  │ │
│  │                                  │   │                                │ │
│  │  GridFS:                         │   │  TTL:                          │ │
│  │  • sanction_letters.pdf          │   │  • OTP: 5 minutes              │ │
│  │  • uploaded_documents            │   │  • Bureau cache: 24 hours      │ │
│  │                                  │   │  • JWT blacklist: 24 hours     │ │
│  └─────────────────────────────────┘   └───────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Frontend Layer (Next.js)

**Technology**: Next.js 14 with App Router, TypeScript, TailwindCSS

**Key Pages**:
- `/` - Landing & OTP login
- `/dashboard` - User loan overview
- `/apply/[loanType]` - Chat-based application flow
- `/loans/[loanId]` - Loan details & EMI schedule
- `/admin` - Analytics dashboard (admin only)

**State Management**:
- React Query for server state
- Zustand for local UI state
- WebSocket (optional) for real-time chat updates

### 2. API Layer (FastAPI)

**Framework**: FastAPI with async support

**Middleware Stack**:
1. CORS middleware (origin restriction)
2. Rate limiting (slowapi)
3. JWT authentication dependency
4. Audit logging middleware
5. Error handling middleware

**Route Groups**:
- `/auth/*` - Authentication (OTP, JWT)
- `/loans/*` - Loan operations
- `/kyc/*` - KYC verification
- `/admin/*` - Admin operations (role-protected)
- `/bureau/*` - Internal credit bureau calls
- `/health` - Health check endpoint

### 3. Orchestration Layer (LangGraph)

**Purpose**: Stateful workflow management for loan application lifecycle

**Key Features**:
- **State persistence**: MongoDB checkpointer stores conversation state
- **Conditional branching**: Route based on verification results
- **Human-in-the-loop**: Pause at offer acceptance
- **Tool calling**: Integrates with deterministic engines
- **Error handling**: Graceful degradation and retry logic

**State Schema**:
```python
class LoanWorkflowState(TypedDict):
    application_id: str
    user_id: str
    loan_type: str
    stage: str  # Current workflow stage
    collected_data: Dict[str, Any]  # User inputs
    kyc_status: Optional[Dict]
    credit_report: Optional[Dict]
    risk_assessment: Optional[Dict]
    offer: Optional[Dict]
    conversation_history: List[Dict]
    errors: List[str]
    metadata: Dict[str, Any]
```

### 4. Business Logic Layer (Engines)

All engines are **pure Python functions** with clearly defined inputs/outputs. They are called as LangChain tools by the LangGraph workflow.

#### Policy Engine
- Loads JSON policy files by loan type
- Validates application against rules
- Returns list of violations or approval

#### KYC Engine
- Validates Aadhaar (12 digits) & PAN (format)
- Encrypts PII using AES-256 (Fernet)
- Returns masked values for LLM consumption
- 90% success rate simulation

#### Bureau Engine
- Fetches credit report from mock dataset (10K records)
- Simulates 1-3 second latency
- Caches results in Redis (24h TTL)
- Returns credit score, active loans, DPD history

#### Affordability Engine
- Calculates FOIR: `(existing_emi + proposed_emi) / income`
- Determines max eligible EMI based on policy FOIR limit
- Back-calculates max principal using EMI formula
- Returns affordable amount

#### Risk Engine
- Implements weighted scoring model:
  ```
  risk_score = (
      normalize(credit_score) * 0.40 +
      normalize(foir) * 0.30 +
      normalize(employment_stability) * 0.15 +
      normalize(city_tier) * 0.10 +
      normalize(bureau_flags) * 0.05
  )
  ```
- Segments: LOW (0-0.3), MEDIUM (0.3-0.6), HIGH (0.6-1.0)
- Provides explainability factors

#### Pricing Engine
- Determines interest rate based on risk segment
- Applies loan amount adjustments
- Calculates processing fee (policy-based %)
- Returns offer structure

#### EMI Engine
- Generates complete amortization schedule
- Formula: `EMI = P * r * (1+r)^n / ((1+r)^n - 1)`
- Returns month-by-month: principal, interest, balance

#### PDF Engine
- Uses ReportLab to generate sanction letter
- Includes all loan terms, RBI compliance clauses
- Simulates digital signature
- Stores in GridFS, returns download URL

### 5. Data Layer

#### MongoDB Collections

**users**:
```json
{
  "_id": ObjectId,
  "user_id": "uuid",
  "email": "user@example.com",
  "is_verified": true,
  "role": "user|admin",
  "created_at": ISODate,
  "updated_at": ISODate
}
```

**loan_applications**:
```json
{
  "_id": ObjectId,
  "application_id": "uuid",
  "user_id": "uuid",
  "loan_type": "personal_loan",
  "status": "PENDING|APPROVED|REJECTED|DISBURSED",
  "workflow_state": "collect_info|kyc_verify|...",
  "collected_data": {
    "income": 75000,
    "employment_type": "salaried",
    "requested_amount": 500000,
    "age": 35
  },
  "verification_data": {
    "kyc_status": "VERIFIED",
    "encrypted_aadhaar": "...",
    "encrypted_pan": "...",
    "credit_score": 750,
    "bureau_flags": []
  },
  "risk_assessment": {
    "risk_score": 0.25,
    "segment": "LOW",
    "factors": {...}
  },
  "offer": {
    "amount": 500000,
    "tenure_months": 36,
    "interest_rate": 12.5,
    "monthly_emi": 16680,
    "processing_fee": 10000
  },
  "conversation_history": [...],
  "created_at": ISODate,
  "updated_at": ISODate
}
```

**loans**:
```json
{
  "_id": ObjectId,
  "loan_id": "uuid",
  "application_id": "uuid",
  "user_id": "uuid",
  "principal": 500000,
  "tenure_months": 36,
  "interest_rate": 12.5,
  "monthly_emi": 16680,
  "status": "ACTIVE|CLOSED|DEFAULTED",
  "disbursement_date": ISODate,
  "emi_schedule": [
    {
      "month": 1,
      "emi": 16680,
      "principal_component": 11513,
      "interest_component": 5167,
      "remaining_balance": 488487
    },
    ...
  ],
  "next_due_date": ISODate,
  "sanction_letter_url": "...",
  "created_at": ISODate
}
```

**audit_logs**:
```json
{
  "_id": ObjectId,
  "user_id": "uuid",
  "application_id": "uuid",
  "action": "RISK_ASSESSMENT|KYC_VERIFICATION|OFFER_GENERATED",
  "decision": "APPROVED|REJECTED|PENDING",
  "risk_score": 0.25,
  "policy_version": "1.0.0",
  "timestamp": ISODate,
  "metadata": {...}
}
```

#### Redis Keys

- `otp:{email}` → `{ "hashed_otp": "...", "expiry": timestamp, "attempts": 0 }`
- `jwt_blacklist:{token_id}` → `1` (TTL 24h)
- `bureau_cache:{pan}` → `{ credit_report_json }` (TTL 24h)
- `rate_limit:{ip}:/auth/request-otp` → `{count}` (TTL 15min)

## Security Architecture

### Authentication Flow

```
1. User enters email
   ↓
2. Backend generates 6-digit OTP
   ↓
3. OTP hashed with bcrypt, stored in Redis (5min TTL)
   ↓
4. Email simulated (console log in dev)
   ↓
5. User enters OTP
   ↓
6. Backend verifies hash, checks expiry & attempts
   ↓
7. On success: Generate JWT token
   ↓
8. JWT includes: user_id, email, role, exp (24h)
   ↓
9. Frontend stores JWT (httpOnly cookie preferred)
   ↓
10. All subsequent requests include JWT in Authorization header
    ↓
11. FastAPI dependency validates JWT on protected routes
```

### PII Protection

**Encryption at Rest**:
- Aadhaar & PAN encrypted using AES-256 (Fernet) before MongoDB storage
- Encryption key stored in environment variable
- Decryption only when absolutely necessary (audit, compliance)

**Masking for LLM**:
- LLM never receives raw Aadhaar or PAN
- Masked format: `XXXX-XXXX-1234` (last 4 digits)
- LangGraph state only contains masked values

**Audit Trail**:
- Every PII access logged with user_id, timestamp, purpose
- Immutable audit logs (append-only)

### Rate Limiting

- OTP requests: Max 3 per 15 minutes per email
- Login attempts: Max 5 per hour per IP
- API calls: 100 per minute per user (authenticated)

## Data Flow: Loan Application Journey

```
1. User Login (OTP)
   ├─ User enters email → Backend generates OTP
   ├─ OTP stored in Redis (hashed) → Email simulated
   └─ User verifies OTP → JWT issued

2. Start Application
   ├─ User selects loan type (Personal)
   ├─ Frontend POST /loans/apply
   └─ Backend creates application_id, initializes LangGraph state

3. Chat-Based Data Collection
   ├─ LLM Node: collect_basic_info
   ├─ User provides: income, employment, amount, age
   ├─ Frontend POST /loans/{app_id}/chat for each message
   └─ LangGraph updates state.collected_data

4. KYC Verification
   ├─ LLM asks for Aadhaar & PAN
   ├─ Tool Call: verify_kyc_tool
   ├─ KYC Engine validates format, simulates verification
   ├─ PII encrypted, stored in MongoDB
   └─ Masked values returned to state

5. Credit Bureau Check
   ├─ Tool Call: fetch_credit_tool
   ├─ Bureau Engine looks up PAN in mock dataset
   ├─ Returns credit_score, active_loans, dpd_history
   ├─ Result cached in Redis (24h)
   └─ Conditional: If score < min → Rejection

6. Affordability Calculation
   ├─ Tool Call: calculate_affordability_tool
   ├─ FOIR = (existing_emi + proposed_emi) / income
   ├─ Max eligible amount calculated
   └─ State updated with affordable_amount

7. Risk Assessment
   ├─ Tool Call: assess_risk_tool
   ├─ Risk Engine applies weighted model
   ├─ Returns risk_score (0-1) and segment (LOW/MED/HIGH)
   └─ State updated with risk_assessment

8. Offer Generation
   ├─ Tool Call: generate_offer_tool
   ├─ Pricing Engine determines interest rate based on risk
   ├─ Calculates EMI for offered amount
   └─ State updated with offer details

9. LLM Explanation
   ├─ LLM Node: explain_offer
   ├─ Conversationally presents: amount, tenure, EMI, rate
   ├─ Explains why this offer (risk factors)
   └─ Asks for user acceptance

10. User Decision
    ├─ User accepts offer
    ├─ Frontend POST /loans/{app_id}/accept
    └─ LangGraph continues to sanction generation

11. Sanction Letter
    ├─ Tool Call: generate_sanction_pdf_tool
    ├─ PDF Engine creates professional sanction letter
    ├─ Includes all terms, RBI compliance clauses
    ├─ Stored in GridFS
    └─ URL returned for download

12. Disbursement Simulation
    ├─ Tool Call: simulate_disbursement_tool
    ├─ Mock NEFT/RTGS transaction
    ├─ Generates transaction_id, timestamp
    ├─ Loan marked as ACTIVE
    ├─ EMI schedule generated and stored
    └─ Audit log created

13. Post-Disbursement
    ├─ User can view loan in dashboard
    ├─ Download sanction letter
    ├─ View EMI schedule
    └─ Admin can see in analytics
```

## LLM Usage & Constraints

### What LLM Does

1. **Conversational Interface**: Natural language interactions with users
2. **Data Collection**: Asks structured questions to gather application info
3. **Tool Orchestration**: Decides when to call verification/calculation tools
4. **Explanation**: Translates policy decisions into user-friendly language
5. **Guidance**: Suggests alternative loan types if application rejected

### What LLM Does NOT Do

1. ❌ Approve or reject loans independently
2. ❌ Calculate risk scores or interest rates
3. ❌ Access raw PII (Aadhaar, PAN)
4. ❌ Modify policy rules
5. ❌ Make pricing decisions

### System Prompt Template

```
You are a professional loan processing assistant for an NBFC.

STRICT RULES:
1. You MUST call the appropriate tool for all decisions (KYC, credit check, risk assessment, pricing)
2. You NEVER approve or reject loans on your own - decisions come from policy engine
3. You NEVER see or handle raw Aadhaar or PAN numbers - only masked versions
4. You explain outcomes in a clear, compliant, customer-friendly manner
5. You collect information systematically following the workflow stages
6. If a rule is violated, you explain WHY using the policy_violations from the tool

CURRENT STAGE: {stage}
LOAN TYPE: {loan_type}

TOOLS AVAILABLE:
- verify_kyc_tool: Validate customer identity documents
- fetch_credit_tool: Retrieve credit bureau report
- calculate_affordability_tool: Determine eligible loan amount based on income
- assess_risk_tool: Calculate risk score and segment
- generate_offer_tool: Create loan offer with terms

CONVERSATION GUIDELINES:
- Be professional yet warm
- Ask one question at a time
- Validate inputs before proceeding
- Provide context for why information is needed
- Celebrate approvals, empathetically handle rejections
```

## Scaling Considerations

### Phase 2 Enhancements

1. **Multiple Loan Types**: Separate LangGraph workflows for Home, Vehicle, Business, Credit Card
2. **Document Processing**: OCR integration for Aadhaar, PAN, bank statements
3. **Real Bureau Integration**: Replace mock with actual CIBIL API (sandbox)
4. **ML Risk Scoring**: Train model on historical data, replace weighted formula
5. **Notification System**: Email, SMS for OTP, approvals, EMI reminders
6. **Background Jobs**: Celery for heavy tasks (PDF generation, email sending)

### Production Readiness

- **Load Balancing**: Multiple FastAPI instances behind Nginx
- **Database Sharding**: Partition MongoDB by user_id hash
- **Redis Cluster**: High availability for sessions
- **CDN**: Serve frontend static assets
- **Monitoring**: Prometheus + Grafana for metrics
- **Logging**: ELK stack (Elasticsearch, Logstash, Kibana)
- **CI/CD**: GitHub Actions for automated testing & deployment

## Compliance & Auditing

### RBI Digital Lending Guidelines

Following key principles:
1. **Transparency**: All charges disclosed upfront
2. **Privacy**: PII encrypted, consent-based usage
3. **Fair Practices**: No hidden fees or predatory terms
4. **Grievance Redressal**: Contact information in all communications
5. **Audit Trail**: Complete decision history maintained

### Audit Logging

Every critical action logged:
- User authentication attempts
- Application submissions
- KYC verifications
- Credit checks
- Risk assessments
- Approvals/rejections
- Disbursements
- EMI payments (Phase 2)

Log retention: 7 years (compliance requirement)

---

**Document Version**: 1.0.0  
**Last Updated**: March 5, 2026  
**Maintained By**: Development Team
