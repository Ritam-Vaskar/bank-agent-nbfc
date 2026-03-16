"""
Credit Bureau Engine - Fixed mock CIBIL report fetching
"""

import json
import logging
import os
from typing import Dict, Any

from config import BASE_DIR

logger = logging.getLogger(__name__)


class BureauEngine:
    """
    Credit Bureau integration engine
    Uses fixed mock CIBIL dataset only (no random generation)
    """
    
    _mock_data = {}

    @classmethod
    def load_mock_dataset(cls) -> Dict[str, Any]:
        """
        Load mock bureau dataset from JSON files and index by PAN.
        """
        candidate_files = [
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

        cls._mock_data = loaded_records
        logger.info(f"Mock bureau dataset ready with {len(cls._mock_data)} PAN profiles")
        return cls._mock_data
    
    @classmethod
    def load_mock_data(cls, data: Dict[str, Any]):
        """Load mock bureau data (from generated dataset)"""
        cls._mock_data = {(key or "").upper().strip(): value for key, value in data.items()}
        logger.info(f"Loaded {len(data)} mock credit bureau records")
    
    @classmethod
    def fetch_credit_report(cls, pan: str) -> Dict[str, Any]:
        """
        Fetch credit report for given PAN (mock CIBIL API)
        - Checks in-memory fixed seed dataset only
        - Returns structured credit report
        """
        pan_upper = pan.upper().strip()

        if not cls._mock_data:
            cls.load_mock_dataset()

        if pan_upper not in cls._mock_data:
            raise ValueError("PAN not found in mock CIBIL registry")

        report = cls._mock_data[pan_upper]
        logger.info(f"Bureau data fetched from mock dataset for PAN ending {pan_upper[-4:]}")

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
