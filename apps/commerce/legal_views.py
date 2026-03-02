"""
MixMint Legal & Compliance Views [Spec §9].

Handles:
- GST invoice download
- DJ GST export report
- Legal agreement tracking
"""

from decimal import Decimal
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from apps.commerce.models import Invoice, TaxRecord, Purchase


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_invoice(request, invoice_id):
    """Download GST invoice for a purchase [Spec §9]."""
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
def dj_gst_export(request):
    """DJ GST export report [Spec §9]."""
    if request.user.role != 'dj':
        return Response({'error': 'DJ access only.'}, status=403)

    try:
        dj_profile = request.user.profile.dj_profile
    except Exception:
        return Response({'error': 'DJ profile not found.'}, status=404)

    # Get all invoices where this DJ is the seller
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
