"""
Master Agent - MCP Orchestrator

Responsibilities:
- Maintain loan journey state machine
- Decide which agent to invoke next
- Validate agent outputs
- Handle failure & retries
- Produce final user-facing message

State machine: INIT → SALES → KYC → CREDIT → DOCUMENTS → OFFER → ACCEPTANCE → SANCTION → COMPLETE
"""

from flask import Flask, request, jsonify
from typing import Dict, Any
import sys
import os
import json

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sales_agent import SalesAgent
from kyc_agent import KYCAgent
from underwriting_agent import UnderwritingAgent
from document_agent import DocumentAgent
from sanction_agent import SanctionAgent

app = Flask(__name__)

class MasterAgent:
    def __init__(self):
        self.sales_agent = SalesAgent()
        self.kyc_agent = KYCAgent()
        self.underwriting_agent = UnderwritingAgent()
        self.document_agent = DocumentAgent()
        self.sanction_agent = SanctionAgent()
        
        self.state_transitions = {
            'INIT': 'SALES',
            'SALES': 'KYC',
            'KYC': 'CREDIT',
            'CREDIT': 'DOCUMENTS',
            'DOCUMENTS': 'OFFER',
            'OFFER': 'ACCEPTANCE',
            'ACCEPTANCE': 'SANCTION',
            'SANCTION': 'COMPLETE'
        }
    
    def process(self, loan_id: str, user_message: str, current_state: str, loan_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main orchestration logic
        Returns both system_action (next agent) and user_message (natural language)
        """
        
        # Determine current agent based on state
        if current_state == 'INIT' or current_state == 'SALES':
            result = self.sales_agent.process(user_message, loan_data)
            
            if result['completed']:
                # Sales completed, move to KYC
                return {
                    'next_agent': 'kyc_agent',
                    'state': 'KYC',
                    'state_update': result['collected'],
                    'user_message': result['reply'] + "\n\nNow let's verify your identity. Please provide your PAN number (format: ABCDE1234F).",
                    'completed': False
                }
            else:
                return {
                    'next_agent': 'sales_agent',
                    'state': 'SALES',
                    'state_update': result['collected'],
                    'user_message': result['reply'],
                    'completed': False
                }
        
        elif current_state == 'KYC':
            result = self.kyc_agent.process(user_message, loan_data)
            
            if result['kyc_status'] == 'VERIFIED':
                return {
                    'next_agent': 'underwriting_agent',
                    'state': 'CREDIT',
                    'state_update': {
                        'kyc_verified': True,
                        'masked_pan': result['masked_data'].get('pan'),
                        'masked_aadhaar': result['masked_data'].get('aadhaar')
                    },
                    'user_message': "✅ Identity verified successfully! Now checking your credit profile...",
                    'completed': False
                }
            elif result['kyc_status'] == 'PENDING':
                return {
                    'next_agent': 'kyc_agent',
                    'state': 'KYC',
                    'state_update': {},
                    'user_message': result['reply'],
                    'completed': False
                }
            else:
                return {
                    'next_agent': 'kyc_agent',
                    'state': 'KYC',
                    'state_update': {},
                    'user_message': "❌ KYC verification failed. " + result['reply'],
                    'completed': False
                }
        
        elif current_state == 'CREDIT':
            result = self.underwriting_agent.process(loan_data)
            
            # Check if high risk
            if result['risk_level'] == 'HIGH':
                return {
                    'next_agent': 'manual_review',
                    'state': 'CREDIT',
                    'state_update': result,
                    'user_message': "⚠️ Your application requires manual review. Our team will contact you within 24 hours.",
                    'completed': False
                }
            
            return {
                'next_agent': 'document_agent',
                'state': 'DOCUMENTS',
                'state_update': result,
                'user_message': f"""✅ Credit Assessment Complete!

Credit Score: {result['credit_score']}
Risk Level: {result['risk_level']}
Approved Amount: ₹{result['approved_amount']:,}
FOIR: {result['foir']}%

{result['reasoning']}

Next, please upload your documents:
1. Recent bank statements (last 3 months)
2. Salary slips or income proof
3. Address proof

Type 'documents uploaded' when ready.""",
                'completed': False
            }
        
        elif current_state == 'DOCUMENTS':
            result = self.document_agent.process(user_message, loan_data)
            
            if result['documents_ok']:
                # Calculate EMI
                loan_amount = loan_data.get('approved_amount', loan_data.get('loan_amount', 0))
                tenure = loan_data.get('tenure', 12)
                interest_rate = 12.5
                
                monthly_rate = interest_rate / 12 / 100
                emi = loan_amount * monthly_rate * ((1 + monthly_rate) ** tenure) / (((1 + monthly_rate) ** tenure) - 1)
                
                return {
                    'next_agent': 'offer',
                    'state': 'OFFER',
                    'state_update': {
                        'documents_verified': True,
                        'emi': round(emi, 2),
                        'interest_rate': interest_rate
                    },
                    'user_message': f"""✅ Documents Verified!

LOAN OFFER:
━━━━━━━━━━━━━━━━━━━━
Loan Amount: ₹{loan_amount:,}
Interest Rate: {interest_rate}% per annum
Tenure: {tenure} months
EMI: ₹{round(emi, 2):,}
Total Payable: ₹{round(emi * tenure, 2):,}

Do you accept this offer? (Type 'accept' or 'reject')""",
                    'completed': False
                }
            else:
                return {
                    'next_agent': 'document_agent',
                    'state': 'DOCUMENTS',
                    'state_update': {},
                    'user_message': "⚠️ " + result.get('message', 'Please upload valid documents.'),
                    'completed': False
                }
        
        elif current_state == 'OFFER':
            if 'accept' in user_message.lower():
                return {
                    'next_agent': 'sanction_agent',
                    'state': 'SANCTION',
                    'state_update': {'offer_accepted': True},
                    'user_message': "✅ Offer accepted! Generating your sanction letter...",
                    'completed': False
                }
            elif 'reject' in user_message.lower():
                return {
                    'next_agent': 'sales_agent',
                    'state': 'SALES',
                    'state_update': {'offer_rejected': True},
                    'user_message': "We understand. Would you like to apply for a different loan amount or tenure?",
                    'completed': False
                }
            else:
                return {
                    'next_agent': 'offer',
                    'state': 'OFFER',
                    'state_update': {},
                    'user_message': "Please respond with 'accept' to proceed or 'reject' to decline the offer.",
                    'completed': False
                }
        
        elif current_state == 'SANCTION':
            result = self.sanction_agent.generate(loan_data)
            
            return {
                'next_agent': 'complete',
                'state': 'COMPLETE',
                'state_update': {
                    'sanction_id': result['sanction_id'],
                    'sanction_letter': result['letter'],
                    'signature_hash': result['signature_hash']
                },
                'user_message': f"""🎉 CONGRATULATIONS! Your loan is SANCTIONED!

Sanction ID: {result['sanction_id']}

{result['letter']}

Digital Signature: {result['signature_hash']}

Your loan will be disbursed within 2-3 business days.
Thank you for choosing our services!""",
                'completed': True
            }
        
        else:
            return {
                'next_agent': 'sales_agent',
                'state': 'INIT',
                'state_update': {},
                'user_message': "Let's start fresh. What kind of loan are you looking for?",
                'completed': False
            }

master_agent = MasterAgent()

@app.route('/master', methods=['POST'])
def process_message():
    try:
        data = request.get_json()
        
        loan_id = data.get('loan_id')
        user_message = data.get('user_message', '')
        current_state = data.get('current_state', 'INIT')
        loan_data = data.get('loan_data', {})
        
        result = master_agent.process(loan_id, user_message, current_state, loan_data)
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"Error in master agent: {str(e)}")
        return jsonify({
            'error': str(e),
            'user_message': 'Sorry, something went wrong. Please try again.'
        }), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'agent': 'master'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
