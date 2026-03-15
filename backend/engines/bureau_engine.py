"""
Credit Bureau Engine - Mock CIBIL/credit report fetching
"""

import random
import json
import logging
import os
from typing import Dict, Any, Optional

from config import BASE_DIR

logger = logging.getLogger(__name__)


class BureauEngine:
    """
    Credit Bureau integration engine
    Simulates CIBIL/TransUnion credit report fetching
    - Fetches from mock dataset
    - Simulates network latency
    - Caches results in Redis
    """
    
    # Mock dataset - will be replaced with actual data generation
    _mock_data = {}
    _seed_profiles = {
        "ABCDE1234F": {
            "pan": "ABCDE1234F",
            "name": "Demo Customer",
            "credit_score": 782,
            "score_tier": "excellent",
            "active_loans": 1,
            "total_outstanding": 125000.0,
            "existing_emi": 6240.0,
            "dpd_30_days": 0,
            "bureau_flags": [],
            "credit_history_length_months": 84,
            "last_updated": "2026-03-10",
            "generated_at": "2026-03-10T00:00:00",
            "bureau": "CIBIL_MOCK"
        }
    }

    @classmethod
    def load_mock_dataset(cls) -> Dict[str, Any]:
        """
        Load mock bureau dataset from JSON files and index by PAN.
        """
        candidate_files = [
            os.path.join(BASE_DIR, "generated", "credit_bureau_data.json"),
            os.path.join(BASE_DIR, "mock_data", "generated", "credit_bureau_data.json"),
            os.path.join(BASE_DIR, "mock_data", "seeds", "credit_bureau_sample.json"),
        ]

        loaded_records = {}
        for file_path in candidate_files:
            if not os.path.exists(file_path):
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as handle:
                    payload = json.load(handle)

                if isinstance(payload, list):
                    records = payload
                elif isinstance(payload, dict):
                    records = payload.get("records") or payload.get("data") or []
                else:
                    records = []

                for record in records:
                    pan = (record.get("pan") or "").upper().strip()
                    if pan:
                        loaded_records[pan] = record

                if loaded_records:
                    logger.info(f"Loaded {len(loaded_records)} bureau records from {file_path}")

            except Exception as exc:
                logger.warning(f"Failed to read bureau mock file {file_path}: {exc}")

        merged = {**cls._seed_profiles, **loaded_records}
        cls._mock_data = merged
        logger.info(f"Mock bureau dataset ready with {len(cls._mock_data)} PAN profiles")
        return cls._mock_data
    
    @classmethod
    def load_mock_data(cls, data: Dict[str, Any]):
        """Load mock bureau data (from generated dataset)"""
        cls._mock_data = data
        logger.info(f"Loaded {len(data)} mock credit bureau records")
    
    @classmethod
    def _generate_mock_record(cls, pan: str) -> Dict[str, Any]:
        """
        Generate a mock credit report on-the-fly
        Used when mock dataset not available
        """
        # Realistic credit score distribution
        score_distribution = [
            (300, 550, 0.10),   # 10% subprime
            (550, 650, 0.20),   # 20% fair
            (650, 750, 0.40),   # 40% good
            (750, 900, 0.30),   # 30% excellent
        ]
        
        # Select range based on distribution
        rand = random.random()
        cumulative = 0
        for min_score, max_score, probability in score_distribution:
            cumulative += probability
            if rand <= cumulative:
                credit_score = random.randint(min_score, max_score)
                break
        else:
            credit_score = random.randint(650, 750)
        
        # Generate other attributes based on credit score tier
        if credit_score >= 750:
            active_loans = random.randint(0, 2)
            total_outstanding = random.uniform(0, 500000)
            dpd_30_days = 0
            bureau_flags = []
        elif credit_score >= 650:
            active_loans = random.randint(1, 3)
            total_outstanding = random.uniform(100000, 1000000)
            dpd_30_days = random.randint(0, 1)
            bureau_flags = []
        elif credit_score >= 550:
            active_loans = random.randint(2, 5)
            total_outstanding = random.uniform(200000, 1500000)
            dpd_30_days = random.randint(1, 3)
            bureau_flags = random.choice([[], ["HIGH_UTILIZATION"]])
        else:
            active_loans = random.randint(3, 7)
            total_outstanding = random.uniform(300000, 2000000)
            dpd_30_days = random.randint(3, 10)
            bureau_flags = random.sample(
                ["HIGH_UTILIZATION", "RECENT_DEFAULT", "MULTIPLE_INQUIRIES"],
                k=random.randint(1, 2)
            )
        
        # Calculate existing EMI (rough estimate)
        if total_outstanding > 0:
            # Assume average 12% interest, 36 months tenure
            monthly_rate = 0.12 / 12
            n = 36
            existing_emi = total_outstanding * monthly_rate * (1 + monthly_rate)**n / ((1 + monthly_rate)**n - 1)
        else:
            existing_emi = 0
        
        return {
            "pan": pan,
            "credit_score": credit_score,
            "active_loans": active_loans,
            "total_outstanding": round(total_outstanding, 2),
            "dpd_30_days": dpd_30_days,
            "existing_emi": round(existing_emi, 2),
            "bureau_flags": bureau_flags,
            "last_updated": "2026-03-05",
            "bureau": "CIBIL_SIMULATED"
        }
    
    @classmethod
    def fetch_credit_report(cls, pan: str) -> Dict[str, Any]:
        """
        Fetch credit report for given PAN (mock CIBIL API)
        - Checks in-memory mock dataset first (seeded records)
        - Falls back to on-the-fly generation for unknown PANs
        - Returns structured credit report
        """
        pan_upper = pan.upper().strip()

        if not cls._mock_data:
            cls.load_mock_dataset()

        # Fetch from seeded/mock data or generate
        if pan_upper in cls._mock_data:
            report = cls._mock_data[pan_upper]
            logger.info(f"Bureau data fetched from mock dataset for PAN ending {pan_upper[-4:]}")
        else:
            report = cls._generate_mock_record(pan_upper)
            logger.info(f"Bureau data generated on-the-fly for PAN ending {pan_upper[-4:]}")

        return report
    
    @classmethod
    def analyze_credit_report(cls, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze credit report and provide insights
        """
        credit_score = report.get("credit_score", 0)
        dpd = report.get("dpd_30_days", 0)
        flags = report.get("bureau_flags", [])
        
        # Determine credit tier
        if credit_score >= 750:
            tier = "EXCELLENT"
            risk_indicator = "LOW"
        elif credit_score >= 650:
            tier = "GOOD"
            risk_indicator = "MEDIUM"
        elif credit_score >= 550:
            tier = "FAIR"
            risk_indicator = "HIGH"
        else:
            tier = "POOR"
            risk_indicator = "VERY_HIGH"
        
        # Check red flags
        red_flags = []
        if dpd > 2:
            red_flags.append(f"High days past due: {dpd} instances in last 30 days")
        if len(flags) > 0:
            red_flags.append(f"Bureau flags: {', '.join(flags)}")
        if report.get("active_loans", 0) > 5:
            red_flags.append(f"High number of active loans: {report.get('active_loans')}")
        
        return {
            "credit_tier": tier,
            "risk_indicator": risk_indicator,
            "red_flags": red_flags,
            "recommendation": "APPROVE" if len(red_flags) == 0 and credit_score >= 700 else "REVIEW"
        }


# Global instance
bureau_engine = BureauEngine()
