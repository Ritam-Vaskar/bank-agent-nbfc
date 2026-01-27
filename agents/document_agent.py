"""
Document Validation Agent

Simulate:
- Bank statement parsing
- Payslip verification
- Address match
"""

import random
from typing import Dict, Any, List

class DocumentAgent:
    def __init__(self):
        self.required_documents = [
            'bank_statement',
            'income_proof',
            'address_proof'
        ]
    
    def process(self, user_message: str, loan_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate uploaded documents
        Returns validation status and issues
        """
        
        # Check if user indicates documents are uploaded
        uploaded_keywords = ['upload', 'done', 'submitted', 'sent', 'ready', 'attached', 'provided']
        
        if any(keyword in user_message.lower() for keyword in uploaded_keywords):
            # Simulate document verification
            # In production, this would parse actual documents
            
            verification_success_rate = random.random()
            
            if verification_success_rate > 0.85:  # 15% chance of document issues
                # Document verification failed
                issues = []
                
                if random.random() > 0.5:
                    issues.append("Bank statement is older than 3 months")
                if random.random() > 0.7:
                    issues.append("Income proof signature mismatch")
                if random.random() > 0.8:
                    issues.append("Address on documents doesn't match Aadhaar")
                
                if not issues:
                    issues.append("Document quality is poor, please upload clearer copies")
                
                return {
                    'documents_ok': False,
                    'issues': issues,
                    'message': "Document verification issues found:\n" + "\n".join(f"- {issue}" for issue in issues) + "\n\nPlease re-upload the correct documents."
                }
            
            # All documents verified successfully
            # Mock parsing results
            avg_monthly_balance = random.randint(50000, 500000)
            monthly_salary = random.randint(30000, 150000)
            
            return {
                'documents_ok': True,
                'issues': [],
                'parsed_data': {
                    'avg_monthly_balance': avg_monthly_balance,
                    'monthly_salary': monthly_salary,
                    'address_verified': True,
                    'bank_name': 'HDFC Bank',
                    'employer_name': 'Tech Corp Pvt Ltd'
                },
                'message': f"""✅ All documents verified successfully!

Document Summary:
- Bank Statement: Verified (Avg Balance: ₹{avg_monthly_balance:,})
- Income Proof: Verified (Monthly Salary: ₹{monthly_salary:,})
- Address Proof: Verified (Matches Aadhaar)"""
            }
        
        # User hasn't uploaded yet
        return {
            'documents_ok': False,
            'issues': ['Documents not uploaded'],
            'message': """Please upload the following documents:

1. Bank Statement (Last 3 months)
2. Salary Slips / Income Proof (Last 3 months)
3. Address Proof (Utility bill/Passport/Driving License)

You can upload documents via the web interface or type 'documents uploaded' when ready."""
        }
