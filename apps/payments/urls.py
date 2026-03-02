from django.urls import path
from .views import initiate_payment, confirm_payment
from .webhooks import razorpay_webhook

urlpatterns = [
    path('initiate/', initiate_payment, name='initiate_payment'),
    path('confirm/', confirm_payment, name='confirm_payment'),
    path('webhook/', razorpay_webhook, name='razorpay_webhook'),
]
