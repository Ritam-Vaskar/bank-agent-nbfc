"""
Sanction Letter Agent

Generate a sanction letter.

Include:
- Loan amount
- EMI
- Interest
- Tenure
- Compliance text

Add:
- mock digital signature hash
- timestamp
"""

import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any

class SanctionAgent:
    def generate(self, loan_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate sanction letter
        Returns sanction ID, letter text, and signature hash
        """
        
        # Generate unique sanction ID
        sanction_id = f"SL{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:8].upper()}"
        
        # Extract loan details
        loan_amount = loan_data.get('approved_amount', loan_data.get('loan_amount', 0))
        tenure = loan_data.get('tenure', 12)
        interest_rate = loan_data.get('interest_rate', 12.5)
        emi = loan_data.get('emi', 0)
        
        # Calculate total payable
        total_payable = round(emi * tenure, 2)
        total_interest = round(total_payable - loan_amount, 2)
        
        # Get customer details
        customer_name = loan_data.get('pan_name', loan_data.get('aadhaar_name', 'Valued Customer'))
        loan_type = loan_data.get('loan_type', 'Personal Loan')
        
        # Generate sanction date and validity
        sanction_date = datetime.now()
        validity_date = sanction_date + timedelta(days=30)
        
        # Create sanction letter
        letter = f"""
╔══════════════════════════════════════════════════════════════╗
║                    LOAN SANCTION LETTER                       ║
╚══════════════════════════════════════════════════════════════╝

Sanction ID: {sanction_id}
Date: {sanction_date.strftime('%d %B %Y')}

Dear {customer_name},

We are pleased to inform you that your loan application has been 
APPROVED and SANCTIONED.

LOAN DETAILS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Loan Type:            {loan_type}
Sanctioned Amount:    ₹{loan_amount:,}
Interest Rate:        {interest_rate}% per annum
Loan Tenure:          {tenure} months
Monthly EMI:          ₹{emi:,}
Total Interest:       ₹{total_interest:,}
Total Payable:        ₹{total_payable:,}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REPAYMENT SCHEDULE:
First EMI Due Date:   {(sanction_date + timedelta(days=30)).strftime('%d %B %Y')}
Last EMI Due Date:    {(sanction_date + timedelta(days=30*tenure)).strftime('%d %B %Y')}

TERMS AND CONDITIONS:
1. This sanction is valid until {validity_date.strftime('%d %B %Y')}
2. Loan amount will be disbursed within 2-3 business days
3. Processing fee of 2% + GST will be deducted from loan amount
4. Late payment charges: 2% per month on overdue amount
5. Pre-payment charges: 2% on principal outstanding (after 6 months)
6. Post-dated cheques (PDCs) for EMIs must be submitted before disbursal
7. Insurance coverage as per bank norms is mandatory

COMPLIANCE STATEMENT:
This loan is sanctioned as per RBI guidelines and internal credit policy.
Customer has been verified through KYC process and credit assessment.
All documents have been verified and found satisfactory.

DISCLAIMER:
- Interest rate is subject to change as per bank policy
- Loan disbursal is subject to submission of all required documents
- Bank reserves the right to recall the loan in case of default
- Customer must inform bank of any change in contact details/employment

We look forward to serving you.

For any queries, contact: support@bankagent.com | 1800-XXX-XXXX

Thank you for choosing our services!

Yours sincerely,
Credit Operations Team
Bank Agent NBFC

---
This is a computer-generated document and does not require physical signature.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        # Generate digital signature hash
        signature_data = f"{sanction_id}{loan_amount}{tenure}{sanction_date.isoformat()}"
        signature_hash = hashlib.sha256(signature_data.encode()).hexdigest()
        
        return {
            'sanction_id': sanction_id,
            'letter': letter,
            'signature_hash': signature_hash[:32],  # First 32 chars
            'timestamp': sanction_date.isoformat()
        }
