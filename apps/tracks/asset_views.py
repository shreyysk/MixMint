"""DJ asset pack: resource page + operations handbook PDF."""

import io

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render


def asset_pack_view(request):
    return render(request, "dj/asset_pack.html")


@login_required
def asset_handbook_pdf(request):
    """One-page-per-topic operations handbook for DJs (ReportLab)."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=18, spaceAfter=6)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=13, spaceAfter=4, spaceBefore=10)
    body = ParagraphStyle("body", parent=styles["Normal"], fontSize=10, leading=14)

    sections = [
        ("MixMint DJ Operations Handbook", None),
        (
            "1. Uploads & backend links",
            "Upload WAV/MP3/AIFF, or paste any Google Drive, MediaFire or direct download link. "
            "Drive files: Share → 'Anyone with the link (Viewer)'. Use 'Verify link' before publishing — "
            "we check the file downloads. Your original link is never shown to buyers.",
        ),
        (
            "2. Previews",
            "Add your YouTube video and/or Instagram Reel. Both can be attached; buyers toggle "
            "Preview 1 / Preview 2. Playback is always from your embeds — MixMint never hosts previews.",
        ),
        (
            "3. Pricing",
            "Buyer sees one all-inclusive price. Paid tracks minimum ₹29. Re-downloads open at 50% after 3 days; "
            "Download Insurance gives unlimited free re-downloads.",
        ),
        (
            "4. Money & payouts",
            "15% commission (8% Pro). Payouts to UPI or bank only, above ₹500, confirmed by OTP. "
            "Pro upgrades are billed via PhonePe.",
        ),
        (
            "5. Delivery",
            "Buyers download via signed MixMint links. First download caches your file privately for 2 days so "
            "repeat buyers are instant. Links expire and are single-use by default.",
        ),
        (
            "6. Support",
            "File a ticket from Contact, or Telegram for urgent order/download/payout issues. "
            "Refunds/disputes are tracked in-app with visible status.",
        ),
    ]
    elements = []
    for title, text in sections:
        elements.append(Paragraph(title, h1 if text is None else h2))
        if text:
            elements.append(Paragraph(text, body))
        elements.append(Spacer(1, 0.3 * cm))
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="MixMint-DJ-Handbook.pdf"'
    return response
