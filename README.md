# NBFC Digital Lending Platform

A production-grade digital lending platform with multi-stage policy-driven underwriting, simulating realistic NBFC loan lifecycle processes inspired by Tata Capital policies.

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Next.js)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │ Chat UI      │  │ Dashboard    │  │ Admin Analytics      │ │
│  └──────────────┘  └──────────────┘  └──────────────────────┘ │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST API / WebSocket
┌────────────────────────────┴────────────────────────────────────┐
│                      Backend (FastAPI)                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │            LangGraph Workflow Orchestrator                │  │
│  │  ┌────────┐  ┌────────┐  ┌────────┐  ┌──────────────┐   │  │
│  │  │ KYC    │→ │Credit  │→ │ Risk   │→ │ Offer Gener- │   │  │
│  │  │Verify  │  │Check   │  │Assess  │  │ation         │   │  │
│  │  └────────┘  └────────┘  └────────┘  └──────────────┘   │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         Deterministic Engines (Tools)                     │  │
│  │  • Policy Engine      • Risk Engine                       │  │
│  │  • KYC Engine         • Pricing Engine                    │  │
│  │  • Bureau Engine      • EMI Engine                        │  │
│  │  • Affordability      • PDF Engine                        │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┴───────────────────┐
        │                                        │
┌───────▼────────┐                      ┌────────▼────────┐
│   MongoDB      │                      │     Redis       │
│  • Users       │                      │  • OTP Sessions │
│  • Loans       │                      │  • JWT Blacklist│
│  • Applications│                      │  • Cache        │
│  • Audit Logs  │                      └─────────────────┘
└────────────────┘
```

## 🚀 Key Features

- **OTP-Based Authentication**: Secure email OTP flow with JWT tokens
- **LangGraph Orchestration**: Stateful loan workflow with conditional branching
- **Policy-Driven Underwriting**: JSON-based policy rules for multiple loan types
- **Risk-Based Pricing**: Weighted risk scoring model (credit score, FOIR, employment, city tier)
- **Mock Bureau Integration**: 10,000+ realistic credit profiles
- **FOIR Calculation**: Automated affordability assessment
- **Sanction Letter Generation**: Professional PDF with digital signature simulation
- **EMI Amortization**: Complete repayment schedule generation
- **Audit Logging**: Every decision point tracked for compliance
- **PII Encryption**: AES-256 encryption for sensitive data
- **Multi-Loan Support**: Personal, Home, Vehicle, Business, Credit Card (Phase 2)

## 🛠️ Technology Stack

**Backend:**
- Python 3.11+ with FastAPI
- LangGraph 0.2+ (workflow orchestration)
- LangChain + OpenAI GPT-4
- MongoDB (document store)
- Redis (sessions & caching)
- ReportLab (PDF generation)

**Frontend:**
- Next.js 14+ (App Router)
- TailwindCSS + Shadcn/UI
- React Query
- TypeScript

**DevOps:**
- Docker Compose
- Multi-stage Dockerfiles

## 📋 Prerequisites

- Docker Desktop installed and running
- OpenAI API key ([Get one here](https://platform.openai.com/api-keys))
- Git
- 4GB+ RAM available for containers
- Ports 3000, 8000, 27017, 6379 available

## 🚀 Quick Start

### 1. Clone and Configure

```bash
# Clone the repository
git clone https://github.com/Ritam-Vaskar/bank-agent-nbfc.git
cd bank-agent

# Copy environment template
cp .env.example .env

# Edit .env and add your OpenAI API key
# On Windows: notepad .env
# On macOS/Linux: nano .env
```

**Required environment variables to configure:**
- `OPENAI_API_KEY`: Your OpenAI API key
- `ENCRYPTION_KEY`: Generate using:
  ```bash
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```
- `JWT_SECRET_KEY`: Any strong random string (32+ characters)

### 2. Start the Platform

```bash
# Build and start all services
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build
```

**Services will start on:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- MongoDB: localhost:27017
- Redis: localhost:6379

### 3. Seed Mock Data

```bash
# In a new terminal, seed the database with mock records
docker-compose exec backend python scripts/seed_db.py

