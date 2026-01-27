"""
Sales Agent - Loan Intent Collection

Goal:
- Collect loan intent conversationally
- Reduce drop-offs
- Ask ONE question at a time

Required fields:
- loan_type
- loan_amount
- tenure
"""

import re
from typing import Dict, Any

class SalesAgent:
    def __init__(self):
        self.required_fields = ['loan_type', 'loan_amount', 'tenure']
    
    def process(self, user_message: str, loan_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process user message and collect loan details
        Returns JSON with completion status and reply
        """
        
        collected = loan_data.copy()
        missing = []
        
        # Extract loan type
        if 'loan_type' not in collected or not collected['loan_type']:
            if any(word in user_message.lower() for word in ['personal', 'home', 'car', 'education', 'business']):
                if 'personal' in user_message.lower():
                    collected['loan_type'] = 'Personal Loan'
                elif 'home' in user_message.lower():
                    collected['loan_type'] = 'Home Loan'
                elif 'car' in user_message.lower():
                    collected['loan_type'] = 'Car Loan'
                elif 'education' in user_message.lower():
                    collected['loan_type'] = 'Education Loan'
                elif 'business' in user_message.lower():
                    collected['loan_type'] = 'Business Loan'
        
        # Extract loan amount
        if 'loan_amount' not in collected or not collected['loan_amount']:
            # Look for numbers in various formats
            amounts = re.findall(r'(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:lakh|lac|l)?', user_message.lower())
            if amounts:
                amount_str = amounts[0].replace(',', '')
                amount = float(amount_str)
                
                # Convert lakhs to actual amount
                if 'lakh' in user_message.lower() or 'lac' in user_message.lower() or 'l' in user_message.lower():
                    amount = amount * 100000
                
                # If amount seems too small, assume it's in lakhs
                if amount < 10000:
                    amount = amount * 100000
                
                collected['loan_amount'] = int(amount)
        
        # Extract tenure
        if 'tenure' not in collected or not collected['tenure']:
            tenures = re.findall(r'(\d+)\s*(?:month|months|yr|year|years)?', user_message.lower())
            if tenures:
                tenure = int(tenures[0])
                
                # If mentions years, convert to months
                if 'year' in user_message.lower() or 'yr' in user_message.lower():
                    tenure = tenure * 12
                
                # Validate tenure range
                if 6 <= tenure <= 360:  # 6 months to 30 years
                    collected['tenure'] = tenure
        
        # Determine missing fields
        for field in self.required_fields:
            if field not in collected or not collected[field]:
                missing.append(field)
        
        # Calculate confidence
        confidence = (len(self.required_fields) - len(missing)) / len(self.required_fields)
        
        # Generate reply based on missing fields
        if not missing:
            reply = f"""Perfect! Let me confirm the details:

Loan Type: {collected['loan_type']}
Loan Amount: ₹{collected['loan_amount']:,}
Tenure: {collected['tenure']} months

Is this correct? We'll proceed with identity verification next."""
            
            return {
                'completed': True,
                'missing_fields': [],
                'collected': collected,
                'confidence': 1.0,
                'reply': reply
            }
        
        # Ask for the first missing field
        if 'loan_type' in missing:
            reply = "I'd be happy to help! What type of loan are you looking for? (Personal, Home, Car, Education, or Business)"
        elif 'loan_amount' in missing:
            reply = f"Great choice on the {collected.get('loan_type', 'loan')}! How much would you like to borrow? (Please specify the amount in rupees or lakhs)"
        elif 'tenure' in missing:
            reply = f"Excellent! And for how long would you like this loan? Please specify the tenure in months (typically 12-60 months for personal loans)."
        else:
            reply = "Thank you for providing those details. Let me help you further."
        
        return {
            'completed': False,
            'missing_fields': missing,
            'collected': collected,
            'confidence': confidence,
            'reply': reply
        }
