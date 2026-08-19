from django.urls import path
from .views import initiate_purchase, payment_callback, cart_page, cart_checkout
from .webhooks import phonepe_webhook
from .webhooks_razorpay import razorpay_webhook

urlpatterns = [
    # New Gateway-Agnostic endpoints
    path('initiate/', initiate_purchase, name='initiate_payment'),
    path('callback/', payment_callback, name='payment_callback'),
    path('webhook/phonepe/', phonepe_webhook, name='phonepe_webhook'),
    path('webhook/razorpay/', razorpay_webhook, name='razorpay_webhook'),
    # Phase 3 Feature 3: Cart checkout
    path('cart/', cart_page, name='cart_page'),
    path('cart-checkout/', cart_checkout, name='cart_checkout'),
]
