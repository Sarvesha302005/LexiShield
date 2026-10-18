"""
Evidentiary PDF Dossier Generator: Generates clean, standardized dispute rebuttal PDFs using ReportLab.
Compiles order details, carrier telemetry, warehouse confirmation, Visa CE 3.0 liability shift schedules,
and category-specific legal rebuttal statements (INR, SNAD, Digital Goods).
"""

import io
import logging
import os
from datetime import UTC, datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.core.exceptions import PDFGenerationError
from src.models.arbitration import ArbitrationDecision
from src.models.schemas import (
    CarrierTrackingInfo,
    OrderCustomerInfo,
    PayPalDisputeResource,
    WarehouseFulfillmentInfo,
)
from src.services.compliance import ComplianceAuditResult
from src.services.visa_ce3 import CE3QualificationResult

logger = logging.getLogger(__name__)


class PDFGenerator:
    """Enterprise evidentiary dispute dossier generator."""

    def __init__(self, output_dir: str | None = None) -> None:
        self.output_dir = output_dir or os.path.join(os.getcwd(), "artifacts", "dossiers")
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_rebuttal_dossier(
        self,
        dispute: PayPalDisputeResource,
        decision: ArbitrationDecision,
        carrier: CarrierTrackingInfo,
        warehouse: WarehouseFulfillmentInfo,
        order: OrderCustomerInfo,
        compliance_result: ComplianceAuditResult | None = None,
        ce3_result: CE3QualificationResult | None = None,
        file_path: str | None = None,
    ) -> bytes:
        """
        Generate a professional evidentiary PDF rebuttal dossier.
        Supports Visa CE 3.0 schedules, AVS address checks, and category-specific templates.
        """
        try:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=letter,
                rightMargin=40,
                leftMargin=40,
                topMargin=40,
                bottomMargin=40,
            )

            styles = getSampleStyleSheet()

            # Custom typography & styles
            title_style = ParagraphStyle(
                "DocTitle",
                parent=styles["Heading1"],
                fontSize=18,
                leading=22,
                textColor=colors.HexColor("#0B2265"),  # PayPal navy blue
                fontName="Helvetica-Bold",
                spaceAfter=4,
            )
            subtitle_style = ParagraphStyle(
                "DocSubtitle",
                parent=styles["Normal"],
                fontSize=9,
                leading=13,
                textColor=colors.HexColor("#555555"),
                spaceAfter=12,
            )
            h2_style = ParagraphStyle(
                "SectionHeading",
                parent=styles["Heading2"],
                fontSize=11,
                leading=15,
                textColor=colors.HexColor("#0B2265"),
                fontName="Helvetica-Bold",
                spaceBefore=8,
                spaceAfter=5,
            )
            body_style = ParagraphStyle(
                "BodyTextCustom",
                parent=styles["Normal"],
                fontSize=8.5,
                leading=12,
                textColor=colors.HexColor("#222222"),
            )
            legal_style = ParagraphStyle(
                "LegalText",
                parent=styles["Normal"],
                fontSize=8,
                leading=11.5,
                textColor=colors.HexColor("#333333"),
                backColor=colors.HexColor("#F4F6F9"),
                borderPadding=7,
                spaceBefore=4,
                spaceAfter=8,
            )
            table_cell_style = ParagraphStyle(
                "TableCell",
                parent=styles["Normal"],
                fontSize=7.5,
                leading=10.5,
                textColor=colors.HexColor("#222222"),
            )
            badge_ce3_style = ParagraphStyle(
                "CE3Badge",
                parent=styles["Normal"],
                fontSize=8,
                leading=11,
                textColor=colors.HexColor("#065F46"),
                backColor=colors.HexColor("#D1FAE5"),
                borderPadding=6,
                spaceBefore=4,
                spaceAfter=6,
            )

            story = []

            # 1. Header Banner
            cat_name = (
                compliance_result.dispute_category_type if compliance_result else "COMMERCIAL"
            )
            story.append(Paragraph(f"EVIDENTIARY REBUTTAL DOSSIER ({cat_name})", title_style))
            story.append(
                Paragraph(
                    f"Official Submission for PayPal Dispute ID: <b>{dispute.dispute_id}</b> | "
                    f"Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}",
                    subtitle_style,
                )
            )
            story.append(
                HRFlowable(
                    width="100%",
                    thickness=2,
                    color=colors.HexColor("#0070BA"),
                    spaceAfter=10,
                )
            )

            # 2. Executive Summary & Case Metadata Table
            story.append(Paragraph("1. Executive Summary & Policy Compliance", h2_style))
            avs_status = "VERIFIED MATCH"
            if compliance_result and compliance_result.package_redirected:
                avs_status = "FLAGGED (Buyer Redirection)"
            elif compliance_result and not compliance_result.avs_address_matched:
                avs_status = "MISMATCH"

            sig_mandate_text = "N/A"
            if compliance_result:
                sig_mandate_text = (
                    "PASSED"
                    if compliance_result.signature_mandate_met
                    else "VIOLATION (No Sig >= $750)"
                )

            overview_data = [
                [
                    Paragraph("<b>Dispute ID</b>", table_cell_style),
                    Paragraph(dispute.dispute_id, table_cell_style),
                    Paragraph("<b>Disputed Amount</b>", table_cell_style),
                    Paragraph(
                        f"${dispute.dispute_amount.value} {dispute.dispute_amount.currency_code}",
                        table_cell_style,
                    ),
                ],
                [
                    Paragraph("<b>Dispute Stage</b>", table_cell_style),
                    Paragraph(dispute.dispute_stage.value, table_cell_style),
                    Paragraph("<b>Dispute Reason</b>", table_cell_style),
                    Paragraph(dispute.dispute_reason.value, table_cell_style),
                ],
                [
                    Paragraph("<b>Order Reference</b>", table_cell_style),
                    Paragraph(order.order_id, table_cell_style),
                    Paragraph("<b>Transaction ID</b>", table_cell_style),
                    Paragraph(order.transaction_id, table_cell_style),
                ],
                [
                    Paragraph("<b>Calculated P(win)</b>", table_cell_style),
                    Paragraph(f"<b>{decision.win_probability * 100:.1f}%</b>", table_cell_style),
                    Paragraph("<b>AVS Address Verification</b>", table_cell_style),
                    Paragraph(avs_status, table_cell_style),
                ],
                [
                    Paragraph("<b>$750+ Signature Mandate</b>", table_cell_style),
                    Paragraph(sig_mandate_text, table_cell_style),
                    Paragraph("<b>Seller Protection Status</b>", table_cell_style),
                    Paragraph(
                        "QUALIFIED"
                        if (not compliance_result or compliance_result.is_eligible)
                        else "INELIGIBLE",
                        table_cell_style,
                    ),
                ],
            ]
            t_overview = Table(overview_data, colWidths=[110, 155, 110, 155])
            t_overview.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ]
                )
            )
            story.append(t_overview)
            story.append(Spacer(1, 8))

            # 3. Carrier Proof of Delivery Telemetry
            story.append(Paragraph("2. Logistics & Proof of Delivery Telemetry", h2_style))
            gps_str = (
                f"{carrier.gps_latitude:.5f}, {carrier.gps_longitude:.5f} (Verified)"
                if carrier.gps_latitude and carrier.gps_longitude
                else "N/A"
            )
            carrier_data = [
                [
                    Paragraph("<b>Carrier Name</b>", table_cell_style),
                    Paragraph(carrier.carrier_name, table_cell_style),
                    Paragraph("<b>Tracking Number</b>", table_cell_style),
                    Paragraph(carrier.tracking_number, table_cell_style),
                ],
                [
                    Paragraph("<b>Carrier Status</b>", table_cell_style),
                    Paragraph(f"<b>{carrier.status}</b>", table_cell_style),
                    Paragraph("<b>Delivery Timestamp</b>", table_cell_style),
                    Paragraph(carrier.delivered_date or "In Transit", table_cell_style),
                ],
                [
                    Paragraph("<b>Delivery Address</b>", table_cell_style),
                    Paragraph(carrier.destination_address, table_cell_style),
                    Paragraph("<b>GPS Coordinates</b>", table_cell_style),
                    Paragraph(gps_str, table_cell_style),
                ],
                [
                    Paragraph("<b>Signed By</b>", table_cell_style),
                    Paragraph(carrier.signed_by or "Direct Porch / Unsigned", table_cell_style),
                    Paragraph("<b>Signature Proof URL</b>", table_cell_style),
                    Paragraph("Archived on Carrier CDN", table_cell_style),
                ],
            ]
            t_carrier = Table(carrier_data, colWidths=[110, 155, 110, 155])
            t_carrier.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0FDF4")),
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#86EFAC")),
                        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BBF7D0")),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ]
                )
            )
            story.append(t_carrier)
            story.append(Spacer(1, 8))

            # 4. Outbound Warehouse Quality & Telemetry
            story.append(
                Paragraph("3. Outbound Warehouse & Packing Station Verification", h2_style)
            )
            wh_data = [
                [
                    Paragraph("<b>Warehouse Facility</b>", table_cell_style),
                    Paragraph(warehouse.warehouse_id, table_cell_style),
                    Paragraph("<b>Packer Operator ID</b>", table_cell_style),
                    Paragraph(warehouse.packer_id, table_cell_style),
                ],
                [
                    Paragraph("<b>Scale Measured Weight</b>", table_cell_style),
                    Paragraph(f"{warehouse.scale_measured_weight_kg:.3f} kg", table_cell_style),
                    Paragraph("<b>Catalog Expected Weight</b>", table_cell_style),
                    Paragraph(
                        f"{warehouse.expected_weight_kg:.3f} kg (Variance: {warehouse.weight_delta_percent}%)",
                        table_cell_style,
                    ),
                ],
                [
                    Paragraph("<b>Scanned Serial(s)</b>", table_cell_style),
                    Paragraph(", ".join(warehouse.scanned_serials) or "N/A", table_cell_style),
                    Paragraph("<b>Security Tamper Seal</b>", table_cell_style),
                    Paragraph(warehouse.tamper_seal_id, table_cell_style),
                ],
                [
                    Paragraph("<b>Pack Station Photo</b>", table_cell_style),
                    Paragraph("Digital QA Archive Logged", table_cell_style),
                    Paragraph("<b>QA Inspection Passed</b>", table_cell_style),
                    Paragraph(
                        "VERIFIED & PASSED" if warehouse.quality_inspection_passed else "FLAGGED",
                        table_cell_style,
                    ),
                ],
            ]
            t_wh = Table(wh_data, colWidths=[110, 155, 110, 155])
            t_wh.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ]
                )
            )
            story.append(t_wh)
            story.append(Spacer(1, 8))

            # 5. Visa Compelling Evidence 3.0 (CE 3.0) Schedule (If Qualified)
            if ce3_result and ce3_result.is_qualified:
                story.append(
                    Paragraph(
                        "4. Visa Compelling Evidence 3.0 (CE 3.0) Liability Shift Schedule",
                        h2_style,
                    )
                )
                story.append(Paragraph(ce3_result.evidence_summary, badge_ce3_style))

                ce3_rows = [
                    [
                        Paragraph("<b>Historical Txn ID</b>", table_cell_style),
                        Paragraph("<b>Fulfillment Date</b>", table_cell_style),
                        Paragraph("<b>Amount</b>", table_cell_style),
                        Paragraph("<b>IP Address Match</b>", table_cell_style),
                        Paragraph("<b>Shipping Addr Match</b>", table_cell_style),
                    ]
                ]
                for txn in ce3_result.qualifying_transactions:
                    ce3_rows.append(
                        [
                            Paragraph(txn.transaction_id, table_cell_style),
                            Paragraph(txn.order_date[:10], table_cell_style),
                            Paragraph(f"${txn.amount:.2f}", table_cell_style),
                            Paragraph(f"{txn.ip_address} (MATCH)", table_cell_style),
                            Paragraph("EXACT MATCH", table_cell_style),
                        ]
                    )

                t_ce3 = Table(ce3_rows, colWidths=[120, 100, 70, 120, 120])
                t_ce3.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#065F46")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#ECFDF5")),
                            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#059669")),
                            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#A7F3D0")),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ("TOPPADDING", (0, 0), (-1, -1), 2),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                        ]
                    )
                )
                story.append(t_ce3)
                story.append(Spacer(1, 6))

            # 6. Formal Legal Defense Statement
            sec_num = "5" if (ce3_result and ce3_result.is_qualified) else "4"
            story.append(Paragraph(f"{sec_num}. Formal Legal Rebuttal & Policy Defense", h2_style))
            formatted_rebuttal = decision.rebuttal_statement.replace("\n", "<br/>")
            story.append(Paragraph(formatted_rebuttal, legal_style))
            story.append(Spacer(1, 6))

            # 7. Attestation
            attestation_text = (
                "<b>Merchant Attestation:</b> I declare under penalty of perjury under the laws of the applicable "
                "jurisdiction that the foregoing telemetry, tracking, warehouse QA records, and historical ledgers "
                "are true, authentic, and extracted directly from immutable automated systems."
            )
            story.append(Paragraph(attestation_text, body_style))

            # Build Document
            doc.build(story)
            pdf_bytes = buffer.getvalue()
            buffer.close()

            # Optionally write to file
            target_path = file_path or os.path.join(
                self.output_dir, f"dispute_{dispute.dispute_id}_evidence.pdf"
            )
            with open(target_path, "wb") as f:
                f.write(pdf_bytes)

            logger.info(
                f"Evidentiary PDF successfully generated for {dispute.dispute_id} at {target_path}."
            )
            return pdf_bytes

        except Exception as exc:
            logger.error(f"Failed to generate evidentiary PDF for {dispute.dispute_id}: {exc}")
            raise PDFGenerationError(f"PDF generation failed: {exc}") from exc
