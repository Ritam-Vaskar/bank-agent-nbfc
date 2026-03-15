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
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_JUSTIFY, TA_LEFT

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
        issue_date = datetime.now()
        format_money = lambda value: f"Rs. {float(value or 0):,.2f}"
        loan_label = offer_data.get('loan_type', 'loan').replace('_', ' ').title()
        applicant_name = user_data.get('full_name') or user_data.get('email', 'Customer')
        first_emi_amount = emi_schedule_summary.get('monthly_emi', offer_data.get('monthly_emi', 0))
        
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

        body_style = ParagraphStyle(
            'BodyStyle',
            parent=styles['Normal'],
            fontSize=10,
            leading=15,
            alignment=TA_LEFT,
        )

        section_note_style = ParagraphStyle(
            'SectionNote',
            parent=styles['Normal'],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor('#4b5563'),
            alignment=TA_LEFT,
        )

        small_heading_style = ParagraphStyle(
            'SmallHeading',
            parent=styles['Heading3'],
            fontSize=11,
            leading=14,
            textColor=colors.HexColor('#1e3a8a'),
            spaceAfter=8,
            fontName='Helvetica-Bold'
        )
        
        # Header
        elements.append(Paragraph("NBFC DIGITAL LENDING PLATFORM", title_style))
        elements.append(Paragraph("Registered Office: Digital Lending Operations Centre, India", section_note_style))
        elements.append(Spacer(1, 0.15 * inch))
        elements.append(Paragraph("LOAN SANCTION LETTER", heading_style))
        elements.append(Spacer(1, 0.2 * inch))

        reference_table = Table([
            ['Applicant', applicant_name],
            ['Loan Type', loan_label],
            ['Loan Reference No.', loan_id],
            ['Application No.', application_data.get('application_id', 'N/A')],
            ['Issue Date', issue_date.strftime('%B %d, %Y')],
            ['Offer Valid Until', offer_data.get('offer_valid_until', '15 calendar days from issue date')],
        ], colWidths=[2.0 * inch, 4.2 * inch])
        reference_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#cbd5e1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(reference_table)
        elements.append(Spacer(1, 0.25 * inch))

        elements.append(Paragraph(f"Dear {applicant_name},", body_style))
        elements.append(Spacer(1, 0.08 * inch))
        elements.append(Paragraph(
            (
                f"We are pleased to sanction your <b>{loan_label}</b> application, subject to the commercial "
                "terms, borrower undertakings, and regulatory disclosures listed in this document. "
                "Please review the details carefully before proceeding."
            ),
            body_style,
        ))
        elements.append(Spacer(1, 0.22 * inch))

        elements.append(Paragraph("1. Commercial Terms", heading_style))
        commercial_terms_table = Table([
            ['Facility Amount', format_money(offer_data.get('principal'))],
            ['Tenure', f"{offer_data.get('tenure_months', 0)} months"],
            ['Interest Rate', f"{offer_data.get('interest_rate', 0)}% per annum"],
            ['Monthly EMI', format_money(offer_data.get('monthly_emi'))],
            ['Processing Fee', format_money(offer_data.get('processing_fee'))],
            ['GST on Processing Fee', format_money(offer_data.get('processing_fee_gst'))],
            ['Total Upfront Charges', format_money(offer_data.get('total_processing_fee'))],
            ['Net Disbursement Amount', format_money(offer_data.get('net_disbursement'))],
            ['Total Interest Over Tenure', format_money(offer_data.get('total_interest'))],
            ['Total Repayment Obligation', format_money(offer_data.get('total_repayment'))],
        ], colWidths=[3.5 * inch, 2.7 * inch])
        commercial_terms_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dbeafe')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#bfdbfe')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bfdbfe')),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(commercial_terms_table)
        elements.append(Spacer(1, 0.22 * inch))

        elements.append(Paragraph("2. Repayment Snapshot", heading_style))
        elements.append(Paragraph(
            "This section summarises the scheduled repayment obligations derived from the amortisation plan generated at sanction time.",
            section_note_style,
        ))
        elements.append(Spacer(1, 0.08 * inch))
        repayment_table = Table([
            ['Total Installments', str(emi_schedule_summary.get('total_installments', offer_data.get('tenure_months', 0)))],
            ['First EMI Amount', format_money(first_emi_amount)],
            ['Principal Repaid Over Term', format_money(emi_schedule_summary.get('total_principal', offer_data.get('principal')))],
            ['Interest Repaid Over Term', format_money(emi_schedule_summary.get('total_interest', offer_data.get('total_interest')))],
        ], colWidths=[3.5 * inch, 2.7 * inch])
        repayment_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#d1d5db')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(repayment_table)
        elements.append(Spacer(1, 0.22 * inch))

        elements.append(Paragraph("3. Borrower Terms and Conditions", heading_style))
        terms = [
            "Disbursement will be initiated only after digital acceptance of this sanction letter and successful completion of final internal checks.",
            "The sanctioned facility remains valid for 15 calendar days from the issue date unless withdrawn earlier for regulatory, fraud-control, or document-validation reasons.",
            "EMIs are due on the agreed debit date each month. Delayed or failed repayment attracts penal charges of 2% per month on overdue dues, in addition to applicable taxes.",
            "A bounce or failed auto-debit instruction will attract a service charge of Rs. 500 per instance plus applicable taxes.",
            "Prepayment or foreclosure is permitted after 6 months from disbursement, subject to a charge of 2% on the principal outstanding and any statutory levies in force.",
            "The borrower must ensure that all declarations, financial details, and KYC information submitted during the application journey remain true, accurate, and complete.",
            "Any material adverse change in employment, income, banking access, or repayment capacity should be disclosed promptly to the lender.",
            "The borrower authorises the lender and its service providers to use validated application data for underwriting, servicing, collections, fraud prevention, and regulatory reporting.",
            "The loan may be recalled, cancelled, or frozen before disbursement if any discrepancy, adverse bureau event, sanctions hit, fraud concern, or policy breach is identified.",
            "A cooling-off period of 24 hours from disbursement is available for eligible cancellations in line with the lender's digital lending policy and applicable RBI directions.",
        ]

        for index, term in enumerate(terms, start=1):
            elements.append(Paragraph(f"{index}. {term}", body_style))
            elements.append(Spacer(1, 0.05 * inch))

        elements.append(Spacer(1, 0.15 * inch))
        elements.append(Paragraph("4. Regulatory and Customer Communication", heading_style))
        elements.append(Paragraph(
            (
                "This sanction has been prepared in line with applicable RBI digital lending directions. "
                "All key charges, repayment obligations, and borrower rights have been disclosed above. "
                "For service requests or grievances, please write to <b>complaints@nbfc-loan-platform.com</b>."
            ),
            body_style,
        ))
        elements.append(Spacer(1, 0.18 * inch))
        elements.append(Paragraph("5. Acceptance and Execution", heading_style))
        elements.append(Paragraph(
            (
                "By accepting this sanction on the digital platform, you confirm that you have read, understood, "
                "and agreed to the commercial terms, repayment obligations, and borrower declarations contained in this document."
            ),
            body_style,
        ))
        elements.append(Spacer(1, 0.35 * inch))
        elements.append(Paragraph("For NBFC Digital Lending Platform", small_heading_style))
        elements.append(Paragraph(
            "Authorised Signatory<br/>Digitally generated and system approved",
            body_style,
        ))
        elements.append(Spacer(1, 0.2 * inch))
        
        # Footer
        footer_text = (
            "<i>This is a system-generated sanction letter and does not require a physical signature. "
            "Please retain a copy for your records and refer to the loan details page for the latest EMI schedule and servicing updates.</i>"
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
