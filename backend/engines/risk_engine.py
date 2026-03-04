"""
Risk Engine - Weighted risk scoring and segmentation
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class RiskEngine:
    """
    Risk assessment engine using weighted factor model
    
    Risk Score = Weighted sum of:
    - Credit Score (40%)
    - FOIR (30%)
    - Employment Stability (15%)
    - City Tier (10%)
    - Bureau Flags (5%)
    
    Score ranges from 0 (best) to 1 (worst)
    Segments: LOW (0-0.3), MEDIUM (0.3-0.6), HIGH (0.6-1.0)
    """
    
    # Weight configuration
    WEIGHTS = {
        "credit_score": 0.40,
        "foir": 0.30,
        "employment_stability": 0.15,
        "city_tier": 0.10,
        "bureau_flags": 0.05
    }
    
    @staticmethod
    def normalize_credit_score(credit_score: int) -> float:
        """
        Normalize credit score to 0-1 scale (inverted - lower score = higher risk)
        Score 900 = 0 risk, Score 300 = 1 risk
        """
        if credit_score >= 900:
            return 0.0
        if credit_score <= 300:
            return 1.0
        
        # Linear normalization (inverted)
        normalized = (900 - credit_score) / (900 - 300)
        return round(normalized, 4)
    
    @staticmethod
    def normalize_foir(foir: float, limit: float = 0.6) -> float:
        """
        Normalize FOIR to 0-1 scale
        FOIR 0 = 0 risk, FOIR >= limit = 1 risk
        """
        if foir <= 0:
            return 0.0
        if foir >= limit:
            return 1.0
        
        normalized = foir / limit
        return round(normalized, 4)
    
    @staticmethod
    def normalize_employment_stability(
        employment_type: str,
        years_experience: int
    ) -> float:
        """
        Normalize employment stability to 0-1 scale
        Salaried with high experience = low risk
        """
        base_risk = {
            "salaried": 0.2,
            "self_employed": 0.5,
            "business": 0.6,
            "other": 0.8
        }.get(employment_type, 0.8)
        
        # Reduce risk with experience
        if years_experience >= 10:
            experience_factor = 0.0
        elif years_experience >= 5:
            experience_factor = 0.1
        elif years_experience >= 2:
            experience_factor = 0.2
        else:
            experience_factor = 0.3
        
        risk = min(base_risk + experience_factor, 1.0)
        return round(risk, 4)
    
    @staticmethod
    def normalize_city_tier(city_tier: int) -> float:
        """
        Normalize city tier to 0-1 scale
        Tier 1 = lowest risk, Tier 3 = highest risk
        """
        tier_risk = {
            1: 0.0,
            2: 0.5,
            3: 1.0
        }.get(city_tier, 0.5)
        
        return tier_risk
    
    @staticmethod
    def normalize_bureau_flags(bureau_flags: List[str]) -> float:
        """
        Normalize bureau flags to 0-1 scale
        No flags = 0, Multiple flags = 1
        """
        if not bureau_flags or len(bureau_flags) == 0:
            return 0.0
        
        # Each flag contributes to risk
        flag_weights = {
            "HIGH_UTILIZATION": 0.3,
            "RECENT_DEFAULT": 0.8,
            "MULTIPLE_INQUIRIES": 0.4,
            "SETTLED_ACCOUNTS": 0.6,
            "WRITE_OFF": 1.0
        }
        
        total_risk = sum(flag_weights.get(flag, 0.5) for flag in bureau_flags)
        
        # Cap at 1.0
        return min(round(total_risk, 4), 1.0)
    
    @classmethod
    def calculate_risk_score(
        cls,
        credit_score: int,
        foir: float,
        employment_type: str,
        years_experience: int,
        city_tier: int,
        bureau_flags: List[str],
        foir_limit: float = 0.6
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive risk score using weighted model
        """
        # Normalize each factor
        credit_factor = cls.normalize_credit_score(credit_score)
        foir_factor = cls.normalize_foir(foir, foir_limit)
        employment_factor = cls.normalize_employment_stability(employment_type, years_experience)
        city_factor = cls.normalize_city_tier(city_tier)
        bureau_factor = cls.normalize_bureau_flags(bureau_flags)
        
        # Calculate weighted risk score
        risk_score = (
            credit_factor * cls.WEIGHTS["credit_score"] +
            foir_factor * cls.WEIGHTS["foir"] +
            employment_factor * cls.WEIGHTS["employment_stability"] +
            city_factor * cls.WEIGHTS["city_tier"] +
            bureau_factor * cls.WEIGHTS["bureau_flags"]
        )
        
        risk_score = round(risk_score, 4)
        
        # Determine segment
        if risk_score <= 0.3:
            segment = "LOW"
            description = "Excellent credit profile with low default probability"
        elif risk_score <= 0.6:
            segment = "MEDIUM"
            description = "Good credit profile with moderate risk"
        else:
            segment = "HIGH"
            description = "Acceptable but higher risk profile, requires monitoring"
        
        # Generate explanation
        factors_breakdown = {
            "credit_score_factor": {
                "normalized": credit_factor,
                "weight": cls.WEIGHTS["credit_score"],
                "contribution": round(credit_factor * cls.WEIGHTS["credit_score"], 4),
                "raw_value": credit_score
            },
            "foir_factor": {
                "normalized": foir_factor,
                "weight": cls.WEIGHTS["foir"],
                "contribution": round(foir_factor * cls.WEIGHTS["foir"], 4),
                "raw_value": foir
            },
            "employment_stability_factor": {
                "normalized": employment_factor,
                "weight": cls.WEIGHTS["employment_stability"],
                "contribution": round(employment_factor * cls.WEIGHTS["employment_stability"], 4),
                "raw_value": f"{employment_type}, {years_experience} years"
            },
            "city_tier_factor": {
                "normalized": city_factor,
                "weight": cls.WEIGHTS["city_tier"],
                "contribution": round(city_factor * cls.WEIGHTS["city_tier"], 4),
                "raw_value": city_tier
            },
            "bureau_flags_factor": {
                "normalized": bureau_factor,
                "weight": cls.WEIGHTS["bureau_flags"],
                "contribution": round(bureau_factor * cls.WEIGHTS["bureau_flags"], 4),
                "raw_value": bureau_flags if bureau_flags else "None"
            }
        }
        
        # Key risk drivers
        contributions = {k: v["contribution"] for k, v in factors_breakdown.items()}
        top_drivers = sorted(contributions.items(), key=lambda x: x[1], reverse=True)[:3]
        
        return {
            "risk_score": risk_score,
            "risk_segment": segment,
            "description": description,
            "factors_breakdown": factors_breakdown,
            "top_risk_drivers": [driver[0].replace("_factor", "") for driver in top_drivers],
            "recommendation": "APPROVE" if risk_score <= 0.6 else "MANUAL_REVIEW"
        }
    
    @staticmethod
    def explain_risk_factors(risk_assessment: Dict[str, Any]) -> str:
        """
        Generate human-readable explanation of risk factors
        For LLM to use in conversation
        """
        segment = risk_assessment["risk_segment"]
        score = risk_assessment["risk_score"]
        top_drivers = risk_assessment["top_risk_drivers"]
        
        explanation = f"Your application has been assessed as {segment} risk (score: {score:.2f}). "
        
        if segment == "LOW":
            explanation += "This is an excellent credit profile. "
        elif segment == "MEDIUM":
            explanation += "This is a good credit profile with moderate risk. "
        else:
            explanation += "This profile requires careful review. "
        
        explanation += f"The main factors considered were: {', '.join(top_drivers)}. "
        
        return explanation


# Global instance
risk_engine = RiskEngine()
