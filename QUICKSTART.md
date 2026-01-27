# Bank Agent - Quick Start Guide

## 🚀 Getting Started in 5 Minutes

### Prerequisites
- Docker Desktop installed
- 8GB RAM minimum
- Ports 3000, 5000, 8000 available

### Installation

1. **Clone or extract the project**
```bash
cd bank-agent
```

2. **Start all services with Docker**
```bash
docker-compose up --build
```

Wait for all services to start (2-3 minutes on first run)

3. **Access the application**
- Frontend: http://localhost:3000
- Backend API: http://localhost:5000
- Agent Service: http://localhost:8000

4. **Login**
```
Email: demo@example.com
Password: demo123
```

5. **Start your first loan application!**
- Click "Chat" or "Start New Application"
- Follow the conversational flow

---

## 💬 Sample Conversation

**You:** I want a personal loan

**Agent:** Great! How much would you like to borrow?

**You:** 5 lakhs

**Agent:** And for how many months?

**You:** 36 months

**Agent:** Perfect! Now let's verify your identity. Please provide your PAN.

**You:** ABCDE1234F

**Agent:** ✅ PAN verified! Now provide your Aadhaar number.

**You:** 123456789012

**Agent:** ✅ Identity verified! Checking credit profile...

**Agent:** ✅ Credit approved! Approved amount: ₹500,000. Please upload documents.

**You:** documents uploaded

**Agent:** ✅ Documents verified! Here's your offer...

**You:** accept

**Agent:** 🎉 Congratulations! Your loan is sanctioned!

---

## 🔧 Troubleshooting

### Services not starting?
```bash
docker-compose down
docker-compose up --build
```

### Check service health:
```bash
curl http://localhost:5000/health
curl http://localhost:8000/health
```

### View logs:
```bash
docker-compose logs -f
```

---

## 📱 Features to Try

1. **Complete Loan Journey** - Apply for a loan from start to finish
2. **Dashboard** - View all your applications
3. **Dark Mode** - Toggle in the navbar
4. **Admin Panel** - Login as admin@example.com / admin123

---

## 🎯 Next Steps

- Read [README.md](README.md) for full documentation
- Explore the API at http://localhost:5000
- Check agent responses at http://localhost:8000
- Customize agents in `agents/` directory

---

**Need help?** Check the logs or open an issue!