# Generate 10,000 mock credit bureau records (optional)
docker-compose exec backend python mock_data/generator.py --records 10000
```

### 4. Access the Platform

1. Open http://localhost:3000
2. Enter your email to receive OTP (check console logs: `docker-compose logs backend`)
3. Enter OTP to login
4. Apply for a Personal Loan via chat interface
5. Experience the complete loan journey!

## 📚 API Documentation

Once the backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

**Authentication:**
- `POST /auth/request-otp` - Request OTP for email
- `POST /auth/verify-otp` - Verify OTP and get JWT
- `GET /auth/me` - Get current user info

**Loan Application:**
- `POST /loans/apply` - Start new loan application
- `POST /loans/{application_id}/chat` - Send message in chat flow
- `GET /loans/applications` - List user's applications
- `POST /loans/{application_id}/accept` - Accept loan offer
- `GET /loans/{loan_id}/sanction-letter` - Download PDF

**Admin:**
- `GET /admin/applications` - All applications (admin only)
- `GET /admin/analytics/risk-distribution` - Risk analytics
- `GET /admin/audit-logs` - Audit trail

**Telegram:**
- `POST /telegram/webhook` - Telegram webhook receiver
- `POST /telegram/link-token` - Generate one-time account link code (auth required)
- `GET /telegram/link-status` - Get Telegram link status for current account
- `POST /telegram/unlink` - Unlink Telegram from current account

## 🤖 Telegram Bot Integration

Configure these backend environment variables:
- `TELEGRAM_BOT_TOKEN` - Telegram bot token from BotFather
- `TELEGRAM_WEBHOOK_SECRET` - Secret token used by Telegram webhook header (recommended)
- `TELEGRAM_BOT_USERNAME` - Bot username (used to build deep-link)
- `TELEGRAM_LINK_CODE_TTL_SECONDS` - One-time link code expiry (default 900)
- `TELEGRAM_DASHBOARD_URL` - Dashboard URL sent in Telegram confirmations

Link flow:
1. Login in dashboard and generate Telegram link code.
2. In Telegram bot chat, send `/link <code>` (or use deep-link).
3. Start a loan flow via `/new personal`, `/new home`, or `/new business`.
4. Telegram chat updates are saved under the same user account and visible in dashboard chats.

## 🏦 Loan Types & Policies

### Phase 1 (Current): Personal Loan
- Min Age: 21, Max Age: 60
- Min Credit Score: 700
- Min Income: ₹25,000/month
- FOIR Limit: 60%
- Interest Rates: 11.5% - 18% (based on risk)
- Max Tenure: 60 months

### Phase 2 (Planned):
- **Home Loan**: LTV-based, property valuation
- **Vehicle Loan**: Insurance mandatory
- **Business Loan**: GST + ITR verification
- **Credit Card**: Credit limit determination

Policy files located in: `backend/policies/`

## 🧪 Testing

### Manual Test Scenarios

**Scenario 1: Successful Application**
```
- Email: test@example.com
- Income: ₹75,000
- Employment: Salaried, 5 years
- Requested: ₹500,000
→ Should approve with LOW risk, ~12% interest
```

**Scenario 2: High Risk**
```
- Income: ₹30,000
- Credit Score: 650 (simulated from mock data)
- Existing EMI: ₹10,000
→ Should approve with HIGH risk, ~17% interest
```

**Scenario 3: Policy Violation**
```
- Age: 65
→ Should reject (exceeds max age)
```

**Scenario 4: Poor Credit**
```
- Credit Score: 550 (simulated)
→ Should reject (below minimum)
```

### Run Automated Tests (Phase 2)

```bash
docker-compose exec backend pytest -v
```

## 🔒 Security Features

- **JWT Authentication**: 24-hour expiry, refresh token support
- **Rate Limiting**: Max 3 OTP requests per 15 minutes
- **PII Encryption**: AES-256 for Aadhaar/PAN storage
- **Input Validation**: Pydantic models on all endpoints
- **PII Masking**: Raw data never sent to LLM
- **Audit Logging**: Every decision recorded
- **CORS Protection**: Restricted origins
- **Role-Based Access**: User vs Admin permissions

## 📊 System Architecture Details

### LangGraph Workflow Nodes

1. **collect_basic_info**: LLM gathers income, employment, amount
2. **verify_kyc**: Validates Aadhaar & PAN (90% success simulation)
3. **fetch_credit_score**: Retrieves bureau data from mock dataset
4. **calculate_affordability**: FOIR-based eligible amount
5. **run_risk_assessment**: Weighted scoring (credit 40%, FOIR 30%, etc.)
6. **generate_offer**: Risk-based interest rate determination
7. **explain_offer**: LLM presents terms conversationally
8. **await_acceptance**: User decision point
9. **generate_sanction**: PDF sanction letter creation
10. **simulate_disbursement**: Mock NEFT/RTGS transaction

### Risk Scoring Model

```
Risk Score = (
    Credit Score Factor    × 0.40 +
    FOIR Factor           × 0.30 +
    Employment Stability  × 0.15 +
    City Tier            × 0.10 +
    Bureau Flags         × 0.05
)

