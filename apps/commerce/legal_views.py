"""
MixMint Legal & Compliance Views [Spec §9].

Handles:
- GST invoice download (JSON + PDF)
- DJ GST export report (JSON + CSV)
- Legal agreement tracking
"""

import csv
import io
from decimal import Decimal
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import HttpResponse

from apps.commerce.models import Invoice, TaxRecord


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_invoice(request, invoice_id):
    """Download GST invoice JSON for a purchase [Spec §9]."""
    try:
        invoice = Invoice.objects.get(
            id=invoice_id,
            user=request.user.profile,
        )
    except Invoice.DoesNotExist:
        return Response({'error': 'Invoice not found.'}, status=404)

    tax_records = TaxRecord.objects.filter(invoice=invoice)

    data = {
        'invoice_number': invoice.invoice_number,
        'date': invoice.created_at.isoformat(),
        'buyer': invoice.user.full_name,
        'seller': invoice.dj.dj_name,
        'subtotal': str(invoice.subtotal),
        'tax_details': [{
            'type': tr.tax_type,
            'rate': str(tr.tax_rate),
            'amount': str(tr.tax_amount),
        } for tr in tax_records],
        'total': str(invoice.total_amount),
        'currency': invoice.currency,
        'platform': 'MixMint',
        'platform_url': 'https://mixmint.site',
    }

    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_invoice_pdf(request, invoice_id):
    """
    Download GST invoice as a PDF file [Spec §9].
    Generated using reportlab. Returns Content-Disposition: attachment.
    """
    try:
        invoice = Invoice.objects.get(
            id=invoice_id,
            user=request.user.profile,
        )
    except Invoice.DoesNotExist:
        return HttpResponse('Invoice not found.', status=404)

    tax_records = list(TaxRecord.objects.filter(invoice=invoice))

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_RIGHT, TA_CENTER

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('title', parent=styles['Heading1'], fontSize=20, spaceAfter=6)
        subtitle_style = ParagraphStyle('subtitle', parent=styles['Normal'], fontSize=10, textColor=colors.grey)
        normal = styles['Normal']
        right_style = ParagraphStyle('right', parent=styles['Normal'], alignment=TA_RIGHT)

        elements = []

        # Header
        elements.append(Paragraph("TAX INVOICE (GST)", title_style))
        elements.append(Paragraph("MixMint — Digital Music Distribution", subtitle_style))
        elements.append(Paragraph("https://mixmint.site | support@mixmint.site", subtitle_style))
        elements.append(Spacer(1, 0.5*cm))

        # Invoice metadata
        meta_data = [
            ['Invoice Number:', invoice.invoice_number],
            ['Date:', invoice.created_at.strftime('%d %B %Y')],
            ['Currency:', invoice.currency],
        ]
        meta_table = Table(meta_data, colWidths=[5*cm, 12*cm])
        meta_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 0.5*cm))

        # Parties
        party_data = [
            ['SOLD BY (DJ)', 'SOLD TO (BUYER)'],
            [invoice.dj.dj_name, invoice.user.full_name],
            ['MixMint Partner DJ', invoice.user.user.email],
            ['Platform: MixMint', ''],
        ]
        party_table = Table(party_data, colWidths=[8.5*cm, 8.5*cm])
        party_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a1a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ]))
        elements.append(party_table)
        elements.append(Spacer(1, 0.5*cm))

        # Line items
        items_data = [
            ['Description', 'Amount (INR)'],
            ['Digital Music License', f"₹{invoice.subtotal}"],
        ]
        for tr in tax_records:
            items_data.append([f"{tr.tax_type} @ {tr.tax_rate}%", f"₹{tr.tax_amount}"])
        items_data.append(['TOTAL', f"₹{invoice.total_amount}"])

        items_table = Table(items_data, colWidths=[13*cm, 4*cm])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e91e8c')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 0.5*cm))

        # Footer
        elements.append(Paragraph(
            "This is a system-generated GST invoice. No signature required.",
            subtitle_style
        ))
        elements.append(Paragraph(
            "Anti-Resale Notice: Files are licensed for personal use only. "
            "Resale or redistribution is strictly prohibited.",
            subtitle_style
        ))

        doc.build(elements)
        pdf = buffer.getvalue()
        buffer.close()

    except ImportError:
        # ReportLab not installed — return JSON fallback with 406
        return HttpResponse(
            'PDF generation requires reportlab. Install with: pip install reportlab',
            status=501,
            content_type='text/plain',
        )

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="MixMint-Invoice-{invoice.invoice_number}.pdf"'
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dj_gst_export(request):
    """DJ GST export report as JSON [Spec §9]."""
    if request.user.profile.role != 'dj':
        return Response({'error': 'DJ access only.'}, status=403)

    try:
        dj_profile = request.user.profile.dj_profile
    except Exception:
        return Response({'error': 'DJ profile not found.'}, status=404)

    invoices = Invoice.objects.filter(dj=dj_profile).select_related('purchase')

    report = []
    total_gst = Decimal('0')

    for inv in invoices:
        tax_records = TaxRecord.objects.filter(invoice=inv)
        for tr in tax_records:
            total_gst += tr.tax_amount
            report.append({
                'invoice_number': inv.invoice_number,
                'date': inv.created_at.isoformat(),
                'subtotal': str(inv.subtotal),
                'gst_rate': str(tr.tax_rate),
                'gst_amount': str(tr.tax_amount),
                'total': str(inv.total_amount),
            })

    return Response({
        'dj_name': dj_profile.dj_name,
        'total_gst_collected': str(total_gst),
        'records': report,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dj_gst_export_csv(request):
    """
    DJ GST export report as downloadable CSV file [Spec §9].
    """
    if request.user.profile.role != 'dj':
        return HttpResponse('DJ access only.', status=403)

    try:
        dj_profile = request.user.profile.dj_profile
    except Exception:
        return HttpResponse('DJ profile not found.', status=404)

    invoices = Invoice.objects.filter(dj=dj_profile).select_related('purchase')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="MixMint-GST-Export-{dj_profile.slug}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Invoice Number', 'Date', 'Buyer Name', 'Subtotal (INR)',
        'GST Rate (%)', 'GST Amount (INR)', 'Total (INR)'
    ])

    total_gst = Decimal('0')
    for inv in invoices:
        tax_records = TaxRecord.objects.filter(invoice=inv)
        for tr in tax_records:
            total_gst += tr.tax_amount
            writer.writerow([
                inv.invoice_number,
                inv.created_at.strftime('%Y-%m-%d'),
                inv.user.full_name,
                str(inv.subtotal),
                str(tr.tax_rate),
                str(tr.tax_amount),
                str(inv.total_amount),
            ])

    writer.writerow([])
    writer.writerow(['', '', 'TOTAL GST COLLECTED', '', '', str(total_gst), ''])

    return response

