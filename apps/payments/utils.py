import razorpay
from django.conf import settings

razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

# PhonePe Client Stub [Spec §10]
class PhonePeClient:
    def create_order(self, amount, receipt=None, notes=None):
        # Implementation for PhonePe Order API
        return {
            'id': f'ph_ord_{receipt}',
            'amount': int(amount * 100),
            'status': 'created'
        }

    def verify_signature(self, payment_id, order_id, signature):
        # Implementation for PhonePe Signature Verification
        return True

phonepe_client = PhonePeClient()

def get_payment_client():
    from apps.admin_panel.models import SystemSetting
    setting = SystemSetting.objects.filter(key='active_payment_gateway').first()
    gateway = setting.value.get('gateway', 'razorpay') if setting else 'razorpay'
    
    if gateway == 'phonepe':
        return phonepe_client
    return razorpay_client

def create_order(amount, currency='INR', receipt=None, notes=None):
    client = get_payment_client()
    if hasattr(client, 'order'):
        data = {
            'amount': int(amount * 100), 
            'currency': currency,
            'receipt': receipt,
            'notes': notes or {}
        }
        return client.order.create(data=data)
    else:
        return client.create_order(amount, receipt=receipt, notes=notes)

def verify_payment(payment_id, order_id, signature):
    client = get_payment_client()
    if hasattr(client, 'utility'):
        params_dict = {
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        }
        try:
            client.utility.verify_payment_signature(params_dict)
            return True
        except:
            return False
    else:
        return client.verify_signature(payment_id, order_id, signature)
