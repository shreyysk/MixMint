import hashlib
import hmac
import base64
import json
import uuid
import requests
from django.conf import settings
from .base import PaymentGateway

class PhonePeGateway(PaymentGateway):
    """
    PhonePe Production Payment Gateway Integration.
    """

    def __init__(self):
        self.merchant_id = getattr(settings, 'PHONEPE_MERCHANT_ID', 'PGTESTPAYUAT')
        self.salt_key = getattr(settings, 'PHONEPE_SALT_KEY', '099eb0cd-02cf-4e2a-8aca-3e6c6aff0399')
        self.salt_index = getattr(settings, 'PHONEPE_SALT_INDEX', '1')
        self.base_url = getattr(settings, 'PHONEPE_BASE_URL', 'https://api-preprod.phonepe.com/apis/pg-sandbox')

    def _generate_checksum(self, payload_base64, endpoint):
        """
        PhonePe checksum = SHA256(payload_base64 + endpoint + salt_key) + "###" + salt_index
        """
        data = payload_base64 + endpoint + self.salt_key
        sha256_hash = hashlib.sha256(data.encode()).hexdigest()
        checksum = sha256_hash + "###" + self.salt_index
        return checksum

    def create_order(self, amount_paise, currency='INR', order_id=None, metadata=None):
        if not order_id:
            order_id = f"MM_{uuid.uuid4().hex[:16].upper()}"

        metadata = metadata or {}
        
        payload = {
            "merchantId": self.merchant_id,
            "merchantTransactionId": order_id,
            "merchantUserId": metadata.get('user_id', 'unknown'),
            "amount": int(amount_paise),
            "redirectUrl": f"{settings.BASE_URL}/payment/callback/?order_id={order_id}",
            "redirectMode": "REDIRECT",
            "callbackUrl": f"{settings.BASE_URL}/payment/webhook/phonepe/",
            "mobileNumber": metadata.get('mobile', ''),
            "paymentInstrument": {
                "type": "PAY_PAGE"
            }
        }

        payload_json = json.dumps(payload)
        payload_base64 = base64.b64encode(payload_json.encode()).decode()

        endpoint = "/pg/v1/pay"
        checksum = self._generate_checksum(payload_base64, endpoint)

        response = requests.post(
            f"{self.base_url}{endpoint}",
            headers={
                "Content-Type": "application/json",
                "X-VERIFY": checksum,
                "X-MERCHANT-ID": self.merchant_id
            },
            json={"request": payload_base64},
            timeout=30
        )

        data = response.json()

        if data.get('success') and data.get('data', {}).get('instrumentResponse'):
            redirect_url = data['data']['instrumentResponse']['redirectInfo']['url']
            return {
                'success': True,
                'order_id': order_id,
                'redirect_url': redirect_url,
                'gateway_response': data
            }
        else:
            raise Exception(f"PhonePe order creation failed: {data.get('message', 'Unknown error')}")

    def verify_payment(self, payload_base64, x_verify_header):
        """
        Verify PhonePe webhook signature [BUG-001 FIX].
        PhonePe S2S callback sends X-VERIFY header = SHA256(response + salt_key) + "###" + salt_index
        Note: For callbacks, the checksum is computed differently than for API requests.
        """
        if not x_verify_header:
            return False
        
        # PhonePe callback signature format: SHA256(base64_payload + salt_key) + "###" + salt_index
        data = payload_base64 + self.salt_key
        sha256_hash = hashlib.sha256(data.encode()).hexdigest()
        expected_signature = sha256_hash + "###" + self.salt_index
        
        return hmac.compare_digest(expected_signature, x_verify_header)

    def get_payment_status(self, merchant_transaction_id):
        endpoint = f"/pg/v1/status/{self.merchant_id}/{merchant_transaction_id}"
        checksum = self._generate_checksum("", endpoint)

        response = requests.get(
            f"{self.base_url}{endpoint}",
            headers={
                "Content-Type": "application/json",
                "X-VERIFY": checksum,
                "X-MERCHANT-ID": self.merchant_id,
                "X-VERIFY-INDEX": self.salt_index
            },
            timeout=30
        )

        data = response.json()
        return {
            'success': data.get('success', False),
            'status': data.get('code', ''), # 'PAYMENT_SUCCESS' | 'PAYMENT_PENDING' | 'PAYMENT_DECLINED'
            'amount': data.get('data', {}).get('amount', 0),
            'transaction_id': data.get('data', {}).get('transactionId', ''),
            'gateway_response': data
        }

    def process_refund(self, original_transaction_id, amount_paise, reason=''):
        refund_id = f"REFUND_{uuid.uuid4().hex[:16].upper()}"

        payload = {
            "merchantId": self.merchant_id,
            "merchantUserId": "INTERNAL",
            "originalTransactionId": original_transaction_id,
            "merchantTransactionId": refund_id,
            "amount": int(amount_paise),
            "callbackUrl": f"{settings.BASE_URL}/payment/webhook/phonepe/refund/"
        }

        payload_json = json.dumps(payload)
        payload_base64 = base64.b64encode(payload_json.encode()).decode()

        endpoint = "/pg/v1/refund"
        checksum = self._generate_checksum(payload_base64, endpoint)

        response = requests.post(
            f"{self.base_url}{endpoint}",
            headers={
                "Content-Type": "application/json",
                "X-VERIFY": checksum
            },
            json={"request": payload_base64},
            timeout=30
        )

        data = response.json()

        if data.get('success'):
            return {
                'success': True,
                'refund_id': refund_id,
                'gateway_response': data
            }
        else:
            raise Exception(f"PhonePe refund failed: {data.get('message', 'Unknown error')}")

    def create_subscription_order(self, dj_id, plan_type, amount_paise):
        from django.utils import timezone
        order_id = f"PRO_{dj_id[:8].upper()}_{timezone.now().strftime('%Y%m%d')}"
        metadata = {
            'user_id': str(dj_id),
            'purpose': 'pro_subscription',
            'plan_type': plan_type
        }
        return self.create_order(amount_paise=amount_paise, order_id=order_id, metadata=metadata)

    def create_overage_order(self, dj_id, overage_gb, amount_paise):
        from django.utils import timezone
        order_id = f"OVERAGE_{dj_id[:8].upper()}_{timezone.now().strftime('%Y%m')}"
        return self.create_order(
            amount_paise=amount_paise,
            order_id=order_id,
            metadata={
                'user_id': str(dj_id),
                'purpose': 'storage_overage',
                'overage_gb': overage_gb
            }
        )