Segments:
- 0.0-0.3: LOW risk    → 11.5-12% interest
- 0.3-0.6: MEDIUM risk → 14-15% interest
- 0.6-1.0: HIGH risk   → 17-18% interest
```

## 🗂️ Project Structure

```
bank-agent/
├── backend/
│   ├── auth/              # OTP + JWT services
│   ├── engines/           # Deterministic engines (KYC, Risk, etc.)
│   ├── models/            # Pydantic models
│   ├── policies/          # JSON policy rules
│   ├── routes/            # FastAPI endpoints
│   ├── workflows/         # LangGraph definitions
│   ├── mock_data/         # Generators & seeds
│   ├── scripts/           # Database seeding
│   └── main.py            # FastAPI app entry
├── frontend/
│   ├── app/               # Next.js pages (App Router)
│   ├── components/        # React components
│   ├── hooks/             # Custom hooks
│   └── lib/               # API client, utilities
├── docs/
│   ├── ARCHITECTURE.md    # Detailed architecture
│   ├── TECHNICAL_DOCUMENTATION.md  # Full technical design and agent flow
│   └── API.md             # Extended API docs
├── docker-compose.yml
├── .env.example
└── README.md
```

## 🐛 Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs backend
docker-compose logs frontend

# Restart services
docker-compose restart
```

### Port conflicts
```bash
# Check what's using the ports
# Windows:
netstat -ano | findstr :8000
netstat -ano | findstr :3000

# macOS/Linux:
lsof -i :8000
lsof -i :3000
```

### MongoDB connection issues
```bash
# Verify MongoDB is healthy
docker-compose ps
docker-compose exec mongodb mongosh --eval "db.adminCommand('ping')"
```

### Frontend can't reach backend
```bash
# Check NEXT_PUBLIC_API_URL in frontend container
docker-compose exec frontend printenv | grep API
```

## 📈 Roadmap

**Phase 1 (Current):**
- ✅ Personal Loan complete flow
- ✅ LangGraph orchestration
- ✅ Mock data generators
- ✅ Basic admin dashboard

**Phase 2 (Next):**
- [ ] Home, Vehicle, Business, Credit Card loans
- [ ] Enhanced analytics dashboard
- [ ] Document upload & processing
- [ ] Prepayment calculator
- [ ] Comprehensive test suite

**Phase 3 (Future):**
- [ ] Real-time notifications
- [ ] Multi-language support
- [ ] Mobile app (React Native)
- [ ] ML-based credit scoring

## 🤝 Contributing

This is a hackathon/educational project demonstrating NBFC digital lending architecture.

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- Architecture inspired by Tata Capital's digital lending practices
- Policies based on RBI digital lending guidelines
- Built with LangGraph for stateful LLM workflows

## 📞 Support

For issues or questions:
- GitHub Issues: https://github.com/Ritam-Vaskar/bank-agent-nbfc/issues
- Email: ritamvaskar@example.com

---

**⚠️ Disclaimer**: This is a simulation platform for educational/hackathon purposes. Not intended for real financial transactions. Mock data and dummy integrations only.

**Built with ❤️ for the future of digital lending**
