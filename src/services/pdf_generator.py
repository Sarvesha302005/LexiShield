"""
Evidentiary PDF Dossier Generator: Generates clean, standardized dispute rebuttal PDFs using ReportLab.
Compiles order details, carrier telemetry, warehouse confirmation, and structured legal rebuttal statements.
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
        file_path: str | None = None,
    ) -> bytes:
        """
        Generate a professional evidentiary PDF rebuttal dossier.
        Returns raw bytes and optionally writes to the specified file path.
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

            # Custom styling
            title_style = ParagraphStyle(
                "DocTitle",
                parent=styles["Heading1"],
                fontSize=20,
                leading=24,
                textColor=colors.HexColor("#0B2265"),  # PayPal navy blue
                fontName="Helvetica-Bold",
                spaceAfter=4,
            )
            subtitle_style = ParagraphStyle(
                "DocSubtitle",
                parent=styles["Normal"],
                fontSize=10,
                leading=14,
                textColor=colors.HexColor("#555555"),
                spaceAfter=15,
            )
            h2_style = ParagraphStyle(
                "SectionHeading",
                parent=styles["Heading2"],
                fontSize=12,
                leading=16,
                textColor=colors.HexColor("#0B2265"),
                fontName="Helvetica-Bold",
                spaceBefore=10,
                spaceAfter=6,
            )
            body_style = ParagraphStyle(
                "BodyTextCustom",
                parent=styles["Normal"],
                fontSize=9,
                leading=13,
                textColor=colors.HexColor("#222222"),
            )
            legal_style = ParagraphStyle(
                "LegalText",
                parent=styles["Normal"],
                fontSize=8.5,
                leading=12,
                textColor=colors.HexColor("#333333"),
                backColor=colors.HexColor("#F4F6F9"),
                borderPadding=8,
                spaceBefore=6,
                spaceAfter=10,
            )
            table_cell_style = ParagraphStyle(
                "TableCell",
                parent=styles["Normal"],
                fontSize=8,
                leading=11,
                textColor=colors.HexColor("#222222"),
            )

            story = []

            # 1. Header Banner
            story.append(Paragraph("EVIDENTIARY DISPUTE REBUTTAL DOSSIER", title_style))
            story.append(
                Paragraph(
                    f"Official Case Submission for PayPal Dispute ID: <b>{dispute.dispute_id}</b> | "
                    f"Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}",
                    subtitle_style,
                )
            )
            story.append(
                HRFlowable(
                    width="100%",
                    thickness=2,
                    color=colors.HexColor("#0070BA"),
                    spaceAfter=12,
                )
            )

            # 2. Executive Summary & Case Metadata Table
            story.append(Paragraph("1. Executive Summary & Case Overview", h2_style))
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
                    Paragraph("<b>Customer Name</b>", table_cell_style),
                    Paragraph(order.customer_name, table_cell_style),
                    Paragraph("<b>Calculated P(win)</b>", table_cell_style),
                    Paragraph(f"<b>{decision.win_probability * 100:.1f}%</b>", table_cell_style),
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
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            story.append(t_overview)
            story.append(Spacer(1, 10))

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
                    Paragraph(carrier.signed_by or "Direct Delivery / Porch", table_cell_style),
                    Paragraph("<b>Signature Proof URL</b>", table_cell_style),
                    Paragraph("Archived on Carrier CDN", table_cell_style),
                ],
            ]
            t_carrier = Table(carrier_data, colWidths=[110, 155, 110, 155])
            t_carrier.setStyle(
                TableStyle(
                    [
                        (
                            "BACKGROUND",
                            (0, 0),
                            (-1, -1),
                            colors.HexColor("#F0FDF4"),
                        ),  # light green tint
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#86EFAC")),
                        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BBF7D0")),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            story.append(t_carrier)
            story.append(Spacer(1, 10))

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
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            story.append(t_wh)
            story.append(Spacer(1, 10))

            # 5. Formal Legal Defense Statement
            story.append(Paragraph("4. Formal Legal Rebuttal & Policy Defense", h2_style))
            formatted_rebuttal = decision.rebuttal_statement.replace("\n", "<br/>")
            story.append(Paragraph(formatted_rebuttal, legal_style))
            story.append(Spacer(1, 8))

            # 6. Attestation
            attestation_text = (
                "<b>Merchant Attestation:</b> I declare under penalty of perjury under the laws of the applicable "
                "jurisdiction that the foregoing telemetry, tracking, and fulfillment records are true, authentic, "
                "and extracted directly from automated immutable warehouse scanners and logistics carrier APIs."
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
