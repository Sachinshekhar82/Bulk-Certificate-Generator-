import hashlib
import io
import os
import uuid
from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import qrcode
from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas

from app.config import settings


class CertificateGenerator:
    """Professional PDF Certificate Generator using ReportLab."""

    PAGE_WIDTH, PAGE_HEIGHT = landscape(A4)  # 841.89 x 595.27 points

    # Color Palette
    PRIMARY_COLOR = colors.HexColor("#0F294A")     # Midnight Navy
    SECONDARY_COLOR = colors.HexColor("#C59B27")   # Rich Warm Gold
    TEXT_DARK = colors.HexColor("#1A202C")         # Charcoal Dark
    TEXT_MUTED = colors.HexColor("#4A5568")        # Slate Gray
    BORDER_LIGHT = colors.HexColor("#E2E8F0")      # Subtle Light Border
    BACKGROUND_TINT = colors.HexColor("#FCFBF7")   # Warm Parchment White

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or settings.absolute_storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def generate_certificate_id(self) -> str:
        """Generate unique, professional certificate identifier."""
        random_suffix = uuid.uuid4().hex[:10].upper()
        return f"CERT-{date.today().year}-{random_suffix}"

    def _generate_qr_code_image(self, verification_url: str) -> io.BytesIO:
        """Generates a high-contrast QR code image as an in-memory buffer."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=6,
            border=1,
        )
        qr.add_data(verification_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#0F294A", back_color="white")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer

    def _draw_borders_and_decorations(self, c: canvas.Canvas) -> None:
        """Draws elegant double-layer certificate borders, corner accents, and seal."""
        w, h = self.PAGE_WIDTH, self.PAGE_HEIGHT

        # Background Subtle Warmth
        c.setFillColor(self.BACKGROUND_TINT)
        c.rect(0, 0, w, h, fill=1, stroke=0)

        # Outer Primary Navy Border
        c.setStrokeColor(self.PRIMARY_COLOR)
        c.setLineWidth(4.0)
        c.rect(24, 24, w - 48, h - 48, fill=0, stroke=1)

        # Inner Thin Gold Border
        c.setStrokeColor(self.SECONDARY_COLOR)
        c.setLineWidth(1.5)
        c.rect(32, 32, w - 64, h - 64, fill=0, stroke=1)

        # Corner Geometric Accents (L-brackets with gold squares)
        c.setFillColor(self.SECONDARY_COLOR)
        corner_offsets = [
            (28, 28),
            (w - 36, 28),
            (28, h - 36),
            (w - 36, h - 36),
        ]
        for cx, cy in corner_offsets:
            c.rect(cx, cy, 8, 8, fill=1, stroke=0)

        # Ornate Central Seal Emblem (Canvas-drawn)
        seal_x = w / 2
        seal_y = 110
        c.saveState()
        # Outer gold circle
        c.setStrokeColor(self.SECONDARY_COLOR)
        c.setLineWidth(2)
        c.circle(seal_x, seal_y, 32, fill=0, stroke=1)
        # Inner dashed gold circle
        c.setDash(2, 2)
        c.circle(seal_x, seal_y, 27, fill=0, stroke=1)
        c.setDash()
        # Solid center disk
        c.setFillColor(self.PRIMARY_COLOR)
        c.circle(seal_x, seal_y, 22, fill=1, stroke=0)
        # Star / Starburst in center
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(seal_x, seal_y - 4, "★ VALID ★")
        c.restoreState()

    def generate(
        self,
        recipient_name: str,
        recipient_email: str,
        event_name: str,
        issuer_name: str,
        issue_date: date,
        template_title: str = "Certificate of Completion",
        description: Optional[str] = "has successfully participated in and completed",
        metadata: Optional[Dict[str, Any]] = None,
        custom_cert_id: Optional[str] = None,
    ) -> Tuple[str, str, str, str]:
        """
        Generates a PDF certificate file.

        Returns:
            Tuple[cert_id, file_path, file_hash, verification_url]
        """
        cert_id = custom_cert_id or self.generate_certificate_id()
        verification_url = f"{settings.BASE_URL}/api/v1/certificates/verify/{cert_id}"
        output_filename = f"{cert_id}.pdf"
        output_path = self.storage_dir / output_filename

        w, h = self.PAGE_WIDTH, self.PAGE_HEIGHT
        c = canvas.Canvas(str(output_path), pagesize=(w, h))

        # 1. Background, borders, and seal
        self._draw_borders_and_decorations(c)

        # 2. Issuer / Organization Header
        c.setFont("Helvetica", 11)
        c.setFillColor(self.TEXT_MUTED)
        c.drawCentredString(w / 2, h - 80, issuer_name.upper())

        # 3. Certificate Title
        c.setFont("Helvetica-Bold", 28)
        c.setFillColor(self.PRIMARY_COLOR)
        c.drawCentredString(w / 2, h - 125, template_title.upper())

        # Decorative title accent line
        c.setStrokeColor(self.SECONDARY_COLOR)
        c.setLineWidth(2)
        c.line(w / 2 - 120, h - 138, w / 2 + 120, h - 138)

        # 4. "THIS CERTIFICATE IS PROUDLY PRESENTED TO"
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(self.SECONDARY_COLOR)
        c.drawCentredString(w / 2, h - 175, "THIS IS PROUDLY PRESENTED TO")

        # 5. Recipient Name
        c.setFont("Helvetica-Bold", 32)
        c.setFillColor(self.TEXT_DARK)
        c.drawCentredString(w / 2, h - 225, recipient_name)

        # Name underline flourish
        c.setStrokeColor(self.BORDER_LIGHT)
        c.setLineWidth(1)
        name_width = min(max(c.stringWidth(recipient_name, "Helvetica-Bold", 32) + 60, 240), w - 200)
        c.line(w / 2 - (name_width / 2), h - 238, w / 2 + (name_width / 2), h - 238)

        # 6. Description / Reason
        c.setFont("Helvetica", 13)
        c.setFillColor(self.TEXT_MUTED)
        desc_text = description or "has successfully participated in and completed"
        c.drawCentredString(w / 2, h - 275, desc_text)

        # 7. Event / Course Name
        c.setFont("Helvetica-Bold", 22)
        c.setFillColor(self.PRIMARY_COLOR)
        c.drawCentredString(w / 2, h - 315, event_name)

        # 8. Optional Metadata (e.g., Score, Grade, Honors)
        current_y = h - 350
        if metadata and isinstance(metadata, dict):
            meta_parts = [f"{k.capitalize()}: {v}" for k, v in metadata.items() if v is not None]
            if meta_parts:
                meta_string = "   •   ".join(meta_parts)
                c.setFont("Helvetica-Oblique", 11)
                c.setFillColor(self.SECONDARY_COLOR)
                c.drawCentredString(w / 2, current_y, meta_string)

        # 9. Signatures and Date Footer
        # Left: Date of Issuance
        left_x = 130
        c.setStrokeColor(self.TEXT_MUTED)
        c.setLineWidth(1)
        c.line(left_x - 60, 105, left_x + 60, 105)
        c.setFont("Helvetica", 10)
        c.setFillColor(self.TEXT_DARK)
        c.drawCentredString(left_x, 88, issue_date.strftime("%B %d, %Y"))
        c.setFont("Helvetica", 9)
        c.setFillColor(self.TEXT_MUTED)
        c.drawCentredString(left_x, 72, "DATE OF ISSUANCE")

        # Right: Authorized Signatory
        right_x = w - 130
        c.line(right_x - 60, 105, right_x + 60, 105)
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(self.TEXT_DARK)
        c.drawCentredString(right_x, 88, issuer_name)
        c.setFont("Helvetica", 9)
        c.setFillColor(self.TEXT_MUTED)
        c.drawCentredString(right_x, 72, "AUTHORIZED SIGNATORY")

        # 10. QR Code for Verification (bottom-left margin)
        try:
            qr_buffer = self._generate_qr_code_image(verification_url)
            from reportlab.lib.utils import ImageReader
            qr_reader = ImageReader(qr_buffer)
            c.drawImage(qr_reader, 42, 42, width=48, height=48)
        except Exception:
            pass  # Fail gracefully if image rendering encounters environment issue

        # 11. Security & Certificate ID Footer
        c.setFont("Courier-Bold", 8)
        c.setFillColor(self.TEXT_MUTED)
        c.drawString(98, 48, f"Certificate ID: {cert_id}")
        c.setFont("Helvetica", 7.5)
        c.drawString(98, 38, f"Verify authenticity at: {verification_url}")

        c.showPage()
        c.save()

        # Compute SHA-256 for cryptographic file integrity
        sha256 = hashlib.sha256()
        with open(output_path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        file_hash = sha256.hexdigest()

        return cert_id, str(output_path), file_hash, verification_url


certificate_generator = CertificateGenerator()
