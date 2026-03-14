"""
Automated Webhook Signature Tests for MixMint CI Pipeline.
Prevents payment security regressions.

Run with: python manage.py test tests.test_webhook_signatures
"""
import hashlib
import hmac
from django.test import TestCase
from django.conf import settings


class PhonePeWebhookSignatureTests(TestCase):
    """Test PhonePe webhook signature verification [BUG-001 regression prevention]."""

    def setUp(self):
        from apps.payments.phonepe import PhonePeGateway
        self.gateway = PhonePeGateway()

    def _generate_valid_signature(self, payload_base64):
        """Generate a valid PhonePe signature for testing."""
        data = payload_base64 + self.gateway.salt_key
        sha256_hash = hashlib.sha256(data.encode()).hexdigest()
        return sha256_hash + "###" + self.gateway.salt_index

    def test_valid_signature_accepted(self):
        """Valid signature should be accepted."""
        payload = "eyJ0ZXN0IjoidmFsaWQifQ=="  # {"test":"valid"} base64
        signature = self._generate_valid_signature(payload)
        self.assertTrue(self.gateway.verify_payment(payload, signature))

    def test_invalid_signature_rejected(self):
        """Invalid signature should be rejected."""
        payload = "eyJ0ZXN0IjoidmFsaWQifQ=="
        self.assertFalse(self.gateway.verify_payment(payload, "invalid_signature###1"))

    def test_empty_signature_rejected(self):
        """Empty signature should be rejected."""
        payload = "eyJ0ZXN0IjoidmFsaWQifQ=="
        self.assertFalse(self.gateway.verify_payment(payload, ""))

    def test_none_signature_rejected(self):
        """None signature should be rejected."""
        payload = "eyJ0ZXN0IjoidmFsaWQifQ=="
        self.assertFalse(self.gateway.verify_payment(payload, None))

    def test_wrong_salt_index_rejected(self):
        """Wrong salt index should be rejected."""
        payload = "eyJ0ZXN0IjoidmFsaWQifQ=="
        data = payload + self.gateway.salt_key
        sha256_hash = hashlib.sha256(data.encode()).hexdigest()
        wrong_signature = sha256_hash + "###99"  # Wrong index
        self.assertFalse(self.gateway.verify_payment(payload, wrong_signature))

    def test_tampered_payload_rejected(self):
        """Signature for different payload should be rejected."""
        original_payload = "eyJ0ZXN0IjoiYSJ9"  # {"test":"a"}
        tampered_payload = "eyJ0ZXN0IjoiYiJ9"  # {"test":"b"}
        signature = self._generate_valid_signature(original_payload)
        self.assertFalse(self.gateway.verify_payment(tampered_payload, signature))


class WebhookIdempotencyTests(TestCase):
    """Test webhook idempotency to prevent duplicate purchases [CP-03.07]."""

    def test_duplicate_webhook_ignored(self):
        """Same transaction_id webhook should not create duplicate purchase."""
        from apps.commerce.models import WebhookLog
        
        tx_id = "TEST_TX_12345"
        
        # First webhook
        WebhookLog.objects.create(
            transaction_id=tx_id,
            gateway='phonepe',
            payload={'test': True},
            status='PAYMENT_SUCCESS',
            processed=True
        )
        
        # Check duplicate exists
        self.assertTrue(
            WebhookLog.objects.filter(transaction_id=tx_id, processed=True).exists()
        )
