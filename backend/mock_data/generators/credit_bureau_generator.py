"""
Credit Bureau Data Generator
Generates realistic credit bureau records with proper distributions
"""

import random
import json
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CreditBureauGenerator:
    """
    Generates realistic credit bureau records
    - Proper distribution: 10% subprime, 20% fair, 40% good, 30% excellent
    - Realistic active loans, outstanding amounts, DPD patterns
    """
    
    # Score distributions
    SCORE_RANGES = {
        "subprime": (300, 550),      # 10%
        "fair": (550, 650),          # 20%
        "good": (650, 750),          # 40%
        "excellent": (750, 900)      # 30%
    }
    
    DISTRIBUTION_WEIGHTS = [0.10, 0.20, 0.40, 0.30]
    
    # Indian names for realistic data
    FIRST_NAMES = [
        "Aarav", "Vivaan", "Aditya", "Arjun", "Sai", "Rohan", "Krishna", "Aryan",
        "Ananya", "Diya", "Aadhya", "Anvi", "Saanvi", "Kavya", "Priya", "Riya",
        "Rahul", "Amit", "Ravi", "Suresh", "Vijay", "Rajesh", "Pradeep", "Manoj",
        "Pooja", "Sneha", "Neha", "Divya", "Anjali", "Deepa", "Swati", "Nikita"
    ]
    
    LAST_NAMES = [
        "Sharma", "Verma", "Kumar", "Singh", "Patel", "Agarwal", "Gupta", "Reddy",
        "Iyer", "Nair", "Mehta", "Shah", "Joshi", "Desai", "Rao", "Kapoor",
        "Malhotra", "Khanna", "Bhat", "Shetty", "Kulkarni", "Patil", "Naidu"
    ]
    
    @staticmethod
    def _generate_pan() -> str:
        """Generate valid PAN format"""
        letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        digits = '0123456789'
        
        pan = (
            ''.join(random.choices(letters, k=3)) +
            random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') +
            random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') +
            ''.join(random.choices(digits, k=4)) +
            random.choice(letters)
        )
        return pan
    
    @staticmethod
    def _generate_credit_score(tier: str) -> int:
        """Generate credit score within tier range"""
        min_score, max_score = CreditBureauGenerator.SCORE_RANGES[tier]
        return random.randint(min_score, max_score)
    
    @staticmethod
    def _generate_active_loans(tier: str) -> int:
        """Generate number of active loans based on tier"""
        if tier == "excellent":
            return random.choices([0, 1, 2, 3], weights=[0.3, 0.4, 0.2, 0.1])[0]
        elif tier == "good":
            return random.choices([0, 1, 2, 3, 4], weights=[0.2, 0.3, 0.3, 0.1, 0.1])[0]
        elif tier == "fair":
            return random.choices([1, 2, 3, 4, 5], weights=[0.2, 0.3, 0.3, 0.1, 0.1])[0]
        else:  # subprime
            return random.choices([2, 3, 4, 5, 6], weights=[0.2, 0.3, 0.3, 0.1, 0.1])[0]
    
    @staticmethod
    def _generate_total_outstanding(active_loans: int, tier: str) -> float:
        """Generate total outstanding amount"""
        if active_loans == 0:
            return 0.0
        
        base_amounts = {
            "excellent": (50000, 500000),
            "good": (30000, 300000),
            "fair": (20000, 200000),
            "subprime": (10000, 150000)
        }
        
        min_amt, max_amt = base_amounts[tier]
        return round(random.uniform(min_amt, max_amt), 2)
    
    @staticmethod
    def _generate_dpd(tier: str) -> int:
        """Generate Days Past Due"""
        if tier == "excellent":
            return random.choices([0, 1], weights=[0.95, 0.05])[0]
        elif tier == "good":
            return random.choices([0, 1, 2, 3], weights=[0.85, 0.10, 0.03, 0.02])[0]
        elif tier == "fair":
            return random.choices([0, 1, 2, 3, 10], weights=[0.70, 0.15, 0.10, 0.03, 0.02])[0]
        else:  # subprime
            return random.choices([0, 10, 30, 60, 90], weights=[0.40, 0.30, 0.15, 0.10, 0.05])[0]
    
    @staticmethod
    def _generate_existing_emi(total_outstanding: float, active_loans: int) -> float:
        """Calculate existing monthly EMI"""
        if active_loans == 0 or total_outstanding == 0:
            return 0.0
        
        # Assume average 12-18% interest for 12-36 months
        avg_tenure = random.randint(12, 36)
        monthly_rate = random.uniform(0.12, 0.18) / 12
        
        # EMI formula
        if monthly_rate > 0:
            emi = total_outstanding * monthly_rate * pow(1 + monthly_rate, avg_tenure) / (pow(1 + monthly_rate, avg_tenure) - 1)
        else:
            emi = total_outstanding / avg_tenure
        
        return round(emi, 2)
    
    @staticmethod
    def _generate_bureau_flags(tier: str) -> List[str]:
        """Generate bureau red flags"""
        flags = []
        
        if tier == "subprime":
            possible_flags = ["Multiple DPDs", "Loan writeoff", "Settlement", "High credit utilization", "Multiple inquiries"]
            flags = random.sample(possible_flags, k=random.randint(1, 3))
        elif tier == "fair":
            possible_flags = ["Occasional DPD", "High credit utilization", "Multiple inquiries"]
            if random.random() < 0.3:
                flags = random.sample(possible_flags, k=random.randint(1, 2))
        
        return flags
    
    @staticmethod
    def _generate_credit_history_length(tier: str) -> int:
        """Generate credit history length in months"""
        if tier == "excellent":
            return random.randint(60, 180)  # 5-15 years
        elif tier == "good":
            return random.randint(36, 120)  # 3-10 years
        elif tier == "fair":
            return random.randint(12, 60)   # 1-5 years
        else:  # subprime
            return random.randint(6, 36)    # 6 months - 3 years
    
    @staticmethod
    def generate_record(tier: str) -> Dict[str, Any]:
        """Generate a single credit bureau record"""
        credit_score = CreditBureauGenerator._generate_credit_score(tier)
        active_loans = CreditBureauGenerator._generate_active_loans(tier)
        total_outstanding = CreditBureauGenerator._generate_total_outstanding(active_loans, tier)
        existing_emi = CreditBureauGenerator._generate_existing_emi(total_outstanding, active_loans)
        
        record = {
            "pan": CreditBureauGenerator._generate_pan(),
            "name": f"{random.choice(CreditBureauGenerator.FIRST_NAMES)} {random.choice(CreditBureauGenerator.LAST_NAMES)}",
            "credit_score": credit_score,
            "score_tier": tier,
            "active_loans": active_loans,
            "total_outstanding": total_outstanding,
            "existing_emi": existing_emi,
            "dpd_30_days": CreditBureauGenerator._generate_dpd(tier),
            "bureau_flags": CreditBureauGenerator._generate_bureau_flags(tier),
            "credit_history_length_months": CreditBureauGenerator._generate_credit_history_length(tier),
            "last_updated": datetime.now().isoformat(),
            "generated_at": datetime.now().isoformat()
        }
        
        return record
    
    @staticmethod
    def generate_dataset(count: int) -> List[Dict[str, Any]]:
        """
        Generate dataset with proper distribution
        10% subprime, 20% fair, 40% good, 30% excellent
        """
        records = []
        tiers = ["subprime", "fair", "good", "excellent"]
        
        # Calculate counts per tier
        tier_counts = [
            int(count * CreditBureauGenerator.DISTRIBUTION_WEIGHTS[0]),  # subprime
            int(count * CreditBureauGenerator.DISTRIBUTION_WEIGHTS[1]),  # fair
            int(count * CreditBureauGenerator.DISTRIBUTION_WEIGHTS[2]),  # good
            int(count * CreditBureauGenerator.DISTRIBUTION_WEIGHTS[3])   # excellent
        ]
        
        # Adjust last tier to match exact count
        tier_counts[3] += count - sum(tier_counts)
        
        logger.info(f"Generating {count} credit bureau records")
        logger.info(f"Distribution - Subprime: {tier_counts[0]}, Fair: {tier_counts[1]}, Good: {tier_counts[2]}, Excellent: {tier_counts[3]}")
        
        for tier, tier_count in zip(tiers, tier_counts):
            for _ in range(tier_count):
                records.append(CreditBureauGenerator.generate_record(tier))
        
        # Shuffle to randomize order
        random.shuffle(records)
        
        return records
    
    @staticmethod
    def save_to_file(records: List[Dict[str, Any]], filepath: str):
        """Save records to JSON file"""
        with open(filepath, 'w') as f:
            json.dump(records, f, indent=2)
        
        logger.info(f"Saved {len(records)} records to {filepath}")


# Convenience function
def generate_credit_bureau_data(count: int, output_file: str):
    """Generate and save credit bureau data"""
    generator = CreditBureauGenerator()
    records = generator.generate_dataset(count)
    generator.save_to_file(records, output_file)
    return records
