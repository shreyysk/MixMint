from django.conf import settings

def get_gateway():
    return settings.ACTIVE_GATEWAY

# These functions are kept for backward compatibility if needed, 
# but new code should use settings.ACTIVE_GATEWAY directly or get_gateway()

def create_order(amount_paise, currency='INR', order_id=None, metadata=None):
    gateway = get_gateway()
    return gateway.create_order(amount_paise, currency=currency, order_id=order_id, metadata=metadata)

def verify_payment(payload, signature):
    gateway = get_gateway()
    return gateway.verify_payment(payload, signature)

def get_payment_status(payment_id):
    gateway = get_gateway()
    return gateway.get_payment_status(payment_id)
