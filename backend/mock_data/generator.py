"""
Mock Data Generator CLI
Generate realistic NBFC loan platform test data
"""

import argparse
import os
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from generators.credit_bureau_generator import CreditBureauGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def generate_all_data(count: int, output_dir: str):
    """Generate all mock data"""
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info(f"Starting mock data generation - {count} records")
    
    # Generate credit bureau data
    logger.info("Generating credit bureau data...")
    bureau_file = os.path.join(output_dir, "credit_bureau_data.json")
    records = CreditBureauGenerator.generate_dataset(count)
    CreditBureauGenerator.save_to_file(records, bureau_file)
    
    logger.info("✓ Credit bureau data generated")
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("DATA GENERATION COMPLETE")
    logger.info("="*60)
    logger.info(f"Total records: {count}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Files created:")
    logger.info(f"  - credit_bureau_data.json ({count} records)")
    logger.info("="*60)


def main():
    parser = argparse.ArgumentParser(
        description="Generate mock data for NBFC Loan Platform"
    )
    
    parser.add_argument(
        '--records',
        type=int,
        default=10000,
        help='Number of records to generate (default: 10000)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='./generated',
        help='Output directory (default: ./generated)'
    )
    
    args = parser.parse_args()
    
    generate_all_data(args.records, args.output)


if __name__ == "__main__":
    main()
