"""
PDF Engine - Sanction letter generation
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_JUSTIFY

from config import SANCTION_LETTERS_DIR

logger = logging.getLogger(__name__)


class PDFEngine:
    """
    PDF generation engine for loan sanction letters
    - Generates professional sanction letter PDFs
    - Includes all loan terms and conditions
    - RBI compliance clauses
    - Digital signature simulation
    """
    
    @staticmethod
    def generate_sanction_letter(
        loan_id: str,
        application_data: Dict[str, Any],
        offer_data: Dict[str, Any],
        user_data: Dict[str, Any],
        emi_schedule_summary: Dict[str, Any]
    ) -> str:
        """
        Generate loan sanction letter PDF
        Returns: File path of generated PDF
        """
        # Create filename
        filename = f"sanction_letter_{loan_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join(SANCTION_LETTERS_DIR, filename)
        
        # Create PDF
        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            rightMargin=inch,
            leftMargin=inch,
            topMargin=inch,
            bottomMargin=inch
        )
        
        # Container for PDF elements
        elements = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1a237e'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1a237e'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        )
        
        normal_style = styles['Normal']
        normal_style.alignment = TA_JUSTIFY
        
        # Header
        elements.append(Paragraph("NBFC DIGITAL LENDING PLATFORM", title_style))
        elements.append(Spacer(1, 0.2 * inch))
        elements.append(Paragraph("LOAN SANCTION LETTER", heading_style))
        elements.append(Spacer(1, 0.3 * inch))
        
        # Date and reference
        date_text = f"<b>Date:</b> {datetime.now().strftime('%B %d, %Y')}<br/>"
        date_text += f"<b>Loan Reference No:</b> {loan_id}<br/>"
        date_text += f"<b>Application No:</b> {application_data.get('application_id', 'N/A')}"
        elements.append(Paragraph(date_text, normal_style))
        elements.append(Spacer(1, 0.3 * inch))
        
        # Applicant details
        applicant_text = f"<b>Dear {user_data.get('email', 'Customer')},</b>"
        elements.append(Paragraph(applicant_text, normal_style))
        elements.append(Spacer(1, 0.2 * inch))
        
        intro_text = (
            f"We are pleased to inform you that your application for a "
            f"<b>{offer_data.get('loan_type', 'personal_loan').replace('_', ' ').title()}</b> "
            f"has been <b>APPROVED</b> subject to the terms and conditions mentioned below."
        )
        elements.append(Paragraph(intro_text, normal_style))
        elements.append(Spacer(1, 0.3 * inch))
        
        # Loan details table
        elements.append(Paragraph("LOAN DETAILS", heading_style))
        
        loan_details_data = [
            ['Loan Amount (Principal)', f"₹{offer_data.get('principal', 0):,.2f}"],
            ['Tenure', f"{offer_data.get('tenure_months', 0)} months"],
            ['Interest Rate (per annum)', f"{offer_data.get('interest_rate', 0)}%"],
            ['Monthly EMI', f"₹{offer_data.get('monthly_emi', 0):,.2f}"],
            ['Processing Fee (incl. GST)', f"₹{offer_data.get('total_processing_fee', 0):,.2f}"],
            ['Total Interest Payable', f"₹{offer_data.get('total_interest', 0):,.2f}"],
            ['Total Amount Payable', f"₹{offer_data.get('total_repayment', 0):,.2f}"],
            ['Net Disbursement', f"₹{offer_data.get('net_disbursement', 0):,.2f}"],
        ]
        
        loan_table = Table(loan_details_data, colWidths=[3.5 * inch, 2.5 * inch])
        loan_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(loan_table)
        elements.append(Spacer(1, 0.3 * inch))
        
        # Terms and Conditions
        elements.append(Paragraph("TERMS AND CONDITIONS", heading_style))
        
        terms = [
            "The loan shall be disbursed to your registered bank account within 2-3 business days upon acceptance.",
            "The first EMI shall be due on the 1st of the month following disbursement.",
            f"Late payment charges of 2% per month will be levied on overdue EMIs.",
            "Prepayment is allowed after 6 months with a prepayment charge of 2% on the outstanding principal.",
            "EMI bounce charges of ₹500 will be applicable for failed auto-debit transactions.",
            "The loan is subject to satisfactory verification of documents and credit assessment.",
            "This sanction is valid for 15 days from the date of issuance.",
            "You may cancel this loan within 24 hours of disbursement without any charges (cooling period).",
        ]
        
        for i, term in enumerate(terms, 1):
            elements.append(Paragraph(f"{i}. {term}", normal_style))
            elements.append(Spacer(1, 0.1 * inch))
        
        elements.append(Spacer(1, 0.2 * inch))
        
        # RBI Compliance
        elements.append(Paragraph("REGULATORY COMPLIANCE", heading_style))
        
        compliance_text = (
            "This loan is offered in compliance with RBI Guidelines on Digital Lending "
            "(RBI/2022-23/90 DOR.STR.REC.51/21.04.048/2022-23). "
            "All charges have been disclosed transparently. For grievances, please contact: "
            "<b>complaints@nbfc-loan-platform.com</b> or call our helpline."
        )
        elements.append(Paragraph(compliance_text, normal_style))
        elements.append(Spacer(1, 0.3 * inch))
        
        # Acceptance clause
        elements.append(Paragraph("ACCEPTANCE", heading_style))
        acceptance_text = (
            "By accepting this sanction letter through our digital platform, you agree to all "
            "terms and conditions mentioned herein and authorize us to proceed with loan disbursement."
        )
        elements.append(Paragraph(acceptance_text, normal_style))
        elements.append(Spacer(1, 0.4 * inch))
        
        # Signature (simulated)
        signature_text = (
            "<b>For NBFC Digital Lending Platform</b><br/><br/>"
            "___________________________<br/>"
            "Authorized Signatory<br/>"
            "(Digitally Signed)"
        )
        elements.append(Paragraph(signature_text, normal_style))
        elements.append(Spacer(1, 0.3 * inch))
        
        # Footer
        footer_text = (
            "<i>This is a system-generated document and does not require a physical signature. "
            "For any queries, please contact support@nbfc-loan-platform.com</i>"
        )
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER
        )
        elements.append(Paragraph(footer_text, footer_style))
        
        # Build PDF
        doc.build(elements)
        
        logger.info(f"Sanction letter generated: {filename}")
        
        return filepath


# Global instance
pdf_engine = PDFEngine()
