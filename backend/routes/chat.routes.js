const express = require('express');
const axios = require('axios');
const { v4: uuidv4 } = require('uuid');
const Loan = require('../schemas/loan.schema');
const Audit = require('../schemas/audit.schema');
const auth = require('../middleware/auth');

const router = express.Router();

// Python agent service URL
const AGENT_SERVICE_URL = process.env.AGENT_SERVICE_URL || 'http://localhost:8000';

// Send message
router.post('/message', async (req, res) => {
  try {
    const { message, loanId, userId } = req.body;

    let loan;

    // Get or create loan
    if (loanId) {
      loan = await Loan.findById(loanId);
      if (!loan) {
        return res.status(404).json({
          success: false,
          message: 'Loan not found'
        });
      }
    } else {
      // Create new loan
      loan = new Loan({
        userId: userId || 'guest',
        state: 'INIT',
        data: {},
        riskLevel: null
      });
      await loan.save();
    }

    // Call master agent
    try {
      const agentResponse = await axios.post(`${AGENT_SERVICE_URL}/master`, {
        loan_id: loan._id.toString(),
        user_message: message,
        current_state: loan.state,
        loan_data: loan.data
      }, {
        timeout: 30000
      });

      const { next_agent, state_update, user_message, completed, state } = agentResponse.data;

      // Update loan
      loan.state = state || loan.state;
      loan.data = { ...loan.data, ...state_update };
      
      if (state_update.risk_level) {
        loan.riskLevel = state_update.risk_level;
      }

      await loan.save();

      // Log audit
      const audit = new Audit({
        loanId: loan._id,
        agent: next_agent || 'master_agent',
        action: `State: ${loan.state}`,
        userId: userId || 'guest'
      });
      await audit.save();

      res.json({
        success: true,
        reply: user_message,
        loanId: loan._id,
        state: loan.state,
        completed: completed || false
      });

    } catch (agentError) {
      console.error('Agent service error:', agentError.message);
      
      // Fallback response if agent service is down
      const fallbackMessage = getFallbackMessage(loan.state, message);
      
      res.json({
        success: true,
        reply: fallbackMessage,
        loanId: loan._id,
        state: loan.state,
        completed: false
      });
    }

  } catch (error) {
    console.error('Chat error:', error);
    res.status(500).json({
      success: false,
      message: error.message
    });
  }
});

// Get loan details
router.get('/loan/:loanId', auth, async (req, res) => {
  try {
    const loan = await Loan.findById(req.params.loanId);
    
    if (!loan) {
      return res.status(404).json({
        success: false,
        message: 'Loan not found'
      });
    }

    res.json({
      success: true,
      loan
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      message: error.message
    });
  }
});

// Fallback messages when agent service is unavailable
function getFallbackMessage(state, userMessage) {
  const lowerMsg = userMessage.toLowerCase();

  switch (state) {
    case 'INIT':
    case 'SALES':
      if (lowerMsg.includes('personal') || lowerMsg.includes('loan')) {
        return "Great! I'd be happy to help you with a personal loan. What amount are you looking to borrow?";
      }
      if (lowerMsg.match(/\d+/)) {
        return "Thank you. And for how many months would you like this loan? (typically 12-60 months)";
      }
      return "I'm here to help you with your loan application. What type of loan are you interested in?";

    case 'KYC':
      return "Now I'll need to verify your identity. Please provide your PAN number.";

    case 'CREDIT':
      return "We're checking your credit profile. This will just take a moment...";

    case 'DOCUMENTS':
      return "Please upload your recent bank statements and income proof.";

    default:
      return "Thank you for your information. We're processing your application.";
  }
}

module.exports = router;
