import razorpay
from django.conf import settings
from .base import PaymentGateway

class RazorpayGateway(PaymentGateway):
    """
    Razorpay Test/Dev Payment Gateway Integration.
    """

    def __init__(self):
        self.client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    def create_order(self, amount_paise, currency='INR', order_id=None, metadata=None):
        notes = metadata or {}
        data = {
            'amount': int(amount_paise),
            'currency': currency,
            'receipt': order_id,
            'notes': notes
        }
        order = self.client.order.create(data=data)
        return {
            'success': True,
            'order_id': order['id'],
            'amount': order['amount'],
            'gateway_response': order
        }

    def verify_payment(self, payload, signature):
        # Razorpay signature verification
        # Payload here would be a dict with razorpay_order_id and razorpay_payment_id
        try:
            self.client.utility.verify_payment_signature({
                'razorpay_order_id': payload.get('order_id'),
                'razorpay_payment_id': payload.get('payment_id'),
                'razorpay_signature': signature
            })
            return True
        except:
            return False

    def get_payment_status(self, payment_id):
        payment = self.client.payment.fetch(payment_id)
        status_map = {
            'captured': 'PAYMENT_SUCCESS',
            'failed': 'PAYMENT_DECLINED',
            'authorized': 'PAYMENT_PENDING'
        }
        return {
            'success': payment['status'] == 'captured',
            'status': status_map.get(payment['status'], 'UNKNOWN'),
            'amount': payment['amount'],
            'transaction_id': payment['id'],
            'gateway_response': payment
        }

    def process_refund(self, transaction_id, amount_paise, reason=''):
        refund = self.client.payment.refund(transaction_id, {
            'amount': int(amount_paise),
            'notes': {'reason': reason}
        })
        return {
            'success': True,
            'refund_id': refund['id'],
            'gateway_response': refund
        }

    def create_subscription_order(self, dj_id, plan_type, amount_paise):
        # Razorpay handles subscriptions natively usually, but for consistency we use orders
        return self.create_order(amount_paise, order_id=f"TEST_PRO_{dj_id[:8]}", metadata={'user_id': str(dj_id)})

    def create_overage_order(self, dj_id, overage_gb, amount_paise):
        return self.create_order(amount_paise, order_id=f"TEST_OV_{dj_id[:8]}", metadata={'user_id': str(dj_id)})
