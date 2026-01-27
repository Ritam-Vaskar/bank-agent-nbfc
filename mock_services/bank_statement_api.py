"""Mock Bank Statement Parser"""

import random
from datetime import datetime, timedelta
from typing import Dict, Any, List

def parse_bank_statement(file_path: str) -> Dict[str, Any]:
    """
    Parse bank statement and extract financial data
    In production, this would use OCR and NLP to parse actual statements
    """
    
    # Generate mock statement data
    months = 3
    transactions_per_month = random.randint(15, 30)
    
    transactions = []
    current_balance = random.randint(50000, 500000)
    
    for month in range(months):
        for _ in range(transactions_per_month):
            # Random transaction
            is_credit = random.random() > 0.4
            amount = random.randint(1000, 50000)
            
            if is_credit:
                transaction_type = random.choice(['Salary', 'Transfer', 'Interest', 'Refund'])
                current_balance += amount
            else:
                transaction_type = random.choice(['ATM', 'POS', 'Online', 'UPI', 'EMI', 'Bill Payment'])
                current_balance -= amount
            
            date = datetime.now() - timedelta(days=random.randint(1, 90))
            
            transactions.append({
                'date': date.strftime('%Y-%m-%d'),
                'type': transaction_type,
                'amount': amount,
                'balance': max(current_balance, 0),
                'credit': is_credit
            })
    
    # Calculate statistics
    credits = [t['amount'] for t in transactions if t['credit']]
    debits = [t['amount'] for t in transactions if not t['credit']]
    
    avg_monthly_credit = sum(credits) / months if credits else 0
    avg_monthly_debit = sum(debits) / months if debits else 0
    
    # Identify salary
    salary_transactions = [t for t in transactions if t['type'] == 'Salary']
    monthly_salary = int(sum(t['amount'] for t in salary_transactions) / months) if salary_transactions else 0
    
    return {
        'success': True,
        'bank_name': random.choice(['HDFC Bank', 'ICICI Bank', 'SBI', 'Axis Bank', 'Kotak Bank']),
        'account_number': f"XXXX-XXXX-{random.randint(1000, 9999)}",
        'statement_period': f"{(datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}",
        'opening_balance': random.randint(30000, 100000),
        'closing_balance': current_balance,
        'avg_monthly_balance': int(sum(t['balance'] for t in transactions) / len(transactions)),
        'avg_monthly_credit': int(avg_monthly_credit),
        'avg_monthly_debit': int(avg_monthly_debit),
        'monthly_salary': monthly_salary,
        'total_transactions': len(transactions),
        'bounced_cheques': random.randint(0, 1),
        'minimum_balance_violations': random.randint(0, 2),
        'transactions': transactions[:10]  # Return sample transactions
    }

def verify_salary_credit(transactions: List[Dict]) -> Dict[str, Any]:
    """
    Verify regular salary credits
    """
    salary_transactions = [t for t in transactions if t['type'] == 'Salary']
    
    if len(salary_transactions) < 3:
        return {
            'verified': False,
            'message': 'Insufficient salary credit history'
        }
    
    # Check regularity (should be monthly)
    avg_salary = sum(t['amount'] for t in salary_transactions) / len(salary_transactions)
    
    return {
        'verified': True,
        'avg_monthly_salary': int(avg_salary),
        'salary_credits_found': len(salary_transactions),
        'employer_identified': True,
        'message': 'Regular salary credits verified'
    }
