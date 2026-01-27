# Bank Agent - AI-Powered Loan Processing System

<div align="center">

![Bank Agent](https://img.shields.io/badge/AI-Powered-blue)
![Next.js](https://img.shields.io/badge/Next.js-14-black)
![Node.js](https://img.shields.io/badge/Node.js-20-green)
![Python](https://img.shields.io/badge/Python-3.11-yellow)
![License](https://img.shields.io/badge/license-MIT-blue)

**A complete, production-ready AI agent system for automated loan processing with conversational UI**

[Features](#features) • [Tech Stack](#tech-stack) • [Quick Start](#quick-start) • [Architecture](#architecture) • [API Docs](#api-documentation)

</div>

---

## 🎯 Overview

Bank Agent is an intelligent, multi-agent loan processing system that guides users through the entire loan journey - from initial inquiry to sanction letter - all through natural conversation. Built with modern tech stack and following MCP (Model Context Protocol) architecture.

### ✨ Key Features

- **🤖 AI-Powered Agents** - 6 specialized agents handling different stages
- **💬 Conversational UI** - Chat-based loan application process
- **🔐 Secure & Compliant** - Bank-grade security with audit trails
- **⚡ Real-time Processing** - Instant credit decisions and approvals
- **📊 Admin Dashboard** - Complete oversight and manual review capabilities
- **🎨 Modern UI** - Beautiful, responsive design with dark mode
- **🐳 Docker Ready** - One-command deployment

---

## 🏗️ Architecture

### State Machine Flow

```
INIT → SALES → KYC → CREDIT → DOCUMENTS → OFFER → ACCEPTANCE → SANCTION → COMPLETE
```

### Agent Responsibilities

| Agent | Purpose | Output |
|-------|---------|--------|
| **Master Agent** | Orchestrates entire flow | Next agent + user message |
| **Sales Agent** | Collects loan intent | Loan type, amount, tenure |
| **KYC Agent** | Verifies identity | Masked PAN/Aadhaar |
| **Underwriting Agent** | Credit assessment | Risk level, approved amount |
| **Document Agent** | Validates documents | Verification status |
| **Sanction Agent** | Generates letter | Sanction ID + letter |

---

## 📚 Tech Stack

### Frontend
- **Next.js 14** - React framework with App Router
- **Tailwind CSS** - Utility-first styling
- **Framer Motion** - Smooth animations
- **NextAuth.js** - Authentication
- **Axios** - HTTP client

### Backend
- **Node.js + Express** - REST API server
- **MongoDB** - Primary database
- **Redis** - Session & cache storage
- **JWT** - Token-based auth

### AI Agents
- **Python 3.11 + Flask** - Agent runtime
- **JSON-only communication** - Structured outputs
- **Mock APIs** - CIBIL, Aadhaar, PAN verification

### Infrastructure
- **Docker Compose** - Container orchestration
- **MongoDB** - Document storage
- **Redis** - Caching layer

---

## 🚀 Quick Start

### Prerequisites

- **Docker** & **Docker Compose** (Recommended)
- OR: **Node.js 20+**, **Python 3.11+**, **MongoDB**, **Redis**

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone <repo-url>
cd bank-agent

# Start all services
docker-compose up --build

# Access the application
# Frontend: http://localhost:3000
# Backend: http://localhost:5000
# Agents: http://localhost:8000
```

### Option 2: Manual Setup

#### 1. Backend Setup

```bash
cd backend
npm install
cp .env.example .env  # Edit with your config
npm run dev
```

#### 2. Python Agents Setup

```bash
cd agents
pip install -r requirements.txt
python master_agent.py
```

#### 3. Frontend Setup

```bash
cd frontend
npm install
cp .env.local.example .env.local  # Edit with your config
npm run dev
```

#### 4. Database Setup

```bash
# Start MongoDB (if not using Docker)
mongod --dbpath /path/to/data

# Start Redis
redis-server

# Seed demo users
cd backend
node seed/demo_users.js
```

---

## 🎮 Usage

### Demo Credentials

| Role | Email | Password |
|------|-------|----------|
| User | demo@example.com | demo123 |
| Admin | admin@example.com | admin123 |

### Sample Loan Journey

1. **Visit** http://localhost:3000
2. **Sign In** with demo credentials
3. **Start Chat** - "I want a personal loan"
4. **Provide Details**:
   - Amount: "5 lakhs"
   - Tenure: "36 months"
5. **KYC Verification**:
   - PAN: `ABCDE1234F`
   - Aadhaar: `123456789012`
6. **Documents**: Type "documents uploaded"
7. **Accept Offer**: Type "accept"
8. **Get Sanction Letter** 🎉

---

## 📁 Project Structure

```
bank-agent/
├── frontend/               # Next.js application
│   ├── app/
│   │   ├── auth/          # Authentication pages
│   │   ├── chat/          # Chat interface
│   │   └── dashboard/     # User dashboard
│   ├── components/        # Reusable components
│   └── lib/               # Utilities
│
├── backend/               # Express API server
│   ├── routes/
│   │   ├── auth.routes.js
│   │   ├── chat.routes.js
│   │   └── admin.routes.js
│   ├── middleware/
│   │   ├── auth.js
│   │   ├── rateLimiter.js
│   │   └── auditLogger.js
│   └── server.js
│
├── agents/                # Python AI agents
│   ├── master_agent.py    # Orchestrator
│   ├── sales_agent.py
│   ├── kyc_agent.py
│   ├── underwriting_agent.py
│   ├── document_agent.py
│   └── sanction_agent.py
│
├── mock_services/         # Mock external APIs
│   ├── cibil_api.py
│   ├── aadhaar_api.py
│   ├── pan_api.py
│   └── bank_statement_api.py
│
├── schemas/               # Database models
│   ├── user.schema.js
│   ├── loan.schema.js
│   └── audit.schema.js
│
├── seed/                  # Initial data
│   └── demo_users.js
│
└── docker-compose.yml     # Container orchestration
```

---

## 🔒 Security Features

### Authentication
- ✅ JWT with 15-minute access tokens
- ✅ 7-day refresh tokens
- ✅ HttpOnly cookies
- ✅ Password hashing with bcrypt

### API Security
- ✅ Rate limiting (60 req/min)
- ✅ CORS configuration
- ✅ Helmet security headers
- ✅ Input validation (Joi/Zod)

### Data Security
- ✅ PII masking (PAN: XXXXX1234X)
- ✅ SHA-256 hashing for IDs
- ✅ Immutable audit logs
- ✅ No raw ID storage

---

## 📊 API Documentation

### Authentication Endpoints

#### Sign Up
```http
POST /api/auth/signup
Content-Type: application/json

{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "password123"
}
```

#### Sign In
```http
POST /api/auth/signin
Content-Type: application/json

{
  "email": "john@example.com",
  "password": "password123"
}

Response:
{
  "success": true,
  "accessToken": "eyJhbGc...",
  "refreshToken": "eyJhbGc...",
  "user": { ... }
}
```

### Chat Endpoints

#### Send Message
```http
POST /api/chat/message
Content-Type: application/json
Authorization: Bearer <token>

{
  "message": "I want a personal loan",
  "loanId": "optional-existing-loan-id",
  "userId": "user-id"
}

Response:
{
  "success": true,
  "reply": "Great! How much would you like to borrow?",
  "loanId": "65abc123...",
  "state": "SALES",
  "completed": false
}
```

### Loan Endpoints

#### Get User Loans
```http
GET /api/loans/user
Authorization: Bearer <token>

Response:
{
  "success": true,
  "loans": [...]
}
```

### Admin Endpoints

#### Get All Loans
```http
GET /api/admin/loans?state=SALES&page=1&limit=20
Authorization: Bearer <admin-token>
```

#### Get Stats
```http
GET /api/admin/stats
Authorization: Bearer <admin-token>

Response:
{
  "success": true,
  "stats": {
    "totalLoans": 150,
    "activeLoans": 45,
    "completedLoans": 105,
    ...
  }
}
```

---

## 🧪 Testing

### Test Mock APIs

```bash
# Test CIBIL
curl http://localhost:8000/mock/cibil?pan=ABCDE1234F

# Test Aadhaar
curl http://localhost:8000/mock/aadhaar?number=123456789012

# Test Master Agent
curl -X POST http://localhost:8000/master \
  -H "Content-Type: application/json" \
  -d '{
    "loan_id": "test123",
    "user_message": "I want a personal loan",
    "current_state": "INIT",
    "loan_data": {}
  }'
```

---

## 🎨 UI Features

### Modern Design
- ✨ Gradient hero sections
- 🎭 Smooth animations with Framer Motion
- 🌙 Dark mode support
- 📱 Fully responsive
- 🎯 Accessible components

### Chat Interface
- 💬 Real-time message streaming
- 🤖 Bot/User message differentiation
- ⏱️ Timestamps
- 📍 State indicators
- 🎨 Beautiful message bubbles

### Dashboard
- 📊 Application statistics
- 📈 Progress tracking
- 🔔 Status indicators
- 📋 Application history

---

## 🔄 Development Workflow

### Hot Reload

All services support hot reload:
- Frontend: Next.js auto-reload
- Backend: Nodemon
- Agents: Python auto-reload

### Adding New Agents

1. Create agent file in `agents/`
2. Implement `process()` method
3. Return JSON with required fields
4. Register in `master_agent.py`

```python
class NewAgent:
    def process(self, user_message, loan_data):
        return {
            'status': 'success',
            'data': {},
            'message': 'Response to user'
        }
```

---

## 📈 Scaling Considerations

### Horizontal Scaling
- Load balance backend instances
- Separate agent services
- Redis cluster for sessions
- MongoDB replica set

### Performance
- Redis caching for frequently accessed data
- Database indexing on userId, state
- Agent response caching
- CDN for static assets

---

## 🐛 Troubleshooting

### Common Issues

**Port Already in Use**
```bash
# Kill process on port 3000, 5000, or 8000
npx kill-port 3000 5000 8000
```

**MongoDB Connection Error**
```bash
# Check MongoDB is running
docker ps | grep mongodb
# Or restart
docker-compose restart mongodb
```

**Agent Service Not Responding**
```bash
# Check logs
docker-compose logs agents
# Restart service
docker-compose restart agents
```

---

## 📝 Environment Variables

### Frontend (.env.local)
```env
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-secret-key
BACKEND_URL=http://localhost:5000
```

### Backend (.env)
```env
PORT=5000
MONGODB_URI=mongodb://mongodb:27017/bank_agent
REDIS_URL=redis://redis:6379
JWT_SECRET=your-jwt-secret
JWT_REFRESH_SECRET=your-refresh-secret
AGENT_SERVICE_URL=http://localhost:8000
```

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open Pull Request

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file

---

## 🎯 Roadmap

- [ ] WhatsApp integration
- [ ] Voice-based loan application
- [ ] AI-powered document OCR
- [ ] Multi-language support
- [ ] Mobile apps (React Native)
- [ ] Real CIBIL/Aadhaar integration
- [ ] E-sign integration
- [ ] Payment gateway integration

---

## 👥 Support

- 📧 Email: support@bankagent.com
- 💬 Discord: [Join our community](#)
- 📚 Docs: [Full documentation](#)
- 🐛 Issues: [GitHub Issues](#)

---

<div align="center">

**Built with ❤️ for the future of banking**

⭐ Star us on GitHub if you find this helpful!

</div>
