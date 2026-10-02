"""DJ asset pack: resource page + operations handbook PDF."""

import io

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render


def asset_pack_view(request):
    return render(request, "dj/asset_pack.html", {
        "logos": [("mixmint-logo-white.png", "Logo for dark backgrounds", "#0B0D0B"),
                  ("mixmint-logo-black.png", "Logo for light backgrounds", "#F1EEE8")],
        "templates_list": [
            ("reel-story-cover-1080x1920.png", "Reel / Story / Short cover", "1080 × 1920", "Instagram Reels and Stories, YouTube Shorts."),
            ("instagram-post-1080x1080.png", "Feed post", "1080 × 1080", "Instagram and Facebook posts."),
            ("youtube-thumbnail-1280x720.png", "YouTube thumbnail", "1280 × 720", "Thumbnail for your preview video."),
            ("youtube-banner-2560x1440.png", "YouTube banner & store cover", "2560 × 1440", "Channel banner and your MixMint store cover. Keep text in the middle 1546 × 423."),
            ("x-header-1500x500.png", "X (Twitter) header", "1500 × 500", "Profile header."),
        ],
    })


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
            "1. Uploads",
            "Upload MP3, WAV, FLAC or AIFF (or one ZIP for an album pack) straight from the upload page. "
            "Files go into MixMint's private storage; buyers only ever get signed, expiring download links.",
        ),
        (
            "2. Previews",
            "Add a YouTube video, an Instagram Reel, or both (at least one). Buyers watch the preview from "
            "your own post, so every preview is a view on your channel. MixMint never hosts previews.",
        ),
        (
            "3. Pricing",
            "Buyers see one all-inclusive price. Paid tracks start at ₹29. Each purchase includes 3 downloads within "
            "7 days on the buyer's first device; after that re-downloads cost 50%. Download Insurance makes them free.",
        ),
        (
            "4. Money & payouts",
            "You keep 85% of every sale (92% on Pro), plus 15% of the ad income from your pages. "
            "Withdraw once a week, any day, from ₹500 to UPI or bank, confirmed with a code we email you.",
        ),
        (
            "5. Delivery",
            "Buyers download from their MixMint library with signed, single-use links. If a file needs a few "
            "minutes to get ready, the buyer gets the link by email (and Telegram) as soon as it is.",
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
