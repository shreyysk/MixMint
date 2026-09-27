from django.urls import path

from .views import cart_checkout, cart_page, initiate_purchase, payment_callback, razorpay_confirm
from .webhooks import phonepe_webhook
from .webhooks_razorpay import razorpay_webhook

urlpatterns = [
    path("initiate/", initiate_purchase, name="initiate_payment"),
    path("callback/", payment_callback, name="payment_callback"),
    path("razorpay/confirm/", razorpay_confirm, name="confirm_payment"),
    path("webhook/phonepe/", phonepe_webhook, name="phonepe_webhook"),
    path("webhook/razorpay/", razorpay_webhook, name="razorpay_webhook"),
    path("cart/", cart_page, name="cart_page"),
    path("cart-checkout/", cart_checkout, name="cart_checkout"),
]
