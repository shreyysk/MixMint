from django.urls import path
from django.shortcuts import render
from apps.commerce.legal_views import download_invoice, download_invoice_pdf, dj_gst_export, dj_gst_export_csv


def transparency_page(request):
    return render(request, 'legal/transparency.html')


def terms_page(request):
    return render(request, 'legal/terms.html')


def privacy_page(request):
    return render(request, 'legal/privacy.html')


def refund_page(request):
    return render(request, 'legal/refund.html')


def security_page(request):
    return render(request, 'legal/security.html')


def dmca_page(request):
    return render(request, 'legal/dmca.html')


urlpatterns = [
    path('terms/', terms_page, name='terms'),
    path('privacy/', privacy_page, name='privacy'),
    path('refund/', refund_page, name='refund'),
    path('transparency/', transparency_page, name='transparency'),
    path('security/', security_page, name='security'),
    path('copyright/', dmca_page, name='dmca'),
    # GST Invoice download — JSON and PDF
    path('invoice/<int:invoice_id>/', download_invoice, name='download_invoice'),
    path('invoice/<int:invoice_id>/pdf/', download_invoice_pdf, name='download_invoice_pdf'),
    # DJ GST export — JSON and CSV
    path('gst-export/', dj_gst_export, name='dj_gst_export'),
    path('gst-export/csv/', dj_gst_export_csv, name='dj_gst_export_csv'),
]
