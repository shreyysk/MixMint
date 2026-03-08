# 🎛️ MIXMINT — PHASE 1: FOUNDATION
### *Build this first. Platform cannot launch without these.*
### *Version: Final · March 2026*

---

## PHASE 1 SCOPE

```
Goal:         A working platform where DJs can upload,
              buyers can purchase, and downloads are secure.

Includes:
  → Payment gateway (PhonePe — production)
  → Pro Plan + Storage Overage system
  → Core platform fixes (security, auth, uploads, payouts)
  → Critical infrastructure (file delivery, background jobs,
    Supabase lockdown, two-bucket R2, duplicate purchase guard)
  → Compliance (TDS/PAN, fraud detection, session management)
  → Pre-launch QA

Does NOT include:
  → Growth features (bundles, wishlist, embeds, PWA)
  → Polish (Hindi, changelog, ambassador program)
  → Phase 2 or Phase 3 items

Estimated output:
  A fully functional, secure, revenue-generating marketplace
  ready for real DJs and real buyers.
```

---

## PHASE 1 BUILD ORDER

```
Step 1   Section A   PhonePe Payment Gateway
Step 2   Section B   Pro Plan + Storage Overage
Step 3   Section C   Platform Fixes 01–10
         Fix 01:     Refund Policy Engine
         Fix 02:     Custom Domain (Pro feature)
         Fix 03:     Metadata Injection Pipeline
         Fix 04:     Search Ranking Algorithm
         Fix 05:     Collaboration Edge Cases
         Fix 06:     2FA (TOTP)
         Fix 07:     DJ Onboarding Wizard
         Fix 08:     Content Reporting
         Fix 09:     Star Ratings
         Fix 10:     Payout Bank/UPI Details
Step 4   Section D   Improvements 01–06 (Critical)
         Imp 01:     Dispute Resolution
         Imp 02:     Account Deletion & Data Export
         Imp 03:     Fraud Detection
         Imp 04:     TDS / PAN Compliance
         Imp 05:     Session Management
         Imp 06:     Verified Badge System
Step 5   Section E   Infrastructure Gaps (Critical)
         Gap 02:     Supabase API Lockdown
         Gap 03:     Large File Delivery (CF Worker)
         Gap 05:     Background Job System
         Gap 06:     DJ Username System
         Gap 07:     Two-Bucket R2
         Gap 08:     Search Infrastructure
         Gap 10:     File Format Standards
         Gap 20:     Duplicate Purchase Guard
Step 6   Section F   Full QA — all phases
```

---


# ═══════════════════════════════════════════════════
# SECTION A — PAYMENT GATEWAY (PHONEPE — PRODUCTION)
# ═══════════════════════════════════════════════════
### *Replace every Razorpay reference. PhonePe is the production gateway.*

---

## ⚠️ CORRECTION NOTICE

Across all previous MixMint prompts, Razorpay was referenced as the payment gateway.

**This is wrong for production.**

```
Razorpay:   Testing only — sandbox/dev environment
PhonePe:    Production — all real money flows through PhonePe

Every reference to Razorpay in previous docs = replace with PhonePe
```

The payment abstraction layer (PaymentGateway base class) built in the
gateway migration prompt is exactly right — just implement PhonePeGateway
as the active class and keep RazorpayGateway for test environment only.

---

## 🏗️ GATEWAY ABSTRACTION (FINAL)

```python
# payment_gateway/base.py
from abc import ABC, abstractmethod
from decimal import Decimal

class PaymentGateway(ABC):

    @abstractmethod
    def create_order(self, amount_paise, currency,
                     order_id, metadata): pass

    @abstractmethod
    def verify_payment(self, payload, signature): pass

    @abstractmethod
    def process_refund(self, payment_id, amount_paise,
                       reason): pass

    @abstractmethod
    def get_payment_status(self, payment_id): pass

    @abstractmethod
    def create_subscription(self, plan_id, customer_data): pass

    @abstractmethod
    def cancel_subscription(self, subscription_id): pass


# settings.py
import os

if os.environ.get('ENVIRONMENT') == 'production':
    from payment_gateway.phonepe_gateway import PhonePeGateway
    ACTIVE_GATEWAY = PhonePeGateway()
else:
    from payment_gateway.razorpay_gateway import RazorpayGateway
    ACTIVE_GATEWAY = RazorpayGateway()  # test only
```

---

## 📱 PHONEPE GATEWAY — FULL IMPLEMENTATION

### Credentials & Setup

```python
# payment_gateway/phonepe_gateway.py

import hashlib
import hmac
import base64
import json
import uuid
import requests
from decimal import Decimal
from django.conf import settings

class PhonePeGateway(PaymentGateway):

    def __init__(self):
        self.merchant_id = settings.PHONEPE_MERCHANT_ID
        self.salt_key = settings.PHONEPE_SALT_KEY
        self.salt_index = settings.PHONEPE_SALT_INDEX  # usually '1'
        self.base_url = settings.PHONEPE_BASE_URL
        # Production: https://api.phonepe.com/apis/hermes
        # Sandbox:    https://api-preprod.phonepe.com/apis/pg-sandbox

    def _generate_checksum(self, payload_base64, endpoint):
        """
        PhonePe checksum = SHA256(payload_base64 + endpoint + salt_key)
                           + "###" + salt_index
        """
        data = payload_base64 + endpoint + self.salt_key
        sha256_hash = hashlib.sha256(data.encode()).hexdigest()
        checksum = sha256_hash + "###" + self.salt_index
        return checksum
```

---

### One-Time Payment (Track / Album / Bundle Purchase)

```python
    def create_order(self, amount_paise, currency='INR',
                     order_id=None, metadata=None):
        """
        Creates a PhonePe payment request.
        amount_paise: amount in paise (₹49 = 4900)
        Returns: redirect URL for buyer
        """
        if not order_id:
            order_id = f"MM_{uuid.uuid4().hex[:16].upper()}"

        payload = {
            "merchantId": self.merchant_id,
            "merchantTransactionId": order_id,
            "merchantUserId": metadata.get('user_id', ''),
            "amount": amount_paise,
            "redirectUrl": (
                f"{settings.BASE_URL}/payment/callback/"
                f"?order_id={order_id}"
            ),
            "redirectMode": "REDIRECT",
            "callbackUrl": f"{settings.BASE_URL}/payment/webhook/phonepe/",
            "mobileNumber": metadata.get('mobile', ''),
            "paymentInstrument": {
                "type": "PAY_PAGE"  # Shows full PhonePe payment page
            }
        }

        # Encode payload
        payload_json = json.dumps(payload)
        payload_base64 = base64.b64encode(
            payload_json.encode()
        ).decode()

        # Generate checksum
        endpoint = "/pg/v1/pay"
        checksum = self._generate_checksum(payload_base64, endpoint)

        # Make API call
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

        if (data.get('success') and
                data.get('data', {}).get('instrumentResponse')):
            redirect_url = (
                data['data']['instrumentResponse']
                ['redirectInfo']['url']
            )
            return {
                'success': True,
                'order_id': order_id,
                'redirect_url': redirect_url,
                'gateway_response': data
            }
        else:
            raise Exception(
                f"PhonePe order creation failed: "
                f"{data.get('message', 'Unknown error')}"
            )
```

---

### Payment Verification (Webhook + Status Check)

```python
    def verify_payment(self, payload, signature):
        """
        Verify PhonePe webhook callback.
        payload: base64-encoded response from PhonePe
        signature: X-VERIFY header value
        """
        # Recompute checksum
        expected = self._generate_checksum(
            payload,
            "/pg/v1/pay"  # endpoint used in original request
        )
        return hmac.compare_digest(expected, signature)


    def get_payment_status(self, merchant_transaction_id):
        """
        Check payment status by transaction ID.
        Use this to confirm payment after redirect (don't trust
        redirect params — always verify server-side).
        """
        endpoint = (
            f"/pg/v1/status/"
            f"{self.merchant_id}/{merchant_transaction_id}"
        )
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
            'status': data.get('code', ''),
            # 'PAYMENT_SUCCESS' | 'PAYMENT_PENDING' | 'PAYMENT_DECLINED'
            'amount': data.get('data', {}).get('amount', 0),
            'transaction_id': (
                data.get('data', {}).get('transactionId', '')
            ),
            'gateway_response': data
        }
```

---

### Refund Processing

```python
    def process_refund(self, original_transaction_id,
                       amount_paise, reason=''):
        """
        PhonePe refund via their Refund API.
        """
        refund_id = f"REFUND_{uuid.uuid4().hex[:16].upper()}"

        payload = {
            "merchantId": self.merchant_id,
            "merchantUserId": "",
            "originalTransactionId": original_transaction_id,
            "merchantTransactionId": refund_id,
            "amount": amount_paise,
            "callbackUrl": (
                f"{settings.BASE_URL}/payment/webhook/phonepe/refund/"
            )
        }

        payload_json = json.dumps(payload)
        payload_base64 = base64.b64encode(
            payload_json.encode()
        ).decode()

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
            raise Exception(
                f"PhonePe refund failed: "
                f"{data.get('message', 'Unknown error')}"
            )
```

---

### Pro Plan Subscription Billing (Recurring)

**Important:** PhonePe's subscription/recurring payment API requires
additional merchant agreement. Apply for this separately during
merchant onboarding. Until approved, handle recurring manually
(create new order each billing cycle via backend cron).

```python
    def create_subscription_order(self, dj_id, plan_type,
                                   amount_paise):
        """
        For Pro Plan billing.
        PhonePe doesn't have a Razorpay-style subscription object.
        Instead: create a new payment order each billing cycle.
        Store subscription state in MixMint DB, not PhonePe.
        """
        order_id = (
            f"PRO_{dj_id[:8].upper()}_"
            f"{timezone.now().strftime('%Y%m%d')}"
        )

        metadata = {
            'user_id': dj_id,
            'purpose': 'pro_subscription',
            'plan_type': plan_type
        }

        return self.create_order(
            amount_paise=amount_paise,
            order_id=order_id,
            metadata=metadata
        )

    def create_overage_order(self, dj_id, overage_gb,
                              amount_paise):
        """Storage overage billing — separate order per billing cycle"""
        order_id = (
            f"OVERAGE_{dj_id[:8].upper()}_"
            f"{timezone.now().strftime('%Y%m')}"
        )
        return self.create_order(
            amount_paise=amount_paise,
            order_id=order_id,
            metadata={
                'user_id': dj_id,
                'purpose': 'storage_overage',
                'overage_gb': overage_gb
            }
        )
```

---

## 🔗 DJANGO VIEWS — PAYMENT FLOW

### Step 1: Create Payment Order

```python
# views/payment.py

from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

@login_required
@require_POST
def initiate_purchase(request):
    """
    Buyer clicks "Buy & Download" → this view creates order
    """
    content_id = request.POST.get('content_id')
    content_type = request.POST.get('content_type')  # track|album|bundle

    # 1. Run fraud checks
    fraud_result, risk, flags = run_fraud_checks(
        request.user.id,
        {
            'ip_address': get_client_ip(request),
            'device_hash': get_device_hash(request),
            'content_id': content_id
        }
    )
    if not fraud_result:
        return JsonResponse(
            {'error': 'Purchase could not be processed'},
            status=403
        )

    # 2. Get content + calculate price server-side (never trust client)
    content = get_content_object(content_id, content_type)
    amount_paise = calculate_total_price_paise(content)
    # calculate_total_price_paise includes:
    # - base price
    # - platform fee (if admin-enabled)
    # - GST (if admin-enabled)
    # All folded into one number

    # 3. Create pending purchase record
    order_id = f"MM_{uuid.uuid4().hex[:16].upper()}"
    purchase = Purchase.objects.create(
        user_id=request.user.id,
        content_type=content_type,
        content_id=content_id,
        gateway_order_id=order_id,
        payment_gateway='phonepe',
        amount_paise=amount_paise,
        status='pending',
        ip_address=get_client_ip(request),
        device_hash=get_device_hash(request)
    )

    # 4. Create PhonePe order
    gateway = settings.ACTIVE_GATEWAY
    result = gateway.create_order(
        amount_paise=amount_paise,
        order_id=order_id,
        metadata={
            'user_id': str(request.user.id),
            'purchase_id': str(purchase.id)
        }
    )

    return JsonResponse({
        'redirect_url': result['redirect_url'],
        'order_id': order_id
    })
```

---

### Step 2: Payment Callback (Redirect After Payment)

```python
def payment_callback(request):
    """
    User lands here after PhonePe payment page.
    NEVER trust URL params — always verify via status API.
    """
    order_id = request.GET.get('order_id')

    if not order_id:
        return redirect('/payment/failed/')

    # Verify status via API (not redirect params)
    gateway = settings.ACTIVE_GATEWAY
    status = gateway.get_payment_status(order_id)

    purchase = Purchase.objects.get(gateway_order_id=order_id)

    if status['success'] and status['status'] == 'PAYMENT_SUCCESS':
        return handle_payment_success(purchase, status)
    else:
        return handle_payment_failure(purchase, status)


def handle_payment_success(purchase, gateway_status):
    with transaction.atomic():
        purchase.status = 'paid'
        purchase.gateway_payment_id = gateway_status['transaction_id']
        purchase.gateway_response = gateway_status['gateway_response']
        purchase.paid_at = timezone.now()
        purchase.save()

        # Distribute earnings to DJ wallet
        distribute_earnings(purchase)

        # Generate GST invoice async
        queue_invoice_generation(purchase.id)

        # Send purchase confirmation email
        send_purchase_confirmation_email(purchase)

    # Redirect to download page
    return redirect(f'/download/?purchase_id={purchase.id}')


def handle_payment_failure(purchase, gateway_status):
    purchase.status = 'failed'
    purchase.gateway_response = gateway_status['gateway_response']
    purchase.save()
    return redirect(f'/payment/failed/?order_id={purchase.gateway_order_id}')
```

---

### Step 3: Webhook Handler (Server-to-Server)

```python
@csrf_exempt
def phonepe_webhook(request):
    """
    PhonePe sends server-to-server notifications.
    This is the authoritative payment confirmation.
    """
    if request.method != 'POST':
        return HttpResponse(status=405)

    # Get signature from header
    x_verify = request.headers.get('X-VERIFY', '')

    # Get payload
    body = request.body.decode('utf-8')

    try:
        data = json.loads(body)
        payload_base64 = data.get('response', '')
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    # Verify signature
    gateway = settings.ACTIVE_GATEWAY
    if not gateway.verify_payment(payload_base64, x_verify):
        # Log failed verification attempt
        log_webhook_security_event(request, 'signature_mismatch')
        return HttpResponse(status=401)

    # Decode payload
    payload_json = base64.b64decode(payload_base64).decode()
    payload = json.loads(payload_json)

    # Extract transaction details
    transaction_id = payload.get('data', {}).get('merchantTransactionId')
    payment_status = payload.get('code', '')

    # Idempotency check — don't process same webhook twice
    if WebhookLog.objects.filter(
        transaction_id=transaction_id,
        processed=True
    ).exists():
        return HttpResponse(status=200)  # Already processed, acknowledge

    # Log webhook
    webhook_log = WebhookLog.objects.create(
        transaction_id=transaction_id,
        payload=payload,
        status=payment_status
    )

    # Process based on status
    try:
        if payment_status == 'PAYMENT_SUCCESS':
            process_successful_payment_webhook(transaction_id, payload)
        elif payment_status in ['PAYMENT_DECLINED', 'PAYMENT_ERROR']:
            process_failed_payment_webhook(transaction_id, payload)
        elif payment_status == 'REFUND_SUCCESS':
            process_refund_webhook(transaction_id, payload)

        webhook_log.processed = True
        webhook_log.save()

    except Exception as e:
        webhook_log.error = str(e)
        webhook_log.save()
        # Return 200 anyway — PhonePe will retry on 4xx/5xx
        # Log to Sentry for investigation

    return HttpResponse(status=200)
```

---

## 💰 PRO PLAN BILLING VIA PHONEPE

Since PhonePe doesn't have a native subscription object like Razorpay,
MixMint manages subscription state internally and triggers payments
via backend cron job.

### Subscription State Machine (DB-managed)

```
States:
  trial_active    → Pro features ON, no charge yet
  trial_expired   → trial ended, no payment added → downgrade
  active_monthly  → paid, renews each month
  active_annual   → paid, renews each year
  grace_period    → payment failed, 7 days to retry
  cancelled       → cancelled, active until period end
  expired         → period ended, downgraded to Standard
```

### Monthly Renewal Cron (runs daily at 9 AM IST)

```python
def process_pro_renewals():
    """
    Find all Pro DJs whose billing date is today.
    Create PhonePe payment orders for renewal.
    Send payment link via email.
    """
    today = timezone.now().date()

    due_renewals = Profile.objects.filter(
        is_pro_dj=True,
        pro_plan_type='monthly',
        pro_expires_at__date=today,
        pro_status='active_monthly'
    )

    for dj in due_renewals:
        try:
            gateway = settings.ACTIVE_GATEWAY
            amount_paise = get_pro_monthly_price_paise()

            # Check for overage to add
            overage = StorageOverage.objects.filter(
                dj_id=dj.id,
                billing_period=get_current_billing_period(dj),
                status='pending'
            ).first()

            if overage:
                amount_paise += overage.amount_due

            result = gateway.create_subscription_order(
                dj_id=str(dj.id),
                plan_type='monthly',
                amount_paise=amount_paise
            )

            # Send renewal payment link to DJ email
            send_pro_renewal_payment_email(
                dj_id=dj.id,
                payment_url=result['redirect_url'],
                amount_paise=amount_paise,
                overage_included=overage is not None
            )

            # Mark renewal as pending
            dj.pro_status = 'renewal_pending'
            dj.save()

        except Exception as e:
            # Log failure, alert admin
            log_renewal_failure(dj.id, str(e))
```

### What DJ Sees for Renewal

Email subject: *"Your MixMint Pro renewal is ready — ₹299"*

```
Your Pro plan renews today.

Amount: ₹299 (monthly)
[+ ₹90 storage overage — 3GB over limit]  ← if applicable
─────────────────────────────────────────
Total: ₹389

[Pay Now via PhonePe →]

Link expires in 24 hours. If not paid, your 7-day grace period begins.
```

---

## 🔄 OVERAGE BILLING

Overage is billed as a **separate PhonePe order** each month,
not combined with Pro renewal (simpler to reconcile).

```python
def bill_storage_overage(dj_id, overage_gb, amount_paise):
    gateway = settings.ACTIVE_GATEWAY

    result = gateway.create_overage_order(
        dj_id=dj_id,
        overage_gb=overage_gb,
        amount_paise=amount_paise
    )

    send_overage_payment_email(
        dj_id=dj_id,
        payment_url=result['redirect_url'],
        overage_gb=overage_gb,
        amount_paise=amount_paise
    )
```

---

## 🔁 REFUND FLOW (PHONEPE)

Replace all Razorpay refund references with:

```python
def process_approved_refund(refund_request_id):
    refund_request = RefundRequest.objects.get(id=refund_request_id)
    purchase = refund_request.purchase

    gateway = settings.ACTIVE_GATEWAY

    with transaction.atomic():
        # Issue refund via PhonePe
        result = gateway.process_refund(
            original_transaction_id=purchase.gateway_payment_id,
            amount_paise=purchase.amount_paise,
            reason=refund_request.reason
        )

        # Clawback DJ earnings
        DJWallet.objects.filter(dj_id=purchase.dj_id).update(
            pending_earnings=F('pending_earnings') - purchase.dj_revenue,
            total_earnings=F('total_earnings') - purchase.dj_revenue
        )

        # Update purchase status
        purchase.status = 'refunded'
        purchase.gateway_refund_id = result['refund_id']
        purchase.refunded_at = timezone.now()
        purchase.save()

        # Update refund request
        refund_request.status = 'approved'
        refund_request.gateway_refund_id = result['refund_id']
        refund_request.resolved_at = timezone.now()
        refund_request.save()

        # Notify buyer and DJ
        send_refund_approved_email(refund_request)
        send_dj_earnings_clawback_email(purchase.dj_id, purchase)
```

---

## 🔐 ENVIRONMENT VARIABLES

```bash
# .env.production — NEVER commit this file

# PhonePe (Production)
PHONEPE_MERCHANT_ID=your_merchant_id
PHONEPE_SALT_KEY=your_salt_key
PHONEPE_SALT_INDEX=1
PHONEPE_BASE_URL=https://api.phonepe.com/apis/hermes
ENVIRONMENT=production

# PhonePe (Sandbox — for staging)
# PHONEPE_MERCHANT_ID=PGTESTPAYUAT
# PHONEPE_SALT_KEY=099eb0cd-02cf-4e2a-8aca-3e6c6aff0399
# PHONEPE_SALT_INDEX=1
# PHONEPE_BASE_URL=https://api-preprod.phonepe.com/apis/pg-sandbox
# ENVIRONMENT=staging

# Razorpay (Test only — dev environment)
RAZORPAY_KEY_ID=rzp_test_xxxx
RAZORPAY_KEY_SECRET=xxxx
```

---

## 🛡️ PRODUCTION SAFETY GUARD

```python
# In Django startup — settings.py bottom

if ENVIRONMENT == 'production':
    # Ensure PhonePe is active
    assert isinstance(ACTIVE_GATEWAY, PhonePeGateway), (
        "Production must use PhonePeGateway, not RazorpayGateway"
    )
    # Ensure sandbox URL is not used
    assert 'preprod' not in PHONEPE_BASE_URL, (
        "Production is using PhonePe SANDBOX URL. "
        "Set PHONEPE_BASE_URL to production endpoint."
    )
    # Ensure Razorpay test keys are not present
    assert not RAZORPAY_KEY_ID.startswith('rzp_test_'), (
        "Production environment has Razorpay TEST keys set. "
        "This is a configuration error."
    )
```

---

## 📊 DB SCHEMA (GATEWAY-AGNOSTIC — FINAL VERSION)

```sql
-- Replace any Razorpay-specific columns with these:

ALTER TABLE purchases
  -- Remove if exists: razorpay_order_id, razorpay_payment_id
  ADD COLUMN IF NOT EXISTS payment_gateway VARCHAR(20) DEFAULT 'phonepe',
    -- 'phonepe' (production) | 'razorpay' (test)
  ADD COLUMN IF NOT EXISTS gateway_order_id VARCHAR(100),
  ADD COLUMN IF NOT EXISTS gateway_payment_id VARCHAR(100),
  ADD COLUMN IF NOT EXISTS gateway_refund_id VARCHAR(100),
  ADD COLUMN IF NOT EXISTS gateway_response JSONB,
  ADD COLUMN IF NOT EXISTS amount_paise INTEGER,
  ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'pending',
    -- 'pending' | 'paid' | 'failed' | 'refunded' | 'disputed'
  ADD COLUMN IF NOT EXISTS paid_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS refunded_at TIMESTAMPTZ;

-- Webhook idempotency log
CREATE TABLE IF NOT EXISTS webhook_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  gateway VARCHAR(20),
  transaction_id VARCHAR(100) UNIQUE,
  payload JSONB,
  status VARCHAR(50),
  processed BOOLEAN DEFAULT FALSE,
  error TEXT,
  received_at TIMESTAMPTZ DEFAULT NOW()
);

-- Pro subscription events (gateway-agnostic)
CREATE TABLE IF NOT EXISTS pro_subscription_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  dj_id UUID REFERENCES profiles(id),
  event_type VARCHAR(50),
    -- 'trial_start' | 'payment_initiated' | 'payment_success'
    -- | 'payment_failed' | 'grace_start' | 'downgraded'
    -- | 'cancelled' | 'renewed'
  plan_type VARCHAR(10),
  amount_paise INTEGER,
  gateway VARCHAR(20) DEFAULT 'phonepe',
  gateway_order_id VARCHAR(100),
  gateway_payment_id VARCHAR(100),
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 📋 PHONEPE MERCHANT ONBOARDING CHECKLIST

Complete before launch:

```
Documents needed:
[ ] Business PAN card
[ ] GST registration certificate (or non-registration declaration)
[ ] Business bank account details
[ ] Cancelled cheque
[ ] Business address proof
[ ] Website URL (must be live — not under construction)
[ ] Business description and category

Technical setup:
[ ] Apply at business.phonepe.com
[ ] Submit all documents
[ ] Wait for approval (typically 1–2 weeks)
[ ] Receive Merchant ID + Salt Key
[ ] Test in PhonePe sandbox first:
    Sandbox Merchant ID: PGTESTPAYUAT
    Salt Key: 099eb0cd-02cf-4e2a-8aca-3e6c6aff0399
[ ] Complete 5+ successful sandbox transactions
[ ] Register production webhook URL in PhonePe dashboard:
    https://mixmint.site/payment/webhook/phonepe/
[ ] Register refund webhook URL:
    https://mixmint.site/payment/webhook/phonepe/refund/
[ ] Test production with ₹1 real transaction
[ ] Confirm settlement arrives in bank account
[ ] Enable recurring payment agreement (for Pro plan)

Post-launch:
[ ] Monitor first 50 transactions manually
[ ] Check settlement timing (T+1 or T+2 days typically)
[ ] Set up PhonePe merchant dashboard alerts
[ ] Save PhonePe merchant support number
```

---

## 🔄 WHERE TO UPDATE ACROSS ALL PREVIOUS PROMPTS

Every place in previous documents that said "Razorpay" in a
production context — replace with PhonePe:

```
Document                     Replace
─────────────────────────────────────────────────────────────
v2 Prompt (Section 7)        Checkout → PhonePe gateway
v2 Prompt (Section 16)       GST Invoice → PhonePe transaction ID
Test Prompt (Phase 4)        All checkout tests → PhonePe flow
All Fixes (Fix 01)           Refund → gateway.process_refund()
All Fixes (Fix 04)           TDS payout → PhonePe settlement
Improvements Pt1 (Fix 03)    Fraud detection → pre-PhonePe order
Pro Plan Prompt              Pro billing → PhonePe orders
Storage Overage Prompt       Overage billing → PhonePe orders

Invoice PDF copy:
  Change: "Payment Method: Razorpay / PhonePe"
  To:     "Payment Method: PhonePe"

Checkout page copy:
  Remove any Razorpay branding
  PhonePe logo/branding in payment button area

Error messages:
  "Payment failed via Razorpay" → "Payment could not be processed"
  Never mention gateway name in user-facing error messages
```

---

## ✅ UX COPY — PHONEPE SPECIFIC

**Checkout button:**
```
[Pay ₹49 via PhonePe]
```
Show PhonePe logo beside the button (use their official brand assets).

**Payment processing screen:**
```
Redirecting to PhonePe...
You'll be brought back to MixMint after payment.
```

**Payment success:**
```
✓ Payment confirmed via PhonePe
Preparing your secure download...
```

**Payment failed:**
```
Payment could not be completed.
Please try again or use a different payment method.
[Try Again]
```
Never say "PhonePe declined" — just "could not be completed."

**Invoice footer:**
```
Paid via PhonePe  ·  Transaction ID: [gateway_payment_id]
```

---

*End of PhonePe Integration Prompt*
*Razorpay = test environment only*
*PhonePe = all production money flows*
*Gateway abstraction layer ensures clean separation*

---


# ═══════════════════════════════════════════════════
# SECTION B — PRO PLAN & STORAGE OVERAGE SYSTEM
# ═══════════════════════════════════════════════════
# 🎛️ MIXMINT — PRO PLAN COMPLETE PROMPT
### *Attractive to DJs. Profitable for MixMint. Admin-controlled.*

---

## 💡 DESIGN PHILOSOPHY

The Pro Plan must feel like an **obvious yes** for any DJ who is serious about their music business — not a luxury upsell. Every feature must solve a real pain point DJs already have. The pricing must be set so that a DJ who earns even ₹3,000/month in sales is financially better off on Pro than Standard.

The plan must also be **more profitable for MixMint at scale** — not less. The subscription fee must more than compensate for the reduced commission on high-earning DJs.

---

## 📦 PLAN STRUCTURE

### Two Tiers — Standard vs Pro

```
                    STANDARD            PRO
                    ────────            ───────────────────
Storage             3 GB                20 GB
Commission          Admin-set %         Admin-set Pro %
                    (e.g. 10%)          (e.g. 7% — always lower than Standard)
Search placement    Standard            Priority boost
Custom domain       ✗                   ✓
Ad exposure         Full ads            Reduced ads on storefront
                    on storefront       (buyers still see ads)
Storefront badge    —                   ⚡ PRO badge
Analytics           Basic earnings      Enhanced earnings breakdown
Upload queue        Standard review     Priority admin review
Collaborators       Up to 3             Up to 5
Payout threshold    ₹500                ₹250 (lower threshold)
Billing             Free                Monthly or Annual
Trial               —                   7 days free
```

---

## 💰 PRICING & PROFITABILITY MODEL

### Admin-Controlled Rates (both commission rates set in Admin → Offers & Pricing)

```
Standard commission:   Admin-set  (launch: 10%)
Pro commission:        Admin-set  (launch: 7%)  — always kept below Standard
```

### Suggested Pro Pricing (admin can adjust)

```
Monthly:   ₹299/month
Annual:    ₹2,499/year  (saves ₹1,089 vs monthly — effectively 3 months free)
```

### Profitability Check — Why This Works

```
Scenario: DJ earns ₹10,000/month in sales

Standard plan:
  Commission (10%):        ₹1,000 → MixMint
  Subscription:            ₹0
  MixMint earns:           ₹1,000/month

Pro plan (monthly ₹299):
  Commission (7%):         ₹700 → MixMint
  Subscription fee:        ₹299 → MixMint
  MixMint earns:           ₹999/month
  ─────────────────────────────────────
  Difference:              −₹1/month  ← nearly identical at ₹10K

Pro plan (annual ₹2,499):
  Commission (7%):         ₹700/month × 12 = ₹8,400
  Subscription:            ₹2,499/year
  MixMint earns:           ₹10,899/year = ₹908/month
  Standard equivalent:     ₹12,000/year
  ─────────────────────────────────────
  MixMint earns less on annual for low earners ← acknowledged
  But Pro DJs earn MORE which means they sell MORE which grows the platform

Scenario: DJ earns ₹30,000/month in sales

Standard:  ₹3,000/month to MixMint
Pro monthly: ₹2,100 + ₹299 = ₹2,399/month to MixMint
Pro annual:  ₹2,100 + ₹208 = ₹2,308/month to MixMint

DJ saves: ₹9,000 - ₹7,476 = ₹1,524/year net on Pro annual
MixMint loses: ₹692/month vs Standard

IMPORTANT ADMIN RULE:
─────────────────────────────────────────────────────────
For Pro to always be profitable vs Standard:
Pro must be offered only when:
  (Standard_commission% - Pro_commission%) × avg_monthly_sales
  < Pro subscription fee

At ₹299/month and 3% commission gap:
  Break-even sales = ₹299 / 0.03 = ₹9,967/month

Translation: Pro is profitable for MixMint only when DJ earns
ABOVE ₹10,000/month. Below that, Standard earns MixMint more.

THEREFORE: Show the upgrade prompt strategically — only to DJs
who have demonstrated ₹5,000+/month in consistent earnings.
Don't show Pro to new DJs who haven't proven sales volume yet.
─────────────────────────────────────────────────────────
```

---

## 🎨 PRO PLAN PAGE UI/UX

### URL: `/pro` — Public page, accessible to all

### Page Structure

---

#### Hero Section

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│         ⚡  MixMint Pro                                      │
│                                                              │
│    Your music business.                                      │
│    At full power.                                            │
│                                                              │
│    More storage. Lower commission. Your own domain.         │
│    Built for DJs who are serious about selling.             │
│                                                              │
│    [ Start 7-Day Free Trial ]   [ See What's Included ↓ ]  │
│                                                              │
│    No credit card required for trial.                       │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

- Background (dark): deep near-black with a single sharp diagonal mint gradient stripe — not a blob, a precise geometric band across the hero. Subtle. Like a spotlight on a stage.
- Background (light): warm cream with a thin amber diagonal band
- Headline: Clash Display 72px, two lines, tight tracking
- Sub-headline: Satoshi 20px muted
- CTA: mint filled button, 56px — `Start 7-Day Free Trial`
- Secondary: ghost button — `See What's Included ↓` — scrolls to comparison
- Trial note: DM Mono 12px muted — *"No credit card required for trial."*

---

#### The Math Section — "Does Pro Pay For Itself?"

This is the most important section. Make the financial case visually.

```
┌──────────────────────────────────────────────────────────────┐
│  DOES PRO PAY FOR ITSELF?                                    │
│  — Yes. Here's the exact number.                            │
│                                                              │
│  Your monthly sales: [ ₹ _______  ]  ← live input slider   │
│                                                              │
│  ┌─────────────────────┐  ┌─────────────────────┐          │
│  │   STANDARD          │  │   PRO               │          │
│  │                     │  │                     │          │
│  │   10% commission    │  │   7% commission     │          │
│  │   You keep: ₹9,000  │  │   You keep: ₹9,300  │          │
│  │   Platform: ₹1,000  │  │   Sub fee:  ₹299    │          │
│  │                     │  │   You save: ₹ 1     │          │  ← dynamic
│  └─────────────────────┘  └─────────────────────┘          │
│                                                              │
│  At ₹10,000/month in sales, Pro pays for itself.           │
│  Above that, every rupee saved goes straight to you.        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Interaction:**
- Slider or text input: DJ enters their monthly sales estimate
- Both cards update live — showing exact keep/commission amounts
- Below the cards: a single sentence updates: *"At ₹X/month, you save ₹Y/month on Pro."*
- When sales are below break-even: honest message — *"At this sales volume, plans are nearly equal. Pro becomes more valuable as your sales grow."*
- This section builds trust — you're not hiding the math

**Design:**
- Two cards side by side, Standard vs Pro
- Pro card: mint left border 3px, slightly elevated (4px shadow)
- Active savings highlighted in mint bold
- Slider: custom styled, mint thumb, DM Mono value display

---

#### Feature Comparison Table

```
┌──────────────────────────────────────────────────────────┐
│                        STANDARD        PRO               │
├──────────────────────────────────────────────────────────┤
│  Storage               3 GB            20 GB  ←  7×      │
│  Commission            10%             7%     ←  saves ₹ │
│  Custom domain         —               ✓                  │
│  Search priority       Standard        ⚡ Boosted         │
│  Storefront badge      —               ⚡ PRO             │
│  Collaborators         3 max           5 max              │
│  Payout threshold      ₹500            ₹250               │
│  Upload review         Standard        Priority           │
│  Ad exposure           Full            Reduced*           │
│  Monthly price         Free            ₹299/mo            │
│  Annual price          —               ₹2,499/yr          │
└──────────────────────────────────────────────────────────┘
* Buyers still see ads. Ads are removed from YOUR view of your storefront.
```

- Table: clean, no heavy borders — just subtle row dividers
- Pro column: mint header, slightly warm background
- Checkmarks: mint ✓, X marks: muted —
- `← 7×` and `← saves ₹` annotations: DM Mono 11px amber — draw the eye to value
- Footer note on ads: small, honest, italic

---

#### Pricing Cards

```
┌──────────────────────┐      ┌──────────────────────────────┐
│   MONTHLY            │      │   ANNUAL           BEST VALUE│
│                      │      │                              │
│   ₹299               │      │   ₹2,499 / year             │
│   per month          │      │   = ₹208/month              │
│                      │      │                              │
│   Billed monthly     │      │   Save ₹1,089 vs monthly    │
│   Cancel anytime     │      │   That's 3 months free       │
│                      │      │                              │
│   [Start Free Trial] │      │   [Start Free Trial]         │
└──────────────────────┘      └──────────────────────────────┘

Both plans include a 7-day free trial. No card required to start.
```

**Design:**
- Annual card: slightly larger, `BEST VALUE` amber badge top-right
- Annual shows monthly equivalent prominently — ₹208/mo
- "3 months free" framing — more compelling than "save 30%"
- Both CTAs identical — don't push annual over monthly
- Below both cards: *"Both plans include a 7-day free trial. No card required to start."* — DM Mono 12px muted, centered

---

#### Social Proof Strip (Once You Have DJs)

Placeholder section — activate when you have real testimonials:

```
"I made back my Pro subscription in the first sale of the month."
— DJ [Name], [City]

"The custom domain alone was worth it. My fans think I have my own platform."
— DJ [Name], [City]
```

- Simple quote cards, no star ratings (too generic)
- DJ avatar + name + city
- Leave this section OUT until you have 3+ real quotes — empty social proof is worse than none

---

#### FAQ Section

```
Q: Can I cancel anytime?
A: Yes. Cancel before your trial ends and you won't be charged.
   After that, cancel anytime — you keep Pro until the end of your billing period.

Q: What happens if I cancel?
A: You move to Standard plan. Your 7-day grace period keeps Pro features active
   while you decide. After 7 days, storage over 3GB becomes read-only
   (existing files stay, new uploads blocked until under 3GB).

Q: Does the custom domain cost extra?
A: No. Your domain purchase is separate (from any registrar), 
   but connecting it to MixMint is included in Pro at no extra charge.

Q: Do buyers see fewer ads because I'm on Pro?
A: No — buyers still see the same ads. Ads are removed from YOUR view
   of your own storefront when logged in as a Pro DJ.

Q: Will my commission rate ever change?
A: Commission rates are set by MixMint and may be adjusted with 30 days notice.
   Pro DJs always get a lower rate than Standard DJs.

Q: What's priority search placement?
A: Pro DJ tracks appear higher in search results and genre filters compared
   to identical Standard DJ tracks. It's not guaranteed #1 — quality and
   recency still matter.
```

---

## 🔄 7-DAY FREE TRIAL FLOW

### Trial Start (No Card Required)

1. DJ clicks `Start Free Trial`
2. If not logged in: auth modal → login/register → continues
3. If already a DJ: trial activates immediately
4. If still a buyer: shown DJ application prompt first

**Trial activation screen:**
```
┌──────────────────────────────────────────────────────┐
│  ⚡ Your Pro Trial is Active                         │
│                                                      │
│  You have 7 days to explore everything Pro offers.  │
│                                                      │
│  Trial ends:  [Date] at [Time]                      │
│  After trial: ₹299/month or ₹2,499/year             │
│                                                      │
│  Add payment method to continue after trial:        │
│  [Add Card / UPI]    [Remind Me Later]               │
│                                                      │
│  You will NOT be charged until your trial ends.     │
│  Cancel anytime before [Date] to pay nothing.       │
└──────────────────────────────────────────────────────┘
```

- Payment method optional during trial — required before day 7 to continue
- Day 5: email reminder — *"2 days left on your Pro trial"*
- Day 7: email reminder — *"Your trial ends today"*
- If no payment added by day 7: downgrade to Standard (no charge, no drama)

---

### Trial Status in DJ Dashboard

In DJ sidebar, below DJ name:
```
⚡ PRO TRIAL
5 days remaining
[Add Payment to Continue]
```
- Amber pill, countdown in DM Mono
- Turns red at 2 days remaining
- Links directly to billing page

---

## ⏬ SUBSCRIPTION LAPSE — 7-DAY GRACE

When Pro subscription fails to renew (payment failure or cancellation):

**Day 0 (lapse):**
- Email sent: *"Your Pro subscription has ended. You have 7 days to renew before reverting to Standard."*
- DJ dashboard shows amber banner: *"Pro subscription lapsed — renew within 7 days to keep all features"*
- All Pro features still fully active

**Days 1–7 (grace):**
- Daily reminder email after day 5
- Dashboard banner turns red at day 6

**Day 7 (downgrade):**
- Commission reverts to Standard rate immediately
- Custom domain: disconnected, storefront falls back to mixmint.site/dj/[username]
- Search priority: removed
- PRO badge: removed
- Storage over 3GB: read-only (existing files stay accessible for buyers who already purchased — critical — don't break existing download links)
- Payout threshold: reverts to ₹500
- Upload blocked until storage under 3GB or Pro renewed

**Storage grace note in dashboard (if over 3GB after downgrade):**
```
⚠️ Storage limit exceeded
You are using 8.2 GB. Standard plan allows 3 GB.
New uploads are paused until you free space or renew Pro.
Existing tracks and buyer downloads are unaffected.
[Renew Pro]  [Manage Storage]
```

---

## ⚙️ ADMIN — PRO PLAN CONTROLS

Add to Admin → Offers & Pricing:

```
┌──────────────────────────────────────────────────────────────┐
│  PRO PLAN SETTINGS                                           │
│                                                              │
│  Pro Commission Rate:     [ 7  ]%                           │
│  (Standard rate: 10% — Pro must always be lower)            │
│                                                              │
│  Pro Monthly Price:       ₹[ 299  ]                         │
│  Pro Annual Price:        ₹[ 2499 ]                         │
│                                                              │
│  Trial Duration:          [ 7 ] days                        │
│  Grace Period:            [ 7 ] days                        │
│                                                              │
│  Pro Storage Quota:       [ 20 ] GB                         │
│  Pro Collaborator Limit:  [ 5  ]                            │
│  Pro Payout Threshold:    ₹[ 250 ]                          │
│                                                              │
│  [  ON  ●─────────  ]  Pro Plan currently: ACTIVE          │
│  Disable to stop new signups (existing subscribers unaffected)│
│                                                              │
│  [Save Changes]                                             │
└──────────────────────────────────────────────────────────────┘
```

**Pro Subscribers Table (Admin view):**
```
DJ Name    Plan      Started     Next Billing   Status      Revenue/mo   Action
─────────────────────────────────────────────────────────────────────────────
DJ Rohit   Annual    01/01/26    01/01/27       Active       ₹28,400     View
DJ Priya   Monthly   15/02/26    15/03/26       Trial (3d)   ₹4,200      View
DJ Arjun   Monthly   01/03/26    01/04/26       Grace (5d)   ₹11,000     Renew
```

- Revenue/mo column helps admin see which Pro DJs are profitable
- Admin can manually extend trial or grace period per DJ
- Admin can gift Pro to specific DJs (e.g. first batch of launch DJs)

---

## 🧮 DB SCHEMA ADDITIONS

```sql
-- Add to profiles table
ALTER TABLE profiles ADD COLUMN is_pro_dj BOOLEAN DEFAULT FALSE;
ALTER TABLE profiles ADD COLUMN pro_plan_type VARCHAR(10);  -- 'monthly' | 'annual' | null
ALTER TABLE profiles ADD COLUMN pro_started_at TIMESTAMPTZ;
ALTER TABLE profiles ADD COLUMN pro_expires_at TIMESTAMPTZ;
ALTER TABLE profiles ADD COLUMN pro_trial_ends_at TIMESTAMPTZ;
ALTER TABLE profiles ADD COLUMN pro_grace_ends_at TIMESTAMPTZ;
ALTER TABLE profiles ADD COLUMN pro_payment_ref VARCHAR(255);  -- gateway subscription ID
ALTER TABLE profiles ADD COLUMN storage_quota_mb INTEGER DEFAULT 3072;  -- 3GB standard
-- Pro gets updated to 20480 (20GB) on subscription

-- Pro subscription events log
CREATE TABLE pro_subscription_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  dj_id UUID REFERENCES profiles(id),
  event_type VARCHAR(50),  -- 'trial_start' | 'subscribed' | 'renewed' | 'lapsed' | 'grace_start' | 'downgraded' | 'cancelled'
  plan_type VARCHAR(10),
  amount_paid INTEGER,  -- in paise
  gateway_ref VARCHAR(255),
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 📧 PRO EMAIL SEQUENCE

| Trigger | Subject | Content |
|---------|---------|---------|
| Trial starts | *"Your 7-day Pro trial has started ⚡"* | Features overview, trial end date, how to add payment |
| Trial day 5 | *"2 days left on your MixMint Pro trial"* | What you'll lose, CTA to add payment |
| Trial day 7 | *"Your Pro trial ends today"* | Urgent, direct CTA |
| Trial ends (no payment) | *"Your Pro trial has ended"* | What changed, invite to subscribe later |
| Subscription confirmed | *"You're now on Pro ⚡"* | Confirmation, next billing date, all features |
| 3 days before renewal | *"Pro renewal coming up"* | Amount, date, cancel link |
| Payment fails | *"Action needed — Pro renewal failed"* | Update payment, grace period explained |
| Grace day 5 | *"2 days to renew Pro before downgrade"* | Urgent, what will change |
| Downgraded | *"Your account has moved to Standard"* | What changed, storage warning if over 3GB |
| Annual renewal | *"Pro Annual renewed — thanks ⚡"* | Receipt, next renewal date |

---

## 🚀 UPGRADE PROMPT — WHEN AND WHERE TO SHOW IT

### Smart Trigger Rules (Admin-controlled threshold)

Show the Pro upgrade prompt **only when:**
- DJ has been active for 14+ days AND
- Monthly earnings exceed ₹5,000 OR
- Storage usage exceeds 70% of 3GB OR
- DJ has uploaded 10+ tracks

**Never show to:**
- DJs in their first 7 days
- DJs with 0 sales
- DJs already on Pro

### Upgrade Prompt Locations

**DJ Dashboard — Earnings Page (contextual):**
```
┌──────────────────────────────────────────────────────┐
│  ⚡ You earned ₹12,400 this month                    │
│                                                      │
│  On Pro (7% commission), you would have kept         │
│  ₹372 more this month.                               │
│  That's ₹4,464 extra per year.                      │
│                                                      │
│  Pro costs ₹2,499/year.                             │
│  At your sales volume, it pays for itself            │
│  in 7 months and saves money after that.            │
│                                                      │
│  [Start 7-Day Free Trial →]                         │
└──────────────────────────────────────────────────────┘
```

- Shows real numbers from their actual earnings — not generic
- Makes the ROI case with their own data
- Only shown when savings > subscription cost

**DJ Dashboard — Storage Page (contextual):**
```
┌──────────────────────────────────────────────────────┐
│  Storage: 2.4 GB / 3 GB used  (80%)  ⚠️             │
│                                                      │
│  You're running low on storage.                      │
│  Pro gives you 20 GB — that's 6× more room          │
│  for ₹299/month.                                    │
│                                                      │
│  [Upgrade to Pro →]  [Manage Storage]               │
└──────────────────────────────────────────────────────┘
```

**DJ Sidebar — Persistent (subtle):**
```
─────────────────────
  Upgrade to Pro ⚡
  Lower commission +
  20GB storage
─────────────────────
```
- Always visible in sidebar for non-Pro DJs
- Small, not aggressive — just always there

---

## 🔒 WHAT STANDARD DJs NEVER LOSE

Make this clear on the Pro page and in all downgrade communications — Standard is not a punishment:

- All uploaded tracks remain live
- All buyer downloads continue working
- All earnings history preserved
- All payout history preserved
- All existing purchases by buyers unaffected
- Storefront remains live at mixmint.site/dj/[username]

Standard is a legitimate plan. Pro is an upgrade for DJs who are scaling. Frame it that way.

---

*End of MixMint Pro Plan Prompt*
*3GB free · Admin-controlled commission · 7-day trial · 7-day grace · Monthly + Annual billing*
*Profitable above ₹10,000/month DJ revenue · Always more profitable than Standard at scale*

---

# 🗄️ MIXMINT — STORAGE OVERAGE SYSTEM PROMPT
### *Addendum to Pro Plan Prompt — Pay-as-you-go after 20GB*

---

## 📐 STORAGE TIER OVERVIEW (COMPLETE PICTURE)

```
Plan          Included Storage    Beyond Limit
────────────────────────────────────────────────────────
Standard      3 GB                Uploads blocked
Pro           20 GB               Pay-as-you-go (auto)
Pro + Overage 20 GB + X GB        ₹per GB/month (auto-billed)
```

Standard DJs hitting 3GB get blocked — upgrade prompt shown.
Pro DJs hitting 20GB get auto-charged overage — no interruption.

---

## 💰 OVERAGE PRICING MODEL

### Admin-Controlled Rate (set in Admin → Offers & Pricing)

```
Suggested launch rate:   ₹30 per GB per month
Minimum billing unit:    0.1 GB (100MB) — never charge for less
Billing cycle:           Added to next monthly/annual renewal
Rounding:                Always round UP to next 0.1 GB
```

### Why ₹30/GB Works

```
Your R2 cost:        ~₹1.25/GB/month
Your charge:         ₹30/GB/month
Your margin:         ~24× — healthy
Competitor context:  AWS S3 charges ~₹7/GB — you're premium
                     but DJs aren't comparing you to S3
DJ context:          A DJ earning ₹20,000/month won't notice
                     ₹300 for 10GB extra — it's noise
```

---

## ⚙️ HOW AUTO-CHARGE WORKS (TECHNICAL FLOW)

### Trigger Point
Every time a DJ successfully uploads a file, after R2 confirms storage:

```python
def update_storage_and_check_overage(dj_id, file_size_mb):
    profile = Profile.objects.select_for_update().get(id=dj_id)

    profile.storage_used_mb += file_size_mb
    profile.save()

    # Only applies to Pro DJs
    if not profile.is_pro_dj:
        return  # Standard handled separately (blocked at limit)

    overage_mb = max(0, profile.storage_used_mb - PRO_STORAGE_LIMIT_MB)

    if overage_mb > 0:
        # Round up to nearest 100MB
        overage_gb = math.ceil(overage_mb / 100) * 0.1

        # Store overage for next billing cycle
        StorageOverage.objects.update_or_create(
            dj_id=dj_id,
            billing_period=current_billing_period(),
            defaults={
                'overage_gb': overage_gb,
                'rate_per_gb': settings.STORAGE_OVERAGE_RATE,
                'amount_due': overage_gb * settings.STORAGE_OVERAGE_RATE
            }
        )

        # Notify DJ on first overage of the month
        if not has_been_notified_this_period(dj_id):
            send_overage_notification(dj_id, overage_gb)
```

### Billing Timing

```
Monthly Pro DJs:
  Overage calculated on billing date
  Added to that month's renewal charge
  Single combined charge: ₹299 + overage

Annual Pro DJs:
  Overage billed monthly (separate from annual fee)
  Charged on the same date each month as their annual start date
  Example: Annual started Jan 1 → overage billed 1st of each month
```

---

## 🗃️ DB SCHEMA

```sql
-- Storage overage tracking
CREATE TABLE storage_overage (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  dj_id UUID REFERENCES profiles(id),
  billing_period DATE,           -- first day of billing period
  overage_gb DECIMAL(10, 2),     -- GB over limit
  rate_per_gb INTEGER,           -- rate in paise at time of billing
  amount_due INTEGER,            -- total in paise
  status VARCHAR(20)             -- 'pending' | 'charged' | 'waived'
      DEFAULT 'pending',
  gateway_charge_id VARCHAR(255),-- payment ref if charged
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),

  UNIQUE(dj_id, billing_period)  -- one record per DJ per period
);

-- Add to profiles
ALTER TABLE profiles
  ADD COLUMN overage_enabled BOOLEAN DEFAULT TRUE,
  -- Admin can disable overage for specific DJs (e.g. gifted storage)
  ADD COLUMN custom_storage_quota_mb INTEGER DEFAULT NULL;
  -- If set, overrides plan default. NULL = use plan default.
  -- Lets admin give a specific DJ more storage without full plan change
```

---

## 📊 ADMIN — OVERAGE CONTROLS

Add to **Admin → Offers & Pricing → Storage** section:

```
┌──────────────────────────────────────────────────────────────┐
│  STORAGE OVERAGE PRICING                                     │
│                                                              │
│  Overage rate:    ₹[ 30 ] per GB per month                  │
│  Minimum unit:    [ 0.1 ] GB (100MB)                        │
│                                                              │
│  [  ON  ●─────────  ]  Auto-charge overage: ENABLED        │
│  Disable to block uploads at limit instead of auto-charging │
│                                                              │
│  [Save]                                                     │
└──────────────────────────────────────────────────────────────┘
```

**Per-DJ Override (in DJ detail page):**
```
┌──────────────────────────────────────────────────────────────┐
│  Storage Settings — DJ Rohit                                 │
│                                                              │
│  Current usage:    22.4 GB                                   │
│  Plan quota:       20 GB (Pro)                               │
│  Overage:          2.4 GB → ₹72 this period                 │
│                                                              │
│  Custom quota:     [ ______ ] MB  (blank = use plan default) │
│  Overage enabled:  [  ON  ●───  ]                           │
│                                                              │
│  [Waive This Period's Overage]   [Save]                     │
└──────────────────────────────────────────────────────────────┘
```

- Admin can waive overage for a specific period (e.g. for a top DJ as goodwill)
- Admin can set custom quota for a specific DJ without changing their plan
- Admin can disable overage per DJ (uploads blocked at limit for that DJ instead)

**Overage Revenue Table (Admin → Revenue Intelligence):**
```
Period       Overage DJs    Total GB Over    Revenue
──────────────────────────────────────────────────────
Mar 2026     4 DJs          18.2 GB          ₹546
Feb 2026     2 DJs          6.7 GB           ₹201
Jan 2026     1 DJ           2.1 GB           ₹63
```

---

## 🎛️ DJ DASHBOARD — STORAGE METER (UPDATED)

### Standard DJ (approaching 3GB limit):
```
┌──────────────────────────────────────────────────────┐
│  Storage                                             │
│  ████████████████████░░░░  2.4 GB / 3 GB  (80%) ⚠️ │
│                                                      │
│  Running low. Upgrade to Pro for 20 GB.             │
│  [Upgrade to Pro →]                                  │
└──────────────────────────────────────────────────────┘
```

### Pro DJ (under 20GB — healthy):
```
┌──────────────────────────────────────────────────────┐
│  Storage                                             │
│  ████████░░░░░░░░░░░░░░░░  8.2 GB / 20 GB  (41%)   │
│  11.8 GB remaining                                   │
└──────────────────────────────────────────────────────┘
```

### Pro DJ (hit 20GB — overage active):
```
┌──────────────────────────────────────────────────────┐
│  Storage                                             │
│  ████████████████████████  20 GB / 20 GB            │
│  + 2.4 GB overage  →  ₹72 added to next bill  ℹ️   │
│                                                      │
│  Overage rate: ₹30/GB/month                         │
│  [Manage Storage]  [View Billing]                   │
└──────────────────────────────────────────────────────┘
```

- Progress bar: fills mint to 20GB, then continues in amber for overage
- Two-tone bar: mint (included) + amber (overage)
- ₹ amount updates live as they upload more
- ℹ️ tooltip: *"Overage is billed on your next renewal date"*

### Pro DJ (heavy overage — needs attention):
```
┌──────────────────────────────────────────────────────┐
│  Storage                                             │
│  ████████████████████████████████  20 GB + 12.6 GB  │
│  Overage: 12.6 GB  →  ₹378 added to next bill  ⚠️  │
│                                                      │
│  Consider deleting old tracks to reduce overage.    │
│  [Manage Storage]                                    │
└──────────────────────────────────────────────────────┘
```

- At 10GB+ overage: amber warning strip, suggests cleanup
- At 30GB+ overage: red warning, stronger message

---

## 📧 OVERAGE EMAIL NOTIFICATIONS

| Trigger | Subject | Key Content |
|---------|---------|-------------|
| First overage hit | *"You've exceeded 20GB — here's what happens"* | Explain auto-charge, rate, next bill date, how to manage |
| Every 5GB over | *"Storage update — X GB in overage"* | Current overage, projected cost, manage storage link |
| 3 days before billing | *"Your bill includes ₹X storage overage"* | Breakdown: Pro fee + overage amount + total |
| Overage charged | *"Storage overage charged — ₹X"* | Receipt, current storage, cleanup tips |
| Payment fails on overage | *"Action needed — overage charge failed"* | Update payment, uploads paused until resolved |

---

## 🚦 WHAT HAPPENS WHEN OVERAGE PAYMENT FAILS

If the combined Pro renewal + overage charge fails:

```
Day 0:  Charge fails → email sent → grace period starts
Day 1–3: Uploads paused (existing content untouched)
         Dashboard banner: "Payment failed — uploads paused"
         [Update Payment Method]
Day 4:  Retry charge automatically
Day 7:  If still unpaid → Pro grace period starts (7 days)
        → standard Pro lapse flow kicks in after that
```

Existing tracks stay live and buyer downloads continue working throughout — never punish buyers for a DJ's payment issue.

---

## 💡 UX COPY REFERENCE

**Storage meter tooltip (overage active):**
> *"You're using X GB beyond your 20 GB Pro limit. Overage is billed at ₹30/GB/month and added to your next renewal."*

**First overage notification (in-app toast):**
> *"You've passed 20 GB. Uploads continue automatically — overage is ₹30/GB/month, added to your next bill."*

**Billing page overage line:**
```
Pro Plan (Monthly)          ₹299.00
Storage Overage (2.4 GB)     ₹72.00
─────────────────────────────────────
Total                        ₹371.00
```

**Manage Storage page tip:**
> *"Deleting a track removes it from your storage count immediately. Buyers who already purchased the track can still download it — their access is unaffected."*

---

## 📐 PROFITABILITY OF OVERAGE

```
R2 cost to you:     ₹1.25/GB/month
You charge DJ:      ₹30/GB/month
Your margin:        ₹28.75/GB — 96% margin on overage

A DJ using 10GB overage:
  Costs you:   ₹12.50/month
  Earns you:   ₹300/month
  Profit:      ₹287.50/month extra on top of subscription
```

Overage is your highest-margin revenue line. A handful of storage-heavy DJs can meaningfully contribute to platform revenue with zero extra infra work on your end — R2 scales automatically.

---

*End of Storage Overage Addendum*
*Auto-charge · Admin-controlled rate · Two-tone storage meter · Never blocks existing buyer downloads*

---


# ═══════════════════════════════════════════════════
# SECTION C — PLATFORM FIXES 01–10
# ═══════════════════════════════════════════════════
# 🛠️ MIXMINT — ALL FIXES PROMPT (COMPLETE)
### *17 systems. Every gap closed. Build-ready specifications.*

---

# FIX 01 — REFUND POLICY ENGINE

## Overview
Refunds are only valid when a download is verifiably incomplete. The system must be automated enough to handle simple cases without admin involvement, but always give admin override control.

---

## Refund Eligibility Rules

```
ELIGIBLE for refund:
  ✓ Download byte count < 100% verified
  ✓ Checksum verification failed
  ✓ Token expired before download could begin (within 10 min of purchase)
  ✓ File served was corrupt (admin confirms)

NOT ELIGIBLE:
  ✗ Download marked complete (100% bytes + checksum passed)
  ✗ Re-download request (separate flow)
  ✗ "Changed mind" after successful download
  ✗ File format not as expected (DJ's responsibility)
  ✗ Request made more than 7 days after purchase
```

---

## Buyer-Facing Refund Request Flow

### Entry Point 1 — Download Page (automatic)
When download fails checksum or byte verification:
```
┌──────────────────────────────────────────────────────┐
│  ✗  Download Incomplete                              │
│                                                      │
│  Your file did not complete successfully.            │
│  You are eligible for a full refund or a retry.     │
│                                                      │
│  [Request Refund]      [Retry Download]             │
│                                                      │
│  Refunds are processed within 3–5 business days.   │
└──────────────────────────────────────────────────────┘
```

### Entry Point 2 — Library Page
- Each incomplete purchase shows `Request Refund` link
- Available for 7 days from purchase date
- After 7 days: link disappears, refund window closed

### Refund Request Form
```
┌──────────────────────────────────────────────────────┐
│  Refund Request                                      │
│                                                      │
│  Track: [Track Name]                                 │
│  Purchased: [Date]  ·  Amount: ₹49                  │
│                                                      │
│  Reason: (auto-selected based on failure type)      │
│  ● Download did not complete                        │
│  ○ File was corrupt                                 │
│  ○ Other (describe below)                           │
│                                                      │
│  Additional details: [optional textarea]            │
│                                                      │
│  [Submit Refund Request]                            │
│                                                      │
│  Your refund will be reviewed within 24 hours.      │
│  If approved, it reaches your account in 3–5 days. │
└──────────────────────────────────────────────────────┘
```

---

## Auto-Approval Logic

```python
def evaluate_refund_request(refund_request_id):
    request = RefundRequest.objects.get(id=refund_request_id)
    purchase = request.purchase
    download_log = DownloadLog.objects.filter(
        user_id=purchase.user_id,
        content_id=purchase.content_id
    ).order_by('-created_at').first()

    # Auto-approve conditions
    if (
        not download_log.completed and
        not download_log.checksum_verified and
        download_log.byte_percentage < 100 and
        (timezone.now() - purchase.created_at).days <= 7
    ):
        approve_refund(request)  # auto-approve, no admin needed
        return

    # Auto-reject conditions
    if download_log.completed and download_log.checksum_verified:
        reject_refund(request, reason="Download completed successfully")
        return

    # Edge case — send to admin queue
    escalate_to_admin(request)
```

---

## Admin Refund Queue (Admin Dashboard → New Section: Refunds)

```
┌──────────────────────────────────────────────────────────────┐
│  REFUND REQUESTS                                             │
│                                                              │
│  Auto-approved this week:  12   Auto-rejected: 3            │
│  Pending admin review:      2                               │
│                                                              │
│  Filter: [All] [Pending] [Approved] [Rejected] [Escalated]  │
│                                                              │
│  Buyer    Track        Amount  Status     Download Log  Act  │
│  ───────────────────────────────────────────────────────    │
│  Ravi     DJ Mix 01    ₹49     Pending    67% / FAIL   [▼]  │
│  Priya    Bass Pack    ₹149    Escalated  99% / FAIL   [▼]  │
│                                                              │
│  Expand row shows:                                          │
│  · Full download log (bytes, speed, timestamp)             │
│  · IP + device hash                                         │
│  · Checksum result                                          │
│  · [Approve Refund]  [Reject with Reason]  [Mark Fraud]    │
└──────────────────────────────────────────────────────────────┘
```

---

## DJ Earnings Clawback on Refund

```python
def approve_refund(refund_request):
    purchase = refund_request.purchase

    with transaction.atomic():
        # 1. Initiate gateway refund
        gateway = get_active_gateway()
        gateway.process_refund(
            payment_id=purchase.gateway_payment_id,
            amount=purchase.original_price
        )

        # 2. Clawback DJ earnings
        DJWallet.objects.filter(dj_id=purchase.dj_id).update(
            pending_earnings=F('pending_earnings') - purchase.dj_revenue,
            total_earnings=F('total_earnings') - purchase.dj_revenue
        )

        # 3. If collab track — clawback all collaborators
        collabs = TrackCollaborator.objects.filter(
            track_id=purchase.content_id
        )
        for collab in collabs:
            collab_share = purchase.dj_revenue * (collab.revenue_percentage / 100)
            DJWallet.objects.filter(dj_id=collab.dj_id).update(
                pending_earnings=F('pending_earnings') - collab_share
            )

        # 4. Mark purchase refunded
        purchase.status = 'refunded'
        purchase.refunded_at = timezone.now()
        purchase.save()

        # 5. Notify buyer + DJ
        send_refund_approved_email(refund_request)
        send_dj_earnings_clawback_email(purchase.dj_id, purchase)
```

---

## DB Schema

```sql
CREATE TABLE refund_requests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  purchase_id UUID REFERENCES purchases(id),
  user_id UUID REFERENCES profiles(id),
  reason VARCHAR(100),
  description TEXT,
  status VARCHAR(20) DEFAULT 'pending',
    -- 'pending' | 'auto_approved' | 'approved' | 'rejected' | 'escalated'
  reviewed_by UUID REFERENCES profiles(id),  -- admin who acted
  rejection_reason TEXT,
  gateway_refund_id VARCHAR(255),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  resolved_at TIMESTAMPTZ
);

-- Add to purchases table
ALTER TABLE purchases
  ADD COLUMN status VARCHAR(20) DEFAULT 'active',
    -- 'active' | 'refunded' | 'disputed'
  ADD COLUMN refunded_at TIMESTAMPTZ;
```

---

## Email Notifications

| Trigger | To | Content |
|---------|-----|---------|
| Request submitted | Buyer | Confirmation, 24h review timeline |
| Auto-approved | Buyer | Approved, 3–5 days to account |
| Auto-rejected | Buyer | Rejected (download logs show complete), dispute option |
| Admin approved | Buyer + DJ | Buyer: refund coming. DJ: earnings clawed back + reason |
| Admin rejected | Buyer | Rejection reason, contact support link |

---
---

# FIX 02 — CUSTOM DOMAIN FOR PRO DJs

## Overview
Pro DJs get a custom domain for their storefront (e.g. `music.djrohit.com` instead of `mixmint.site/dj/rohit`). MixMint handles routing and SSL. The DJ only sets a DNS record.

---

## DJ Setup Flow (Dashboard → Store Settings → Custom Domain)

```
┌──────────────────────────────────────────────────────────────┐
│  Custom Domain  ⚡ PRO FEATURE                               │
│                                                              │
│  Your current storefront:                                    │
│  mixmint.site/dj/rohit                                      │
│                                                              │
│  Connect your own domain:                                    │
│  [ music.djrohit.com              ]  [Connect]              │
│                                                              │
│  After connecting, add this DNS record at your registrar:   │
│                                                              │
│  Type    Name    Value                                       │
│  CNAME   @       proxy.mixmint.site                        │
│                                                              │
│  [Copy DNS Record]                                          │
│                                                              │
│  ⏳ Waiting for DNS propagation...                          │
│  DNS can take up to 48 hours to propagate globally.        │
└──────────────────────────────────────────────────────────────┘
```

### After DNS Verified:
```
┌──────────────────────────────────────────────────────────────┐
│  Custom Domain  ✓ Active                                     │
│                                                              │
│  ✓  music.djrohit.com  →  Your MixMint Storefront           │
│  ✓  SSL Certificate:   Active (auto-renewed)                │
│                                                              │
│  [Remove Domain]                                            │
│                                                              │
│  Note: Removing your domain reverts to                      │
│  mixmint.site/dj/rohit immediately.                        │
└──────────────────────────────────────────────────────────────┘
```

---

## Technical Implementation (Vercel)

```python
# When DJ submits domain:

import requests

VERCEL_TOKEN = settings.VERCEL_TOKEN
VERCEL_PROJECT_ID = settings.VERCEL_PROJECT_ID

def add_custom_domain(dj_id, domain):
    # 1. Validate domain format
    if not is_valid_domain(domain):
        raise ValueError("Invalid domain format")

    # 2. Check domain not already used by another DJ
    if DJProfile.objects.filter(custom_domain=domain).exists():
        raise ValueError("Domain already in use")

    # 3. Add to Vercel project via API
    response = requests.post(
        f"https://api.vercel.com/v10/projects/{VERCEL_PROJECT_ID}/domains",
        headers={"Authorization": f"Bearer {VERCEL_TOKEN}"},
        json={"name": domain}
    )

    if response.status_code not in [200, 409]:
        raise Exception("Failed to add domain to Vercel")

    # 4. Save to DB with status 'pending_verification'
    DJProfile.objects.filter(id=dj_id).update(
        custom_domain=domain,
        custom_domain_status='pending_verification',
        custom_domain_added_at=timezone.now()
    )

    # 5. Start polling for DNS verification
    schedule_domain_verification(dj_id, domain)


def verify_domain_status(dj_id, domain):
    # Poll Vercel for domain verification status
    response = requests.get(
        f"https://api.vercel.com/v9/projects/{VERCEL_PROJECT_ID}/domains/{domain}",
        headers={"Authorization": f"Bearer {VERCEL_TOKEN}"}
    )
    data = response.json()

    if data.get('verified'):
        DJProfile.objects.filter(id=dj_id).update(
            custom_domain_status='active',
            custom_domain_verified_at=timezone.now()
        )
        send_domain_verified_email(dj_id, domain)
    else:
        # Retry in 30 minutes for up to 48 hours
        schedule_domain_verification(dj_id, domain, delay_minutes=30)
```

### Django URL Routing for Custom Domains

```python
# middleware/custom_domain.py
class CustomDomainMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().lower().split(':')[0]

        # Skip for main domain and subdomains
        if host in ['mixmint.site', 'www.mixmint.site']:
            return self.get_response(request)

        # Look up DJ by custom domain
        try:
            dj = DJProfile.objects.get(
                custom_domain=host,
                custom_domain_status='active'
            )
            # Rewrite request to DJ storefront
            request.custom_domain_dj = dj
            request.urlconf = 'mixmint.urls.storefront'
        except DJProfile.DoesNotExist:
            return HttpResponse("Domain not configured", status=404)

        return self.get_response(request)
```

---

## Domain States & What DJ Sees

```
State                  DJ Dashboard Shows
─────────────────────────────────────────────────────
Not set                Setup prompt + instructions
pending_verification   DNS record to add + "checking..." spinner
active                 Green ✓, domain shown, remove option
failed_verification    Error message, instructions to recheck DNS
expired_ssl            Warning, auto-renewal attempted
pro_lapsed             Domain disconnected, setup prompt returns
```

---

## SSL Certificates
Vercel handles SSL automatically for all custom domains added to the project. No action needed from MixMint or the DJ. Certificate auto-renews before expiry.

---

## DB Schema

```sql
ALTER TABLE profiles
  ADD COLUMN custom_domain VARCHAR(255) UNIQUE,
  ADD COLUMN custom_domain_status VARCHAR(30) DEFAULT NULL,
    -- NULL | 'pending_verification' | 'active' | 'failed' | 'disconnected'
  ADD COLUMN custom_domain_added_at TIMESTAMPTZ,
  ADD COLUMN custom_domain_verified_at TIMESTAMPTZ;
```

---
---

# FIX 03 — METADATA INJECTION PIPELINE

## Overview
Every file sold through MixMint must have platform metadata injected before being made available for download. This is the anti-piracy watermark. It must be verified before the file is accessible.

---

## What Gets Injected

```
Field               Value
───────────────────────────────────────────────────────
Platform            MixMint
Platform URL        mixmint.site
DJ ID               [UUID]
DJ Name             [Display name]
Track/Album ID      [UUID]
Upload Timestamp    [ISO 8601]
Anti-resale clause  "Licensed for personal use only.
                     Redistribution or resale prohibited.
                     MixMint.site"
```

---

## MP3/Audio File Injection (ID3 Tags)

```python
from mutagen.id3 import ID3, TIT2, TPE1, TCOM, TCOP, COMM, TXXX
from mutagen.mp3 import MP3
import hashlib

def inject_metadata_mp3(file_path, dj_id, dj_name,
                         track_id, track_title):
    try:
        audio = ID3(file_path)
    except:
        audio = ID3()

    # Preserve existing tags (title, artist) — don't overwrite DJ's own tags
    # Only add/overwrite MixMint-specific fields

    audio['TCOP'] = TCOP(encoding=3, text=[
        f"Licensed for personal use only. "
        f"Redistribution or resale prohibited. mixmint.site"
    ])
    audio['COMM'] = COMM(
        encoding=3, lang='eng', desc='MixMint',
        text=[
            f"Platform: MixMint | "
            f"DJ: {dj_name} | "
            f"ID: {track_id} | "
            f"DJ_ID: {dj_id} | "
            f"mixmint.site"
        ]
    )
    audio['TXXX:MIXMINT_ID'] = TXXX(
        encoding=3, desc='MIXMINT_ID',
        text=[str(track_id)]
    )
    audio['TXXX:MIXMINT_DJ'] = TXXX(
        encoding=3, desc='MIXMINT_DJ',
        text=[str(dj_id)]
    )
    audio['TXXX:MIXMINT_TS'] = TXXX(
        encoding=3, desc='MIXMINT_TS',
        text=[timezone.now().isoformat()]
    )

    audio.save(file_path)

    # Verify injection succeeded
    verify = ID3(file_path)
    assert 'TXXX:MIXMINT_ID' in verify, "Metadata injection failed"
    assert verify['TXXX:MIXMINT_ID'].text[0] == str(track_id)

    return True
```

---

## ZIP Album Processing

```python
import zipfile
import os
import shutil
import tempfile

def process_album_zip(zip_path, dj_id, dj_name, album_id):
    """
    Unzip → inject metadata into each audio file → re-zip
    All processing in temp directory — original never modified until success
    """
    SUPPORTED_AUDIO = ['.mp3', '.wav', '.aiff', '.flac', '.m4a']

    with tempfile.TemporaryDirectory() as tmpdir:
        extract_dir = os.path.join(tmpdir, 'extracted')
        output_zip = os.path.join(tmpdir, 'processed.zip')

        # 1. Safe unzip (ZIP bomb protected — see security fix)
        safe_unzip(zip_path, extract_dir)

        # 2. Walk all files, inject metadata into audio files
        injection_results = []
        for root, dirs, files in os.walk(extract_dir):
            for filename in files:
                filepath = os.path.join(root, filename)
                ext = os.path.splitext(filename)[1].lower()

                if ext in SUPPORTED_AUDIO:
                    try:
                        if ext == '.mp3':
                            inject_metadata_mp3(
                                filepath, dj_id, dj_name,
                                album_id, filename
                            )
                        elif ext == '.wav':
                            inject_metadata_wav(filepath, dj_id, album_id)
                        # ... other formats

                        injection_results.append({
                            'file': filename,
                            'status': 'success'
                        })
                    except Exception as e:
                        injection_results.append({
                            'file': filename,
                            'status': 'failed',
                            'error': str(e)
                        })

        # 3. Verify all injections succeeded
        failed = [r for r in injection_results if r['status'] == 'failed']
        if failed:
            raise Exception(
                f"Metadata injection failed for: "
                f"{[f['file'] for f in failed]}"
            )

        # 4. Re-zip processed files
        with zipfile.ZipFile(output_zip, 'w',
                             zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    filepath = os.path.join(root, file)
                    arcname = os.path.relpath(filepath, extract_dir)
                    zf.write(filepath, arcname)

        # 5. Upload processed ZIP to R2
        # (replaces original)
        upload_to_r2(output_zip, get_r2_path(album_id))

    return injection_results
```

---

## When Injection Runs

```
Track upload:
  1. DJ uploads file
  2. File stored in R2 as 'pending' prefix
  3. Metadata injection job queued (async via Celery/background task)
  4. On success: file moved to 'active' prefix, track marked available
  5. On failure: admin alerted, track stays in 'pending'

Album upload:
  Same flow but ZIP processing is heavier — always async
  DJ sees: "Processing your album... This may take a few minutes."
```

---

## Track Status Field

```sql
ALTER TABLE tracks
  ADD COLUMN file_status VARCHAR(20) DEFAULT 'processing',
    -- 'processing' | 'ready' | 'injection_failed'
  ADD COLUMN injection_verified_at TIMESTAMPTZ,
  ADD COLUMN original_checksum VARCHAR(64),   -- SHA-256 before injection
  ADD COLUMN processed_checksum VARCHAR(64);  -- SHA-256 after injection
```

---
---

# FIX 04 — SEARCH RANKING ALGORITHM

## Overview
Search results must be fair, transparent to admin, and resistant to manipulation. Pro DJ boost must be meaningful but not so dominant that it buries great Standard DJ content.

---

## Ranking Formula

```python
def calculate_search_score(track, query, is_pro_dj, is_verified_dj):
    score = 0.0

    # 1. Text relevance (0–40 points)
    title_match = fuzzy_match(query, track.title)      # 0–25
    dj_match = fuzzy_match(query, track.dj_name)       # 0–10
    genre_match = exact_match(query, track.genre)      # 5 bonus
    score += title_match + dj_match + genre_match

    # 2. Recency (0–20 points)
    days_old = (now() - track.created_at).days
    recency_score = max(0, 20 - (days_old / 7))
    # New track: 20 pts. 10 weeks old: ~5 pts. 20+ weeks: 0 pts.
    score += recency_score

    # 3. Sales velocity (0–20 points)
    # Sales in last 30 days — not lifetime (prevents old tracks dominating)
    recent_sales = track.sales_last_30_days
    sales_score = min(20, recent_sales * 2)
    score += sales_score

    # 4. Pro DJ boost (0–15 points)
    if is_pro_dj:
        score += 15

    # 5. Verified DJ boost (0–5 points)
    if is_verified_dj:
        score += 5

    # 6. Spam/manipulation penalty
    # Track title over 60 chars — keyword stuffing signal
    if len(track.title) > 60:
        score -= 10

    # Same DJ appearing more than 3 times in top results
    # (handled at result assembly level, not per-track)

    return score
```

## Anti-Abuse Rules

```python
def assemble_search_results(scored_tracks, page=1, per_page=20):
    # Sort by score
    sorted_tracks = sorted(scored_tracks,
                           key=lambda t: t.score, reverse=True)

    # Anti-monopoly: max 3 tracks from same DJ per page
    result = []
    dj_count = {}
    for track in sorted_tracks:
        dj_id = track.dj_id
        if dj_count.get(dj_id, 0) >= 3:
            continue
        dj_count[dj_id] = dj_count.get(dj_id, 0) + 1
        result.append(track)
        if len(result) == per_page:
            break

    return result
```

## Admin Search Controls

Add to Admin → Platform Controls:

```
┌──────────────────────────────────────────────────────────────┐
│  SEARCH RANKING WEIGHTS                                      │
│                                                              │
│  Text relevance:    [ 40 ] pts max                          │
│  Recency:           [ 20 ] pts max                          │
│  Sales velocity:    [ 20 ] pts max                          │
│  Pro DJ boost:      [ 15 ] pts                              │
│  Verified boost:    [  5 ] pts                              │
│  Keyword spam penalty: [ -10 ] pts                          │
│  Max same DJ per page: [  3 ] tracks                        │
│                                                              │
│  [Save Weights]  [Reset to Default]                         │
└──────────────────────────────────────────────────────────────┘
```

---
---

# FIX 05 — COLLABORATION EDGE CASES

## All Edge Cases Handled

---

### Case 1: Collaborator Account Banned Mid-Cycle

```python
def handle_collab_ban(banned_dj_id):
    # Find all active collab tracks with this DJ
    collabs = TrackCollaborator.objects.filter(
        dj_id=banned_dj_id,
        track__is_active=True
    )

    for collab in collabs:
        # Their % reverts to the track owner (lead DJ)
        TrackCollaborator.objects.filter(
            track=collab.track,
            dj_id=collab.track.dj_id  # lead DJ
        ).update(
            revenue_percentage=F('revenue_percentage')
                               + collab.revenue_percentage
        )
        # Notify lead DJ
        send_collab_removed_email(
            collab.track.dj_id,
            reason=f"Collaborator account suspended"
        )
        collab.delete()

    # Any pending earnings for banned DJ go to escrow, not lost
    DJWallet.objects.filter(dj_id=banned_dj_id).update(
        pending_earnings=0,
        escrow_amount=F('escrow_amount') + F('pending_earnings')
    )
```

---

### Case 2: Collaborator Deletes Account

```python
# Same as ban — their % reverts to lead DJ
# Their historical earnings already paid out = no action needed
# Their pending earnings = escrow hold (30 days) then returned to platform
```

---

### Case 3: Lead DJ Deletes Collab Track

```python
def soft_delete_track(track_id, deleted_by):
    track = Track.objects.get(id=track_id)
    collabs = TrackCollaborator.objects.filter(track=track)

    # Notify all collaborators
    for collab in collabs:
        send_email(
            to=collab.dj.email,
            subject="A track you collaborated on has been removed",
            body=(
                f"'{track.title}' by {track.lead_dj.name} has been "
                f"removed from MixMint. Your earnings from previous "
                f"sales are unaffected."
            )
        )

    # Soft delete
    track.is_deleted = True
    track.deleted_at = timezone.now()
    track.deleted_by = deleted_by
    track.save()
```

---

### Case 4: Can a Collaborator See Track Sales?

```
YES — but limited view only.

Collab DJ's earnings page shows:
- Track name (linked to public page if still active)
- Their revenue % on the track
- Their earnings from this track (their share only)
- NOT: total track sales, other collaborators' earnings, lead DJ earnings
```

```sql
-- RLS: collaborators can see their own split earnings only
CREATE POLICY "collab own earnings" ON track_collaborators
  FOR SELECT USING (dj_id = auth.uid());
```

---

### Case 5: Can a Collaborator Remove Themselves?

```
YES — from their DJ Dashboard → My Tracks → Collaborations tab

On removal:
- Their % redistributed to lead DJ immediately
- Future sales: lead DJ gets their % back
- Past earnings: already paid, unaffected
- Lead DJ notified by email
- Track stays live (removal doesn't affect availability)
```

---

### Case 6: Collab DJ Has No Payout KYC

```python
def distribute_collab_earnings(purchase):
    collabs = TrackCollaborator.objects.filter(
        track_id=purchase.content_id
    )
    for collab in collabs:
        dj_profile = Profile.objects.get(id=collab.dj_id)
        share = purchase.dj_revenue * (collab.revenue_percentage / 100)

        if not dj_profile.payout_details_verified:
            # Hold in escrow — not lost
            DJWallet.objects.filter(dj_id=collab.dj_id).update(
                escrow_amount=F('escrow_amount') + share
            )
            # Email: add payout details to release held earnings
            send_payout_kyc_reminder(collab.dj_id, share)
        else:
            DJWallet.objects.filter(dj_id=collab.dj_id).update(
                pending_earnings=F('pending_earnings') + share,
                total_earnings=F('total_earnings') + share
            )
```

---
---

# FIX 06 — 2FA IMPLEMENTATION

## Method: TOTP (Time-based One-Time Password)
Compatible with Google Authenticator, Authy, any TOTP app. No SMS dependency.

---

## Setup Flow (DJ Dashboard → Settings → Security)

```
Step 1: DJ clicks "Enable 2FA"
  → QR code generated and shown (pyotp library)
  → Instructions: "Scan this with Google Authenticator or Authy"
  → Input: "Enter the 6-digit code from your app to verify"
  → On success: 2FA enabled, 8 recovery codes shown ONCE

Step 2: Recovery codes shown (show once, never again)
  ┌───────────────────────────────────────┐
  │  Save these recovery codes safely.   │
  │  Each can be used once if you lose   │
  │  access to your authenticator app.   │
  │                                       │
  │  XXXX-XXXX    XXXX-XXXX             │
  │  XXXX-XXXX    XXXX-XXXX             │
  │  XXXX-XXXX    XXXX-XXXX             │
  │  XXXX-XXXX    XXXX-XXXX             │
  │                                       │
  │  [Download Codes]  [I've saved them] │
  └───────────────────────────────────────┘

Step 3: 2FA active — payout gate now requires it
```

---

## Implementation

```python
import pyotp
import qrcode
from io import BytesIO
import base64

def generate_2fa_setup(dj_id):
    dj = Profile.objects.get(id=dj_id)

    # Generate secret
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)

    # Generate QR code
    provisioning_uri = totp.provisioning_uri(
        name=dj.email,
        issuer_name="MixMint"
    )
    qr = qrcode.make(provisioning_uri)
    buffer = BytesIO()
    qr.save(buffer, format='PNG')
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    # Store secret temporarily (not confirmed yet)
    dj.totp_secret_pending = secret
    dj.save()

    return {'qr_code': qr_base64, 'secret': secret}


def verify_and_enable_2fa(dj_id, code):
    dj = Profile.objects.get(id=dj_id)
    totp = pyotp.TOTP(dj.totp_secret_pending)

    if not totp.verify(code, valid_window=1):
        raise ValueError("Invalid code. Try again.")

    # Confirm 2FA
    dj.totp_secret = dj.totp_secret_pending
    dj.totp_secret_pending = None
    dj.two_fa_enabled = True
    dj.save()

    # Generate recovery codes
    recovery_codes = [
        f"{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}"
        for _ in range(8)
    ]
    # Store hashed versions only
    for code in recovery_codes:
        TwoFARecoveryCode.objects.create(
            dj_id=dj_id,
            code_hash=hashlib.sha256(code.encode()).hexdigest()
        )

    return recovery_codes  # Shown once, never stored plain


def verify_2fa_code(dj_id, code):
    dj = Profile.objects.get(id=dj_id)

    # Try TOTP first
    totp = pyotp.TOTP(dj.totp_secret)
    if totp.verify(code, valid_window=1):
        return True

    # Try recovery code
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    recovery = TwoFARecoveryCode.objects.filter(
        dj_id=dj_id,
        code_hash=code_hash,
        used=False
    ).first()

    if recovery:
        recovery.used = True
        recovery.used_at = timezone.now()
        recovery.save()
        # Alert DJ that a recovery code was used
        send_recovery_code_used_email(dj_id)
        return True

    return False
```

---

## 2FA Gate on Payout

```python
@dj_required
def request_payout(request):
    dj = Profile.objects.get(id=request.user.id)

    if not dj.two_fa_enabled:
        return JsonResponse({
            'error': '2FA required for payouts',
            'action': 'enable_2fa'
        }, status=403)

    # Check 2FA was verified in this session recently
    last_2fa = request.session.get('last_2fa_verified_at')
    if not last_2fa or (timezone.now() - last_2fa).seconds > 3600:
        return JsonResponse({
            'error': '2FA verification required',
            'action': 'verify_2fa'
        }, status=403)

    # Proceed with payout...
```

---

## 2FA Scope

```
Required for:           NOT required for:
─────────────────────   ────────────────────────────
Payout requests         Browsing dashboard
Bank detail changes     Uploading tracks
Email changes           Viewing earnings
Password changes        Responding to collabs
Admin login (always)
```

---

## DB Schema

```sql
ALTER TABLE profiles
  ADD COLUMN two_fa_enabled BOOLEAN DEFAULT FALSE,
  ADD COLUMN totp_secret VARCHAR(32),
  ADD COLUMN totp_secret_pending VARCHAR(32);

CREATE TABLE two_fa_recovery_codes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  dj_id UUID REFERENCES profiles(id),
  code_hash VARCHAR(64) NOT NULL,
  used BOOLEAN DEFAULT FALSE,
  used_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---
---

# FIX 07 — DJ ONBOARDING WIZARD

## Trigger
Fires once, on first login after DJ application is approved.

---

## 5-Step Wizard

```
Progress: ●●○○○  Step 1 of 5
```

### Step 1 — Welcome
```
┌──────────────────────────────────────────────────────┐
│  Welcome to MixMint, DJ [Name]. ⚡                  │
│                                                      │
│  Your DJ Panel is ready. Let's set up your          │
│  storefront in 5 quick steps.                       │
│                                                      │
│  This takes about 3 minutes.                        │
│                                                      │
│  [Let's Go →]                [Skip for now]         │
└──────────────────────────────────────────────────────┘
```

### Step 2 — Profile Setup
- DJ display name (pre-filled from application)
- Short bio (max 200 chars, char counter)
- Genre tags (multi-select, max 5)
- Avatar upload (circle preview, 400×400px recommended)
- Banner upload (strip preview, 1400×400px recommended)

### Step 3 — Payout Details
```
┌──────────────────────────────────────────────────────┐
│  Add Payout Details                                  │
│                                                      │
│  How would you like to receive earnings?             │
│                                                      │
│  ● UPI ID  (fastest)                                │
│    UPI ID: [ rohit@upi            ]                 │
│                                                      │
│  ○ Bank Account                                     │
│    Account Number: [            ]                   │
│    IFSC Code:      [            ]                   │
│    Account Name:   [            ]                   │
│                                                      │
│  You can change this anytime in Settings.           │
│  Payouts require ₹500 minimum balance.              │
│                                                      │
│  [Save & Continue →]     [Skip — Add Later]         │
└──────────────────────────────────────────────────────┘
```

**If skipped:** Earnings still accumulate. Payout button shows:
*"Add payout details to withdraw earnings"* — links to Settings.

### Step 4 — Upload First Track (Optional)
- Simplified upload form (title, price, file only — genre/year can be edited later)
- "This is optional — you can upload from your dashboard anytime"
- [Upload Now] or [Skip]

### Step 5 — Done
```
┌──────────────────────────────────────────────────────┐
│  You're all set. ⚡                                  │
│                                                      │
│  Your storefront:                                    │
│  mixmint.site/dj/rohit  [Copy Link]                 │
│                                                      │
│  Share it with your fans to start selling.          │
│                                                      │
│  ✓ Profile complete                                 │
│  ✓ Payout details saved                            │
│  ✓ First track uploaded                            │
│                                                      │
│  [Go to My Dashboard →]                             │
└──────────────────────────────────────────────────────┘
```

---

## Incomplete Profile Nudges (After Wizard)

If DJ skipped steps, show gentle reminders in dashboard:

```
┌──────────────────────────────────────────────────────┐
│  📋 Complete your profile  (2 items remaining)      │
│                                                      │
│  ✓ Profile photo           [done]                  │
│  ✗ Payout details          [Add →]                 │
│  ✗ First track uploaded    [Upload →]              │
└──────────────────────────────────────────────────────┘
```
Disappears once all items complete. Never shows again.

---

## DB Schema

```sql
ALTER TABLE profiles
  ADD COLUMN onboarding_completed BOOLEAN DEFAULT FALSE,
  ADD COLUMN onboarding_step INTEGER DEFAULT 0,
  ADD COLUMN payout_method VARCHAR(10),  -- 'upi' | 'bank'
  ADD COLUMN payout_upi_id VARCHAR(100),
  ADD COLUMN payout_bank_account VARCHAR(30),
  ADD COLUMN payout_bank_ifsc VARCHAR(15),
  ADD COLUMN payout_bank_name VARCHAR(100),
  ADD COLUMN payout_details_verified BOOLEAN DEFAULT FALSE;
```

---
---

# FIX 08 — CONTENT REPORTING BY BUYERS

## Report Button Location
- Every track and album detail page
- Small `⚑ Report` link — 12px, muted, bottom of page (not prominent)
- Only visible to logged-in buyers (not DJs viewing their own track)

---

## Report Form

```
┌──────────────────────────────────────────────────────┐
│  Report This Track                                   │
│                                                      │
│  Why are you reporting this track?                  │
│                                                      │
│  ○ File is corrupt or unplayable                    │
│  ○ File doesn't match description                   │
│  ○ Duplicate of another track                       │
│  ○ Suspected copyright violation                    │
│  ○ Inappropriate content                            │
│  ○ Other                                            │
│                                                      │
│  Additional details: [optional, max 300 chars]      │
│                                                      │
│  [Submit Report]                                    │
│                                                      │
│  Reports are reviewed by MixMint admin.             │
│  False reports may result in account restrictions.  │
└──────────────────────────────────────────────────────┘
```

---

## Auto-Flag Threshold

```python
REPORT_THRESHOLDS = {
    'corrupt': 2,           # 2 reports → auto-flag for admin
    'copyright': 1,         # 1 copyright report → immediate admin alert
    'misleading': 3,
    'duplicate': 3,
    'inappropriate': 2,
    'other': 5
}

def check_report_threshold(content_id, report_type):
    count = ContentReport.objects.filter(
        content_id=content_id,
        report_type=report_type,
        status='pending'
    ).count()

    threshold = REPORT_THRESHOLDS.get(report_type, 3)

    if count >= threshold:
        # Auto-flag track for admin review
        flag_content_for_review(content_id, trigger=f"{count}x {report_type}")

        if report_type == 'copyright':
            # Immediate admin email for copyright
            send_urgent_admin_alert(content_id, report_type)
```

---

## Admin Reports Queue

Add to Admin → Content Moderation → Reports tab:

```
Reports (14 pending)

Filter: [All] [Copyright] [Corrupt] [Misleading] [Auto-flagged]

Content          DJ        Reports    Type         Priority  Action
────────────────────────────────────────────────────────────────────
Track: Mix 01    DJ Rohit  3          Copyright    🔴 HIGH   [Review]
Album: Pack 02   DJ Priya  2          Corrupt      🟡 MED    [Review]
Track: Bass Trk  DJ Arjun  1          Misleading   🟢 LOW    [Review]
```

---

## DB Schema

```sql
CREATE TABLE content_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content_id UUID NOT NULL,
  content_type VARCHAR(10),  -- 'track' | 'album'
  reported_by UUID REFERENCES profiles(id),
  report_type VARCHAR(30),
  description TEXT,
  status VARCHAR(20) DEFAULT 'pending',
    -- 'pending' | 'reviewed' | 'actioned' | 'dismissed'
  reviewed_by UUID REFERENCES profiles(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),

  -- Prevent same user reporting same content multiple times
  UNIQUE(content_id, reported_by, report_type)
);
```

---
---

# FIX 09 — BUYER STAR RATINGS

## Rules
- Only buyers who completed a download can rate
- One rating per purchase (not per buyer — same buyer buys track twice = can rate twice)
- Stars only (1–5) — no text reviews (avoids moderation overhead)
- Ratings visible publicly on track/album page
- DJs cannot rate their own tracks
- Ratings cannot be deleted by DJ — only by admin

---

## UI on Track Page

```
★★★★☆  4.2  (47 ratings)
```
- Star display: filled/half/empty stars in mint (dark) or amber (light)
- Count in DM Mono 13px muted
- Only show if 3+ ratings — below that: no stars shown (prevents 1-rating distortion)

## Rating Widget (shown to eligible buyers)

```
┌──────────────────────────────────────────────────────┐
│  Rate this track                                     │
│                                                      │
│  ☆ ☆ ☆ ☆ ☆   (tap to rate)                        │
│                                                      │
│  You purchased this track on [Date]                 │
└──────────────────────────────────────────────────────┘
```
- Appears below security notice on track page
- Only for logged-in buyers with completed download
- After rating: widget replaced with their submitted rating
- Can change rating within 48 hours

---

## DB Schema

```sql
CREATE TABLE track_ratings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content_id UUID NOT NULL,
  content_type VARCHAR(10),
  purchase_id UUID REFERENCES purchases(id),
  user_id UUID REFERENCES profiles(id),
  rating SMALLINT CHECK (rating >= 1 AND rating <= 5),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),

  UNIQUE(purchase_id)  -- one rating per purchase
);

-- Denormalized average on tracks table for fast reads
ALTER TABLE tracks
  ADD COLUMN avg_rating DECIMAL(3,2) DEFAULT NULL,
  ADD COLUMN rating_count INTEGER DEFAULT 0;

-- Update trigger
CREATE OR REPLACE FUNCTION update_track_rating()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE tracks SET
    avg_rating = (
      SELECT AVG(rating)::DECIMAL(3,2)
      FROM track_ratings
      WHERE content_id = NEW.content_id
    ),
    rating_count = (
      SELECT COUNT(*) FROM track_ratings
      WHERE content_id = NEW.content_id
    )
  WHERE id = NEW.content_id;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

---
---

# FIX 10 — PAYOUT BANK/UPI DETAILS FLOW

## Collection Points
1. DJ Onboarding Wizard Step 3 (primary)
2. DJ Dashboard → Settings → Payout Details (always editable)
3. First time DJ tries to request payout (gate)

---

## Payout Settings Page

```
┌──────────────────────────────────────────────────────────────┐
│  Payout Details                                              │
│                                                              │
│  Method:  ● UPI   ○ Bank Transfer                          │
│                                                              │
│  UPI ID:  [ rohit@ybl              ]  [Verify]             │
│           ✓ Verified                                        │
│                                                              │
│  ─── OR ──────────────────────────────────────────         │
│                                                              │
│  Bank Account Number:  [                    ]               │
│  IFSC Code:            [                    ]               │
│  Account Holder Name:  [                    ]               │
│                                                              │
│  [Save Payout Details]                                      │
│                                                              │
│  🔐 Changing payout details requires 2FA verification.     │
│  A 48-hour hold applies after any payout detail change.    │
└──────────────────────────────────────────────────────────────┘
```

---

## UPI Verification

```python
def verify_upi_id(upi_id):
    """
    Use Razorpay/PhonePe UPI validation API to verify
    the UPI ID exists before saving
    """
    # Razorpay contact verification API
    response = razorpay_client.payment.validate_vpa({'vpa': upi_id})
    return response.get('success', False)
```

---

## Security Rules on Payout Detail Changes

```python
def update_payout_details(dj_id, new_details, totp_code):
    # 1. Require 2FA
    if not verify_2fa_code(dj_id, totp_code):
        raise PermissionError("2FA verification failed")

    # 2. Log the change
    PayoutDetailChangeLog.objects.create(
        dj_id=dj_id,
        old_method=old_profile.payout_method,
        old_upi=old_profile.payout_upi_id,
        new_method=new_details['method'],
        new_upi=new_details.get('upi_id'),
        ip_address=get_client_ip(request),
        device_hash=get_device_hash(request)
    )

    # 3. Apply 48-hour hold on payouts after change
    profile.payout_hold_until = timezone.now() + timedelta(hours=48)
    profile.payout_details_verified = True
    profile.save()

    # 4. Send security alert email
    send_payout_details_changed_email(dj_id)
```

---
---


# ═══════════════════════════════════════════════════
# SECTION D — CRITICAL IMPROVEMENTS 01–06
# ═══════════════════════════════════════════════════
# IMPROVEMENT 01 — DISPUTE RESOLUTION SYSTEM

## Overview
When a buyer and DJ disagree about a purchase — wrong file, misleading description, quality issue — admin acts as neutral arbitrator. Every dispute must be documented, both sides heard, and outcome recorded.

---

## Dispute Types

```
Type                    Initiated by    Description
────────────────────────────────────────────────────────────
wrong_file              Buyer           Downloaded file doesn't match description
corrupt_file            Buyer           File unplayable (separate from failed download)
misleading_description  Buyer           Track described as something it isn't
quality_issue           Buyer           File quality significantly worse than preview
unauthorised_sale       Third party     Content sold without rights (copyright)
earnings_dispute        DJ              DJ believes their split was calculated wrong
payout_dispute          DJ              DJ disputes a payout amount or status
```

---

## Buyer Dispute Flow

### Entry Point
- Library page → per purchase → `Open Dispute` link
- Available only for purchases where:
  - Download completed successfully (refund handles incomplete downloads)
  - Within 14 days of purchase
  - No existing open dispute on same purchase

### Step 1 — Dispute Form

```
┌──────────────────────────────────────────────────────────────┐
│  Open a Dispute                                              │
│  Track: [Track Name] · Purchased: [Date] · ₹49             │
│                                                              │
│  What's the issue?                                          │
│  ○ File doesn't match what was described                    │
│  ○ File is corrupt or unplayable                            │
│  ○ Quality is significantly worse than preview              │
│  ○ Other issue with this purchase                           │
│                                                              │
│  Describe the issue:                                        │
│  [textarea — min 30 chars, max 500 chars]                   │
│                                                              │
│  Supporting evidence (optional):                            │
│  [Upload screenshot or file — max 5MB, image only]         │
│                                                              │
│  What resolution are you looking for?                       │
│  ○ Full refund                                              │
│  ○ Replacement file from DJ                                 │
│  ○ Partial refund                                           │
│  ○ Just want it on record                                   │
│                                                              │
│  [Submit Dispute]                                           │
│                                                              │
│  Note: Opening a dispute notifies the DJ. False or          │
│  abusive disputes may result in account restrictions.       │
└──────────────────────────────────────────────────────────────┘
```

---

## DJ Response Flow

### Notification to DJ
- Email: *"A buyer has opened a dispute on '[Track Name]'. You have 48 hours to respond."*
- DJ Dashboard: `Disputes` tab appears (only when there's an active dispute)

### DJ Response Form

```
┌──────────────────────────────────────────────────────────────┐
│  Dispute Response — [Track Name]                            │
│                                                              │
│  Buyer's claim: [buyer's description shown here]           │
│  Requested resolution: [refund / replacement / etc.]       │
│                                                              │
│  Your response:                                             │
│  [textarea — min 30 chars, max 500 chars]                   │
│                                                              │
│  Supporting evidence (optional):                            │
│  [Upload — max 5MB]                                         │
│                                                              │
│  How would you like to resolve this?                        │
│  ○ I'll provide a replacement/corrected file               │
│  ○ I agree to a partial refund                             │
│  ○ I disagree — the file is correct as described           │
│  ○ I agree to a full refund                                │
│                                                              │
│  [Submit Response]                                          │
└──────────────────────────────────────────────────────────────┘
```

---

## Admin Arbitration Panel (Admin → Disputes)

```
┌──────────────────────────────────────────────────────────────┐
│  DISPUTES                                                    │
│                                                              │
│  Open: 3  ·  Awaiting DJ response: 2  ·  Resolved: 47      │
│                                                              │
│  Filter: [All][Open][Awaiting][Admin Review][Resolved]      │
│                                                              │
│  #    Buyer    Track      DJ        Status          Age     │
│  ─────────────────────────────────────────────────────────  │
│  142  Ravi     Mix 01     DJ Rohit  DJ Responded    2d  [▼] │
│  141  Priya    Bass Pack  DJ Arjun  Awaiting DJ     1d  [▼] │
│  140  Kiran    House Set  DJ Priya  Resolved ✓      5d  [▼] │
│                                                              │
│  Expand row shows:                                          │
│  · Full buyer claim + evidence                             │
│  · DJ response + evidence                                  │
│  · Download logs for this purchase                         │
│  · Admin decision panel (see below)                        │
└──────────────────────────────────────────────────────────────┘
```

### Admin Decision Panel (per dispute)

```
┌──────────────────────────────────────────────────────────────┐
│  Admin Decision                                              │
│                                                              │
│  Internal notes: [admin-only textarea]                      │
│                                                              │
│  Decision:                                                  │
│  ○ Full refund to buyer (clawback DJ earnings)             │
│  ○ Partial refund: ₹[___] to buyer                        │
│  ○ Dismiss — in favour of DJ (no refund)                   │
│  ○ Dismiss — buyer claim not credible                      │
│  ○ Warn DJ (no financial action)                           │
│  ○ Escalate — requires further review                      │
│                                                              │
│  Message to buyer: [textarea — sent as email]              │
│  Message to DJ:    [textarea — sent as email]              │
│                                                              │
│  [Submit Decision]                                          │
└──────────────────────────────────────────────────────────────┘
```

---

## Timelines & Auto-Escalation

```python
DISPUTE_TIMELINES = {
    'dj_response_deadline_hours': 48,
    'admin_review_deadline_hours': 72,
    'auto_refund_if_dj_no_response': True,
    # If DJ doesn't respond in 48h → auto-refund buyer
}

def check_dispute_deadlines():
    """Run every hour via cron"""
    now = timezone.now()

    # Auto-refund if DJ didn't respond in time
    overdue = Dispute.objects.filter(
        status='awaiting_dj_response',
        dj_response_deadline__lt=now
    )
    for dispute in overdue:
        auto_resolve_dispute(
            dispute,
            outcome='refund',
            reason='DJ did not respond within 48 hours'
        )
        notify_dj_auto_resolved(dispute)
        notify_buyer_auto_resolved(dispute)
```

---

## DB Schema

```sql
CREATE TABLE disputes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  purchase_id UUID REFERENCES purchases(id),
  buyer_id UUID REFERENCES profiles(id),
  dj_id UUID REFERENCES profiles(id),
  dispute_type VARCHAR(30),
  buyer_description TEXT,
  buyer_evidence_url VARCHAR(500),
  buyer_requested_resolution VARCHAR(30),
  dj_response TEXT,
  dj_evidence_url VARCHAR(500),
  dj_proposed_resolution VARCHAR(30),
  status VARCHAR(30) DEFAULT 'open',
    -- 'open' | 'awaiting_dj_response' | 'admin_review'
    -- | 'resolved_refund' | 'resolved_dismissed' | 'auto_resolved'
  admin_notes TEXT,
  admin_decision VARCHAR(30),
  admin_message_to_buyer TEXT,
  admin_message_to_dj TEXT,
  resolved_by UUID REFERENCES profiles(id),
  dj_response_deadline TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  resolved_at TIMESTAMPTZ
);
```

---
---

# IMPROVEMENT 02 — ACCOUNT DELETION & DATA EXPORT

## Rules Matrix

```
Scenario                    Tracks    Buyer Purchases    Earnings
──────────────────────────────────────────────────────────────────
Buyer deletes account       N/A       Downloads: still   N/A
                                      work for 12mo,
                                      then expire
DJ deletes account          Hidden    Existing buyer     Paid out
                            (not      downloads still    (if above
                            deleted)  work forever       threshold)
DJ deletes + unpaid         Hidden    Existing buyer     Held in
earnings below threshold              downloads work     escrow 90d
Admin deletes account       Admin     Same as above      Admin
(suspension)                decision  per type           decision
```

---

## Buyer Account Deletion Flow

### Entry: Profile Settings → Danger Zone → Delete Account

```
┌──────────────────────────────────────────────────────────────┐
│  Delete Your Account                                         │
│                                                              │
│  Before you go — here's what happens:                      │
│                                                              │
│  ✓ Your account and personal data will be deleted          │
│  ✓ Your purchase history will be anonymised                │
│  ⚠ Your download access expires in 12 months              │
│  ✗ Purchases cannot be refunded at deletion                │
│                                                              │
│  Download your data first:                                  │
│  [Export My Data]  ← generates ZIP with purchase history   │
│                                                              │
│  Type DELETE to confirm:                                    │
│  [________________]                                         │
│                                                              │
│  [Permanently Delete Account]                               │
└──────────────────────────────────────────────────────────────┘
```

---

## DJ Account Deletion Flow

```
┌──────────────────────────────────────────────────────────────┐
│  Delete Your DJ Account                                      │
│                                                              │
│  This is permanent. Here's what happens:                   │
│                                                              │
│  ✓ Your storefront will be taken offline immediately       │
│  ✓ Your personal data will be deleted                      │
│  ⚠ Tracks stay archived (required for buyer access)       │
│  ⚠ Buyers who purchased your tracks keep download access  │
│  ⚠ Pending earnings: paid out if above ₹500 threshold     │
│  ⚠ Earnings below ₹500 threshold are forfeited            │
│  ⚠ Active collaborations: your % reverts to lead DJ       │
│                                                              │
│  Pending balance: ₹1,240                                   │
│  [Request Final Payout First]  ← recommended              │
│                                                              │
│  Type DELETE to confirm:  [________________]                │
│                                                              │
│  [Permanently Delete Account]                               │
└──────────────────────────────────────────────────────────────┘
```

---

## Data Export (Both Buyer and DJ)

```python
def generate_data_export(user_id):
    """
    Generates a ZIP containing:
    - profile_data.json (name, email, created_at, role)
    - purchases.csv (buyer) or earnings.csv (DJ)
    - download_history.csv (buyer)
    - invoices/ folder with all PDFs
    """
    import zipfile
    from io import BytesIO

    buffer = BytesIO()
    profile = Profile.objects.get(id=user_id)

    with zipfile.ZipFile(buffer, 'w') as zf:
        # Profile data
        profile_data = {
            'name': profile.display_name,
            'email': profile.email,
            'role': profile.role,
            'created_at': profile.created_at.isoformat(),
            'exported_at': timezone.now().isoformat()
        }
        zf.writestr(
            'profile_data.json',
            json.dumps(profile_data, indent=2)
        )

        if profile.role == 'user':
            # Purchase history
            purchases = Purchase.objects.filter(user_id=user_id)
            csv_data = generate_purchases_csv(purchases)
            zf.writestr('purchases.csv', csv_data)

        elif profile.role == 'dj':
            # Earnings history
            earnings = generate_earnings_csv(user_id)
            zf.writestr('earnings.csv', earnings)

        # Invoices
        invoices = Purchase.objects.filter(
            user_id=user_id,
            invoice_r2_key__isnull=False
        )
        for purchase in invoices:
            pdf = fetch_from_r2(purchase.invoice_r2_key)
            zf.writestr(
                f'invoices/invoice_{purchase.id}.pdf',
                pdf
            )

    # Store export in R2, email link to user
    export_key = f"exports/{user_id}/{timezone.now().date()}.zip"
    upload_to_r2(buffer.getvalue(), export_key)
    send_data_export_email(user_id, export_key)
```

---

## Anonymisation on Deletion

```python
def anonymise_user_data(user_id):
    """
    GDPR-style: remove PII but keep records for accounting
    """
    Profile.objects.filter(id=user_id).update(
        display_name=f"Deleted User {user_id[:8]}",
        email=f"deleted_{user_id[:8]}@deleted.mixmint.site",
        avatar_url=None,
        bio=None,
        payout_upi_id=None,
        payout_bank_account=None,
        is_deleted=True,
        deleted_at=timezone.now()
    )
    # Delete from Supabase auth (triggers cascade)
    supabase.auth.admin.delete_user(user_id)
```

---
---

# IMPROVEMENT 03 — FRAUD DETECTION ON PURCHASES

## Fraud Signals to Detect

```
Signal                              Risk Level    Action
──────────────────────────────────────────────────────────────
Same card, 3+ purchases in 1hr      HIGH          Flag + slow down
Same IP, 5+ new accounts in 24hr    CRITICAL      Block IP
Same device, 2+ accounts            HIGH          Flag both accounts
Purchase immediately after signup   MEDIUM        Extra verification
Same track bought 2x by same user   MEDIUM        Block (already owns)
High-value purchase on new account  MEDIUM        Flag for review
Multiple failed payments then pass  HIGH          Flag account
```

---

## Implementation

```python
from django.core.cache import cache

def run_fraud_checks(user_id, payment_data):
    """
    Run before creating payment order.
    Returns: (is_allowed, risk_level, flags)
    """
    flags = []
    risk_score = 0
    ip = payment_data['ip_address']
    device = payment_data['device_hash']
    user = Profile.objects.get(id=user_id)

    # Check 1: Purchase velocity (same user)
    recent_purchases = Purchase.objects.filter(
        user_id=user_id,
        created_at__gte=timezone.now() - timedelta(hours=1)
    ).count()
    if recent_purchases >= 3:
        flags.append('high_purchase_velocity')
        risk_score += 30

    # Check 2: IP velocity (new accounts from same IP)
    ip_accounts_today = Profile.objects.filter(
        registration_ip=ip,
        created_at__gte=timezone.now() - timedelta(hours=24)
    ).count()
    if ip_accounts_today >= 5:
        flags.append('ip_account_farm')
        risk_score += 50

    # Check 3: Same device, multiple accounts
    device_accounts = Profile.objects.filter(
        registration_device=device
    ).count()
    if device_accounts >= 2:
        flags.append('multi_account_device')
        risk_score += 25

    # Check 4: Account age vs purchase value
    account_age_days = (timezone.now() - user.created_at).days
    if account_age_days < 1 and payment_data['amount'] > 20000:  # ₹200+
        flags.append('new_account_high_value')
        risk_score += 20

    # Check 5: Already owns this track
    already_owns = Purchase.objects.filter(
        user_id=user_id,
        content_id=payment_data['content_id'],
        status='active'
    ).exists()
    if already_owns:
        return False, 'blocked', ['already_owns_content']

    # Check 6: Failed payment attempts then success
    failed_attempts = cache.get(f"failed_payments_{user_id}", 0)
    if failed_attempts >= 3:
        flags.append('multiple_payment_failures')
        risk_score += 20

    # Decision
    if risk_score >= 70:
        log_fraud_event(user_id, flags, risk_score, 'blocked')
        return False, 'blocked', flags
    elif risk_score >= 40:
        log_fraud_event(user_id, flags, risk_score, 'flagged')
        return True, 'flagged', flags  # allow but flag for review
    else:
        return True, 'clean', flags


def log_fraud_event(user_id, flags, score, outcome):
    FraudLog.objects.create(
        user_id=user_id,
        flags=flags,
        risk_score=score,
        outcome=outcome
    )
    if outcome == 'blocked' or score >= 70:
        send_admin_fraud_alert(user_id, flags, score)
```

---

## Admin Fraud Dashboard (Admin → Security → Fraud)

```
┌──────────────────────────────────────────────────────────────┐
│  FRAUD DETECTION                                             │
│                                                              │
│  Blocked today: 3  ·  Flagged: 7  ·  False positives: 1   │
│                                                              │
│  Recent Events:                                             │
│  User      Score  Flags                    Outcome  Action  │
│  ────────────────────────────────────────────────────────   │
│  user_x    85     ip_farm, velocity        Blocked  [View]  │
│  user_y    45     new_acct_high_value       Flagged  [View]  │
│                                                              │
│  False Positive Rate: 2.1%   [Adjust Thresholds]           │
└──────────────────────────────────────────────────────────────┘
```

---

## DB Schema

```sql
CREATE TABLE fraud_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES profiles(id),
  flags JSONB,
  risk_score INTEGER,
  outcome VARCHAR(20),  -- 'clean' | 'flagged' | 'blocked'
  ip_address VARCHAR(45),
  device_hash VARCHAR(64),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE profiles
  ADD COLUMN registration_ip VARCHAR(45),
  ADD COLUMN registration_device VARCHAR(64),
  ADD COLUMN fraud_flagged BOOLEAN DEFAULT FALSE,
  ADD COLUMN fraud_score INTEGER DEFAULT 0;
```

---
---

# IMPROVEMENT 04 — TDS / PAN COMPLIANCE (INDIA)

## Legal Context

Under Indian income tax law:
- Section 194J: TDS on professional fees — 10% above ₹30,000/year
- Section 194C: TDS on contractor payments — 1-2% above ₹30,000/year
- MixMint must deduct TDS before paying DJ, deposit with govt, issue Form 16A

**Important:** Consult a CA to confirm which section applies to DJ payouts specifically.

---

## PAN Collection (DJ Onboarding — Step 3 Addition)

Add to DJ onboarding wizard Step 3 (Payout Details):

```
┌──────────────────────────────────────────────────────────────┐
│  Tax Information (Required for Payouts)                     │
│                                                              │
│  PAN Number:  [__________]  (10-character PAN)             │
│                                                              │
│  Why we need this:                                          │
│  As per Indian income tax law, MixMint is required to      │
│  deduct TDS on earnings above ₹30,000/year and file        │
│  returns with the Income Tax Department.                    │
│                                                              │
│  Your PAN is required before your first payout.            │
│  It is stored securely and never shared publicly.          │
│                                                              │
│  [Save PAN]           [I'll add this later]                │
│                                                              │
│  Note: Payouts are held until PAN is verified.             │
└──────────────────────────────────────────────────────────────┘
```

---

## TDS Calculation Logic

```python
TDS_ANNUAL_THRESHOLD = 30000  # ₹30,000
TDS_RATE = Decimal('0.10')    # 10% under 194J

def calculate_payout_with_tds(dj_id, payout_amount):
    """
    Called when processing weekly payout.
    Checks cumulative annual earnings and deducts TDS if applicable.
    """
    financial_year_start = get_financial_year_start()  # April 1

    # Total paid to DJ this financial year
    total_paid_this_fy = Payout.objects.filter(
        dj_id=dj_id,
        status='paid',
        created_at__gte=financial_year_start
    ).aggregate(total=Sum('amount'))['total'] or 0

    gross = Decimal(str(payout_amount))
    tds_deducted = Decimal('0')

    if total_paid_this_fy >= TDS_ANNUAL_THRESHOLD:
        # Full TDS on this payout
        tds_deducted = gross * TDS_RATE

    elif total_paid_this_fy + gross > TDS_ANNUAL_THRESHOLD:
        # TDS only on the portion above threshold
        taxable_portion = (
            total_paid_this_fy + gross - TDS_ANNUAL_THRESHOLD
        )
        tds_deducted = taxable_portion * TDS_RATE

    net_payout = gross - tds_deducted

    return {
        'gross': gross,
        'tds_deducted': tds_deducted,
        'net_payout': net_payout,
        'tds_rate': TDS_RATE if tds_deducted > 0 else Decimal('0')
    }
```

---

## DJ Payout Breakdown (Dashboard)

When TDS applies, show clearly in payout history:

```
┌──────────────────────────────────────────────────────────────┐
│  Payout — 15 March 2026                                     │
│                                                              │
│  Gross Earnings:        ₹3,500.00                           │
│  TDS Deducted (10%):   −₹350.00                            │
│  ─────────────────────────────────                         │
│  Net Paid to You:       ₹3,150.00                           │
│                                                              │
│  TDS Certificate (Form 16A) issued quarterly.              │
│  [Download TDS Certificate]                                 │
└──────────────────────────────────────────────────────────────┘
```

---

## Admin TDS Dashboard (Admin → Revenue → TDS)

```
┌──────────────────────────────────────────────────────────────┐
│  TDS MANAGEMENT — FY 2025-26                                │
│                                                              │
│  Total TDS deducted this quarter:  ₹12,450                 │
│  TDS deposited to govt:            ₹8,200  ✓               │
│  Pending deposit:                  ₹4,250  ⚠               │
│                                                              │
│  DJ-wise TDS Summary:                                       │
│  DJ Name    Annual Paid   TDS Deducted   Form 16A          │
│  ─────────────────────────────────────────────────         │
│  DJ Rohit   ₹45,000       ₹4,500         [Generate]        │
│  DJ Priya   ₹28,000       ₹0 (below threshold)             │
│                                                              │
│  [Export TDS Report]  [Mark Deposit Filed]                 │
└──────────────────────────────────────────────────────────────┘
```

---

## DB Schema

```sql
ALTER TABLE profiles
  ADD COLUMN pan_number VARCHAR(10),
  ADD COLUMN pan_verified BOOLEAN DEFAULT FALSE,
  ADD COLUMN pan_added_at TIMESTAMPTZ;

CREATE TABLE tds_records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  dj_id UUID REFERENCES profiles(id),
  payout_id UUID REFERENCES payouts(id),
  financial_year VARCHAR(10),  -- e.g. '2025-26'
  gross_amount INTEGER,
  tds_amount INTEGER,
  tds_rate DECIMAL(5,4),
  deposited_to_govt BOOLEAN DEFAULT FALSE,
  deposited_at TIMESTAMPTZ,
  form_16a_generated BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---
---

# IMPROVEMENT 05 — SESSION MANAGEMENT

## User-Facing Sessions Page

### Location: Profile Settings → Security → Active Sessions

```
┌──────────────────────────────────────────────────────────────┐
│  Active Sessions                                             │
│                                                              │
│  ● This device  (Chrome · Windows · Mumbai)    NOW          │
│    Last active: Just now                                    │
│                                                              │
│  ○ iPhone 14    (Safari · iOS · Delhi)                      │
│    Last active: 2 hours ago               [Log Out]        │
│                                                              │
│  ○ Unknown      (Firefox · Linux · Bengaluru)               │
│    Last active: 3 days ago                [Log Out]        │
│                                                              │
│  [Log Out All Other Sessions]                               │
│                                                              │
│  If you don't recognise a session, log it out              │
│  and change your password immediately.                      │
└──────────────────────────────────────────────────────────────┘
```

---

## Implementation

```python
import user_agents

class UserSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user_id = models.UUIDField()
    session_token_hash = models.CharField(max_length=64)
    ip_address = models.GenericIPAddressField()
    device_type = models.CharField(max_length=20)
    browser = models.CharField(max_length=50)
    os = models.CharField(max_length=50)
    city = models.CharField(max_length=100, null=True)
    is_current = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_active_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)


def create_session(request, user_id):
    ua_string = request.META.get('HTTP_USER_AGENT', '')
    ua = user_agents.parse(ua_string)
    ip = get_client_ip(request)

    session = UserSession.objects.create(
        user_id=user_id,
        session_token_hash=hash_token(request.session.session_key),
        ip_address=ip,
        device_type='mobile' if ua.is_mobile else 'desktop',
        browser=ua.browser.family,
        os=ua.os.family,
        city=get_city_from_ip(ip),  # Using free IP geolocation
        is_current=True
    )
    return session


def logout_session(session_id, requesting_user_id):
    session = UserSession.objects.get(
        id=session_id,
        user_id=requesting_user_id  # Can only logout own sessions
    )
    session.is_active = False
    session.save()
    # Invalidate the actual Django/Supabase session


def logout_all_other_sessions(user_id, current_session_id):
    UserSession.objects.filter(
        user_id=user_id,
        is_active=True
    ).exclude(id=current_session_id).update(is_active=False)
```

---

## Admin Force-Logout

In Admin → Security → User detail:

```
[Force Logout All Sessions]
```

Immediately invalidates all active sessions for that user. Used when:
- Account is frozen
- Suspicious activity detected
- User requests it via support

---
---

# IMPROVEMENT 06 — DJ VERIFIED BADGE SYSTEM

## Verification Criteria (Admin-Defined)

Add to Admin → Platform Controls → Verification Criteria:

```
┌──────────────────────────────────────────────────────────────┐
│  VERIFIED DJ BADGE CRITERIA                                 │
│                                                              │
│  Auto-qualify threshold (admin can override per DJ):        │
│                                                              │
│  Minimum tracks uploaded:     [ 5  ]                       │
│  Minimum total sales:         [ 20 ]                       │
│  Minimum months on platform:  [ 1  ]                       │
│  Identity verification:       [ Required ✓ ]               │
│  No active disputes:          [ Required ✓ ]               │
│  No content violations:       [ Required ✓ ]               │
│                                                              │
│  Verification method:                                       │
│  ● Admin manual review (DJ applies, admin decides)         │
│  ○ Auto-grant when all criteria met                        │
│                                                              │
│  Badge meaning shown to buyers:                            │
│  [ Identity verified by MixMint team      ]                │
│                                                              │
│  [Save Criteria]                                           │
└──────────────────────────────────────────────────────────────┘
```

---

## DJ Application for Verified Badge

### Entry: DJ Dashboard → Profile → Apply for Verified Badge

```
┌──────────────────────────────────────────────────────────────┐
│  Apply for Verified DJ Badge ✦                              │
│                                                              │
│  The Verified badge shows buyers your identity has been     │
│  confirmed by MixMint.                                      │
│                                                              │
│  Requirements:                                              │
│  ✓ 5+ tracks uploaded          [You have: 12]              │
│  ✓ 20+ sales                   [You have: 34]              │
│  ✓ 1+ months on platform       [You have: 3 months]        │
│  ✗ Identity not yet verified   [Required]                   │
│                                                              │
│  Identity Verification:                                     │
│  Upload a government-issued ID (Aadhaar / PAN card)        │
│  [Upload ID — stored securely, never shown publicly]        │
│                                                              │
│  Social proof (optional — speeds up review):               │
│  Instagram: [                    ]                          │
│  YouTube:   [                    ]                          │
│                                                              │
│  [Submit Verification Request]                              │
│                                                              │
│  Review typically takes 2–3 business days.                 │
└──────────────────────────────────────────────────────────────┘
```

---

## Revocation Rules

```
Badge revoked automatically if:
  - Active copyright strike upheld by admin
  - Account frozen for fraud
  - 3+ upheld buyer disputes within 90 days

Badge revoked manually by admin:
  - Any serious platform violation
  - Identity document found fraudulent

On revocation:
  - Badge removed from storefront immediately
  - DJ notified by email with reason
  - Can reapply after 90-day cooling period (admin-set)
```

---
---


# ═══════════════════════════════════════════════════
# SECTION E — CRITICAL INFRASTRUCTURE GAPS
# ═══════════════════════════════════════════════════
# GAP 02 — SUPABASE API LOCKDOWN

## The Problem

Supabase exposes a REST API at `https://[project].supabase.co/rest/v1/`.
If your `anon` key is in the frontend (which is default in most setups),
anyone can query your database directly — bypassing Django entirely.

---

## Architecture Rule: Server-Side Only DB Access

```
WRONG (current likely setup):
  Frontend → Supabase REST API directly
  Frontend has anon key in JavaScript

CORRECT:
  Frontend → Django API → Supabase/PostgreSQL
  Only Django has DB credentials
  Frontend never touches Supabase directly (except auth)
```

---

## Step 1 — Audit What's Currently in Frontend

Search your entire frontend codebase for:
```bash
grep -r "supabase" src/ --include="*.js" --include="*.jsx" --include="*.ts"
grep -r "NEXT_PUBLIC_SUPABASE" .env*
grep -r "createClient" src/
```

Every `createClient` call in frontend code is a potential exposure point.

---

## Step 2 — Lock Down What Frontend Can Use

```javascript
// ALLOWED in frontend — Auth only
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
)

// Frontend can ONLY use:
supabase.auth.signIn()
supabase.auth.signUp()
supabase.auth.signOut()
supabase.auth.getSession()
supabase.auth.onAuthStateChange()

// Frontend can NEVER use:
supabase.from('tracks').select()      // ← MUST go through Django
supabase.from('purchases').insert()   // ← MUST go through Django
supabase.storage.from('bucket')       // ← MUST go through Django
```

---

## Step 3 — Restrict Anon Key Permissions

In Supabase Dashboard → Authentication → Policies:

```sql
-- Anon key should be able to do NOTHING except auth
-- All tables: deny anon access completely

-- Verify no table allows anon SELECT
SELECT schemaname, tablename, policyname, roles
FROM pg_policies
WHERE 'anon' = ANY(roles);
-- This should return ZERO rows for your data tables
```

---

## Step 4 — Django Uses Service Role Key (Server-Side Only)

```python
# settings.py — NEVER expose these to frontend
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')
# Service key = full DB access = server-side ONLY

# .env (never committed to git)
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGci...  # service_role key
SUPABASE_ANON_KEY=eyJhbGci...    # Only for frontend auth
```

---

## Step 5 — JWT Verification in Django

When a user makes a request to Django, verify their Supabase JWT:

```python
import jwt
from django.conf import settings

def verify_supabase_jwt(token):
    """
    Verify the JWT from Supabase auth on every request.
    Extract user_id and role.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,  # from Supabase dashboard
            algorithms=['HS256'],
            audience='authenticated'
        )
        return {
            'user_id': payload['sub'],
            'email': payload.get('email'),
            'role': payload.get('user_metadata', {}).get('role', 'user')
        }
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token expired")
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid token")


class SupabaseAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            try:
                user_data = verify_supabase_jwt(token)
                request.user_id = user_data['user_id']
                request.user_role = user_data['role']
                request.user_email = user_data['email']
                request.is_authenticated = True
            except AuthenticationError:
                request.is_authenticated = False
        else:
            request.is_authenticated = False

        return self.get_response(request)
```

---

## Step 6 — Environment Variable Audit

```bash
# These should NEVER be in frontend env vars:
SUPABASE_SERVICE_KEY       ← backend only
DATABASE_URL               ← backend only
DJANGO_SECRET_KEY          ← backend only
R2_SECRET_ACCESS_KEY       ← backend only
RAZORPAY_KEY_SECRET        ← backend only
PHONEPE_SALT_KEY           ← backend only

# These CAN be in frontend (NEXT_PUBLIC_ prefix):
NEXT_PUBLIC_SUPABASE_URL          ← needed for auth
NEXT_PUBLIC_SUPABASE_ANON_KEY     ← needed for auth only
NEXT_PUBLIC_API_BASE_URL          ← your Django API URL
NEXT_PUBLIC_ADSENSE_PUBLISHER_ID  ← public anyway
```

---
---

# GAP 03 — LARGE FILE DELIVERY ARCHITECTURE

## The Core Problem

Vercel serverless functions have:
- 4.5MB response body limit (Hobby plan)
- 50MB on Pro plan
- 10 second timeout on Hobby, 60s on Pro
- A 500MB ZIP album = immediate failure

**You cannot proxy large files through Vercel Django.**

---

## Solution: Cloudflare Worker as Download Proxy

Replace Django download proxy with a **Cloudflare Worker** that:
1. Receives download request with token
2. Validates token against your API (fast call)
3. Streams file directly from R2 to user
4. Never goes through Vercel

```
Current (broken for large files):
  User → Vercel/Django → R2 → Django → User  ← 4.5MB limit

Correct:
  User → Cloudflare Worker → [validate token via Django API] → R2 → User
  ↑ No size limit, R2 to user is direct, Cloudflare handles streaming
```

---

## Cloudflare Worker Implementation

```javascript
// worker.js — deployed as Cloudflare Worker

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // Only handle download requests
    if (!url.pathname.startsWith('/download/')) {
      return new Response('Not found', { status: 404 });
    }

    const tokenId = url.pathname.split('/download/')[1];
    if (!tokenId) {
      return new Response('Missing token', { status: 400 });
    }

    // Step 1: Validate token with Django API
    const clientIP = request.headers.get('CF-Connecting-IP');
    const deviceFingerprint = request.headers.get('X-Device-Fingerprint');

    const validationResponse = await fetch(
      `${env.DJANGO_API_URL}/api/download/validate/`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Worker-Secret': env.WORKER_SECRET  // shared secret
        },
        body: JSON.stringify({
          token_id: tokenId,
          client_ip: clientIP,
          device_fingerprint: deviceFingerprint
        })
      }
    );

    if (!validationResponse.ok) {
      const error = await validationResponse.json();
      return new Response(
        JSON.stringify({ error: error.message }),
        {
          status: validationResponse.status,
          headers: { 'Content-Type': 'application/json' }
        }
      );
    }

    const { file_key, filename, file_size } = await validationResponse.json();

    // Step 2: Stream file directly from R2
    const r2Object = await env.MIXMINT_PRIVATE.get(file_key);

    if (!r2Object) {
      // File missing from R2 — alert admin
      await fetch(`${env.DJANGO_API_URL}/api/admin/alert/missing-file/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Worker-Secret': env.WORKER_SECRET
        },
        body: JSON.stringify({ token_id: tokenId, file_key })
      });
      return new Response('File not found', { status: 404 });
    }

    // Step 3: Mark download as started in Django (async — don't wait)
    fetch(`${env.DJANGO_API_URL}/api/download/started/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Worker-Secret': env.WORKER_SECRET
      },
      body: JSON.stringify({ token_id: tokenId })
    });

    // Step 4: Stream to user
    const headers = new Headers({
      'Content-Type': r2Object.httpMetadata?.contentType || 'audio/mpeg',
      'Content-Disposition': `attachment; filename="${filename}"`,
      'Content-Length': file_size.toString(),
      'Cache-Control': 'no-store, no-cache',
      'X-Content-Type-Options': 'nosniff',
      // Never expose R2 URL or internal paths
    });

    return new Response(r2Object.body, { headers });
  }
};
```

---

## Django — Token Validation Endpoint (Called by Worker)

```python
@csrf_exempt
@require_worker_secret  # Validates X-Worker-Secret header
def validate_download_token(request):
    """
    Called by Cloudflare Worker before serving file.
    Validates token, marks as used, returns file_key.
    """
    data = json.loads(request.body)
    token_id = data['token_id']
    client_ip = data['client_ip']
    device_fp = data['device_fingerprint']

    with transaction.atomic():
        try:
            token = DownloadToken.objects.select_for_update().get(
                id=token_id,
                used=False,
                expires_at__gt=timezone.now()
            )
        except DownloadToken.DoesNotExist:
            return JsonResponse(
                {'message': 'Token invalid, expired, or already used'},
                status=401
            )

        # Validate IP binding
        if token.client_ip != client_ip:
            log_token_ip_mismatch(token_id, client_ip)
            return JsonResponse(
                {'message': 'Access from different network detected'},
                status=403
            )

        # Mark token as used atomically
        token.used = True
        token.used_at = timezone.now()
        token.save()

        # Increment attempt counter
        purchase = token.purchase
        purchase.download_attempts += 1
        purchase.save()

    return JsonResponse({
        'file_key': token.file_key,
        'filename': token.filename,
        'file_size': token.file_size_bytes
    })
```

---

## Cloudflare Worker Config (`wrangler.toml`)

```toml
name = "mixmint-download"
main = "worker.js"
compatibility_date = "2024-01-01"

[[r2_buckets]]
binding = "MIXMINT_PRIVATE"
bucket_name = "mixmint-private"

[vars]
DJANGO_API_URL = "https://api.mixmint.site"

# Secrets (set via wrangler secret put):
# WORKER_SECRET
```

---

## Download Completion Tracking

Since download is now in Cloudflare Worker (not Django):
- Worker can't verify 100% completion reliably
- Use **EventSource / polling** from frontend instead:

```javascript
// download-tracker.js
// After download starts, poll Django every 5 seconds
// to check if file was fully received

async function trackDownload(tokenId, downloadId) {
  const interval = setInterval(async () => {
    const response = await fetch(
      `/api/download/status/?token=${tokenId}`,
      { headers: { 'Authorization': `Bearer ${getToken()}` } }
    );
    const data = await response.json();

    if (data.status === 'complete') {
      clearInterval(interval);
      showDownloadComplete();
    } else if (data.status === 'failed') {
      clearInterval(interval);
      showDownloadFailed();
    }
    // Update progress bar from data.byte_progress if available
  }, 3000);
}
```

---
---

# GAP 05 — BACKGROUND JOB SYSTEM

## Platform Decision: Vercel Cron + Supabase Edge Functions

Since you're on Vercel (serverless), you can't run Celery workers.

```
Tool                  Use case                         Frequency
───────────────────────────────────────────────────────────────────
Vercel Cron Jobs      Scheduled recurring tasks        Cron schedule
Supabase Edge Fn      Lightweight DB-triggered tasks   On DB event
Django async views    Fire-and-forget within request   Per request
```

---

## Vercel Cron Configuration (`vercel.json`)

```json
{
  "crons": [
    {
      "path": "/api/cron/process-payouts",
      "schedule": "0 9 * * 1"
    },
    {
      "path": "/api/cron/check-preview-urls",
      "schedule": "0 2 * * *"
    },
    {
      "path": "/api/cron/check-dispute-deadlines",
      "schedule": "0 * * * *"
    },
    {
      "path": "/api/cron/distribute-ad-revenue",
      "schedule": "0 10 * * 1"
    },
    {
      "path": "/api/cron/reclaim-deleted-storage",
      "schedule": "0 3 * * 0"
    },
    {
      "path": "/api/cron/check-domain-verification",
      "schedule": "*/30 * * * *"
    },
    {
      "path": "/api/cron/send-pro-trial-reminders",
      "schedule": "0 9 * * *"
    },
    {
      "path": "/api/cron/check-pro-lapses",
      "schedule": "0 * * * *"
    },
    {
      "path": "/api/cron/tds-calculations",
      "schedule": "0 4 1 * *"
    }
  ]
}
```

---

## Django Cron Endpoint Pattern

```python
# All cron endpoints follow this pattern

from functools import wraps

def cron_secret_required(view_func):
    """Ensure cron job can only be called by Vercel, not public"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        secret = request.headers.get('Authorization')
        if secret != f"Bearer {settings.CRON_SECRET}":
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper


@csrf_exempt
@cron_secret_required
def cron_process_payouts(request):
    """Runs every Monday 9am"""
    try:
        results = process_weekly_payouts()
        return JsonResponse({
            'status': 'ok',
            'processed': results['count'],
            'total_paid': str(results['total'])
        })
    except Exception as e:
        logger.error(f"Payout cron failed: {e}")
        send_admin_alert("Payout cron failed", str(e))
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
```

---

## Supabase Edge Functions (DB-Triggered)

For tasks that need to fire immediately when something happens in the DB:

```typescript
// supabase/functions/on-purchase-complete/index.ts
// Triggered when download_completed = true on a purchase

import { serve } from 'https://deno.land/std/http/server.ts'

serve(async (req) => {
  const { record } = await req.json()

  // 1. Update DJ wallet
  await updateDJWallet(record)

  // 2. Update collaborator wallets
  await updateCollabWallets(record)

  // 3. Send purchase confirmation email
  await sendPurchaseEmail(record)

  // 4. Invalidate earnings cache for this DJ
  await invalidateCache(`dj_earnings_${record.dj_id}`)

  return new Response('ok')
})
```

---

## Async Tasks Within Django Request (Fire-and-Forget)

For tasks that should start immediately but don't need to complete before response:

```python
import threading

def fire_and_forget(func, *args, **kwargs):
    """Run function in background thread — use for non-critical tasks"""
    thread = threading.Thread(target=func, args=args, kwargs=kwargs)
    thread.daemon = True
    thread.start()


# Example usage: after upload validated, start metadata injection
def upload_track_view(request):
    # ... validate file ...
    track = save_track_to_db(file_data)
    upload_raw_to_r2(file, track.raw_file_key)

    # Start metadata injection without waiting
    fire_and_forget(inject_metadata_and_publish, track.id)

    return JsonResponse({
        'status': 'processing',
        'track_id': str(track.id),
        'message': 'Track uploaded. Publishing in a few minutes.'
    })
```

---

## Complete Background Job Registry

```
Job                          Tool              Schedule/Trigger
────────────────────────────────────────────────────────────────
Metadata injection           Django thread     On upload
Weekly payouts               Vercel Cron       Mon 9am
Ad revenue distribution      Vercel Cron       Mon 10am
Preview URL validation        Vercel Cron       Daily 2am
Dispute deadline check        Vercel Cron       Hourly
Storage reclaim (90d deletes) Vercel Cron       Weekly Sun 3am
Domain verification poll      Vercel Cron       Every 30min
Pro trial reminders           Vercel Cron       Daily 9am
Pro lapse checks              Vercel Cron       Hourly
TDS calculations              Vercel Cron       1st of month
Purchase complete events      Supabase Edge Fn  On DB update
DJ approval events            Supabase Edge Fn  On DB update
Download complete events      Supabase Edge Fn  On DB update
```

---
---

# GAP 06 — DJ USERNAME / URL SLUG SYSTEM

## Username Rules

```python
import re

USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 30

# Allowed: lowercase letters, numbers, hyphens
# No: spaces, special chars, underscores, uppercase
USERNAME_PATTERN = re.compile(r'^[a-z0-9][a-z0-9-]{1,28}[a-z0-9]$')

# Reserved words — cannot be used as usernames
RESERVED_USERNAMES = [
    'admin', 'api', 'login', 'logout', 'signup', 'register',
    'search', 'browse', 'pro', 'security', 'legal', 'terms',
    'privacy', 'support', 'help', 'track', 'album', 'bundle',
    'dj', 'djs', 'artist', 'artists', 'library', 'checkout',
    'download', 'settings', 'profile', 'dashboard', 'panel',
    'widget', 'embed', 'sitemap', 'robots', 'favicon', 'static',
    'media', 'assets', 'blog', 'updates', 'changelog', 'waitlist',
    'early-access', 'join', 'invite', 'referral', 'ambassador',
    'mixmint', 'www', 'mail', 'email', 'contact', 'about',
    'pricing', 'careers', 'press', 'investor', 'offical',
]

def validate_username(username):
    username = username.lower().strip()

    if len(username) < USERNAME_MIN_LENGTH:
        return False, f"Username must be at least {USERNAME_MIN_LENGTH} characters"

    if len(username) > USERNAME_MAX_LENGTH:
        return False, f"Username must be under {USERNAME_MAX_LENGTH} characters"

    if not USERNAME_PATTERN.match(username):
        return False, "Username can only contain lowercase letters, numbers, and hyphens"

    if username in RESERVED_USERNAMES:
        return False, "This username is reserved. Please choose another."

    if username.startswith('-') or username.endswith('-'):
        return False, "Username cannot start or end with a hyphen"

    if '--' in username:
        return False, "Username cannot contain consecutive hyphens"

    if Profile.objects.filter(username=username).exists():
        return False, "This username is already taken"

    return True, None
```

---

## Username Selection (DJ Application Form)

Add to DJ application form:

```
┌──────────────────────────────────────────────────────────────┐
│  Choose your MixMint URL                                    │
│                                                              │
│  mixmint.site/dj/ [ rohit-beats        ]                   │
│                   ✓ Available                               │
│                                                              │
│  · Lowercase letters, numbers, and hyphens only            │
│  · 3–30 characters                                          │
│  · Cannot be changed after approval                        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Live availability check** as DJ types (300ms debounce):
```javascript
// Check availability via API
const checkUsername = debounce(async (username) => {
  const res = await fetch(`/api/dj/username/check/?u=${username}`);
  const data = await res.json();
  showAvailabilityStatus(data.available, data.message);
}, 300);
```

---

## Username Change Policy

```
Can username be changed?    NO — fixed on approval
Why:                        All external links, custom domains,
                            Google indexing, buyer bookmarks break
                            if username changes

Exception:                  Admin can change username for:
                            - Trademark dispute
                            - Harassment/impersonation
                            - Technical error during registration

If admin changes username:
  - Old username redirects to new for 90 days (301 redirect)
  - DJ notified immediately with new URL
  - Custom domain re-verification required
```

---

## Deleted DJ Username Handling

```python
def handle_dj_account_deletion(dj_id):
    profile = Profile.objects.get(id=dj_id)

    # Reserve the username for 12 months — prevent immediate reclaim
    # (protects buyers who bookmarked the URL)
    ReservedUsername.objects.create(
        username=profile.username,
        reserved_until=timezone.now() + timedelta(days=365),
        reason='account_deleted'
    )

    # Set up redirect for 12 months
    StorefrontRedirect.objects.create(
        from_username=profile.username,
        redirect_to='/browse',  # Or a "DJ no longer on MixMint" page
        expires_at=timezone.now() + timedelta(days=365)
    )
```

---

## DB Schema

```sql
ALTER TABLE profiles
  ADD COLUMN username VARCHAR(30) UNIQUE,
  ADD COLUMN username_set_at TIMESTAMPTZ;

CREATE TABLE reserved_usernames (
  username VARCHAR(30) PRIMARY KEY,
  reserved_until TIMESTAMPTZ,
  reason VARCHAR(50)
);

CREATE TABLE storefront_redirects (
  from_username VARCHAR(30) PRIMARY KEY,
  redirect_to VARCHAR(500),
  expires_at TIMESTAMPTZ
);
```

---
---

# GAP 07 — TWO-BUCKET R2 STRATEGY

## The Problem
Currently all R2 content is private. But track artwork, DJ avatars, and banners need to be publicly accessible for:
- OG tags (WhatsApp/Instagram share previews)
- Search result images
- Fast page loads without proxy overhead
- Sitemap image references

Serving public images through Django proxy = unnecessary load and latency.

---

## Two Bucket Architecture

```
mixmint-private (private bucket):
  audio files/           ← track MP3/WAV/ZIP files
  invoices/              ← PDF invoices
  exports/               ← user data exports
  archive/               ← soft-deleted content

mixmint-public (public bucket, Cloudflare CDN):
  artwork/               ← track/album artwork
  avatars/               ← DJ profile photos
  banners/               ← DJ storefront banners
  thumbnails/            ← auto-generated smaller versions
```

---

## Cloudflare R2 Public Bucket Setup

```
In Cloudflare R2 Dashboard:
1. Create bucket: mixmint-public
2. Settings → Public Access → Enable
3. Custom domain: cdn.mixmint.site → R2 public bucket
4. Cloudflare handles CDN caching automatically
```

---

## Upload Routing Logic

```python
import boto3

# Two separate R2 clients
r2_private = boto3.client(
    's3',
    endpoint_url=settings.R2_PRIVATE_ENDPOINT,
    aws_access_key_id=settings.R2_PRIVATE_ACCESS_KEY,
    aws_secret_access_key=settings.R2_PRIVATE_SECRET_KEY,
)

r2_public = boto3.client(
    's3',
    endpoint_url=settings.R2_PUBLIC_ENDPOINT,
    aws_access_key_id=settings.R2_PUBLIC_ACCESS_KEY,
    aws_secret_access_key=settings.R2_PUBLIC_SECRET_KEY,
)


def upload_file(file_data, key, file_type):
    """Route to correct bucket based on file type"""

    PUBLIC_TYPES = ['artwork', 'avatar', 'banner', 'thumbnail']
    PRIVATE_TYPES = ['audio', 'zip', 'invoice', 'export']

    if file_type in PUBLIC_TYPES:
        r2_public.put_object(
            Bucket=settings.R2_PUBLIC_BUCKET,
            Key=key,
            Body=file_data,
            ContentType=get_content_type(file_type),
            CacheControl='public, max-age=31536000'  # 1 year cache
        )
        return f"https://cdn.mixmint.site/{key}"

    elif file_type in PRIVATE_TYPES:
        r2_private.put_object(
            Bucket=settings.R2_PRIVATE_BUCKET,
            Key=key,
            Body=file_data,
            ContentType=get_content_type(file_type)
        )
        return f"private:{key}"  # Internal reference only, never a URL

    else:
        raise ValueError(f"Unknown file type: {file_type}")
```

---

## Image Processing on Upload

```python
from PIL import Image
from io import BytesIO

def process_and_upload_artwork(image_file, track_id):
    """
    Resize to standard sizes and upload all variants to public bucket
    """
    img = Image.open(image_file)

    # Enforce square artwork
    width, height = img.size
    if width != height:
        # Crop to square from center
        min_dim = min(width, height)
        left = (width - min_dim) // 2
        top = (height - min_dim) // 2
        img = img.crop((left, top, left + min_dim, top + min_dim))

    sizes = {
        'original': 1000,  # Full size
        'medium': 400,     # Card display
        'small': 150,      # Search results, thumbnails
        'og': 1200,        # Open Graph (OG) — wider crop
    }

    urls = {}
    for size_name, px in sizes.items():
        resized = img.copy()
        resized.thumbnail((px, px), Image.LANCZOS)

        buffer = BytesIO()
        resized.save(buffer, format='WEBP', quality=85)
        buffer.seek(0)

        key = f"artwork/{track_id}/{size_name}.webp"
        url = upload_file(buffer.read(), key, 'artwork')
        urls[size_name] = url

    return urls  # Store all URLs in track record
```

---

## DB Schema Updates

```sql
ALTER TABLE tracks
  ADD COLUMN artwork_url_original VARCHAR(500),
  ADD COLUMN artwork_url_medium VARCHAR(500),
  ADD COLUMN artwork_url_small VARCHAR(500),
  ADD COLUMN artwork_url_og VARCHAR(500);

ALTER TABLE profiles
  ADD COLUMN avatar_url_original VARCHAR(500),
  ADD COLUMN avatar_url_medium VARCHAR(500),
  ADD COLUMN banner_url VARCHAR(500);
```

---
---

# GAP 08 — SEARCH INFRASTRUCTURE

## Tool: PostgreSQL Full-Text Search via Supabase

Supabase runs PostgreSQL — use built-in `tsvector` full-text search + `pg_trgm` for fuzzy matching. No external search service needed at launch scale.

---

## Step 1 — Enable Extensions

```sql
-- Run in Supabase SQL Editor
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
```

---

## Step 2 — Add Search Vectors to Tracks Table

```sql
-- Add tsvector column
ALTER TABLE tracks ADD COLUMN search_vector tsvector;

-- Populate existing rows
UPDATE tracks SET search_vector =
  setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
  setweight(to_tsvector('english', coalesce(dj_name, '')), 'B') ||
  setweight(to_tsvector('english', coalesce(genre, '')), 'C') ||
  setweight(to_tsvector('english', coalesce(description, '')), 'D');

-- Create GIN index for fast full-text search
CREATE INDEX tracks_search_idx ON tracks USING GIN(search_vector);

-- Create trigram index for fuzzy matching
CREATE INDEX tracks_title_trgm_idx ON tracks
  USING GIN(title gin_trgm_ops);
CREATE INDEX tracks_dj_name_trgm_idx ON tracks
  USING GIN(dj_name gin_trgm_ops);

-- Auto-update search_vector on insert/update
CREATE OR REPLACE FUNCTION update_track_search_vector()
RETURNS TRIGGER AS $$
BEGIN
  NEW.search_vector :=
    setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(NEW.dj_name, '')), 'B') ||
    setweight(to_tsvector('english', coalesce(NEW.genre, '')), 'C') ||
    setweight(to_tsvector('english', coalesce(NEW.description, '')), 'D');
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tracks_search_vector_update
  BEFORE INSERT OR UPDATE ON tracks
  FOR EACH ROW EXECUTE FUNCTION update_track_search_vector();
```

---

## Step 3 — Django Search Query

```python
from django.db import connection

def search_tracks(query, filters=None, page=1, per_page=20):
    """
    Combines full-text search + fuzzy matching + ranking formula
    """
    query = query.strip()
    offset = (page - 1) * per_page

    if not query:
        # No query — return latest tracks
        return Track.objects.filter(
            is_active=True, is_deleted=False, file_status='ready'
        ).order_by('-created_at')[offset:offset + per_page]

    # Build SQL with ranking
    sql = """
        SELECT
            t.*,
            -- Full-text relevance
            ts_rank(t.search_vector, plainto_tsquery('english', %s)) AS fts_rank,
            -- Fuzzy similarity on title
            similarity(t.title, %s) AS title_similarity,
            -- Combined score
            (
                ts_rank(t.search_vector, plainto_tsquery('english', %s)) * 40 +
                similarity(t.title, %s) * 20 +
                CASE WHEN t.is_pro_dj THEN 15 ELSE 0 END +
                CASE WHEN t.is_verified_dj THEN 5 ELSE 0 END +
                LEAST(t.sales_last_30_days * 2, 20) +
                GREATEST(0, 20 - (EXTRACT(DAY FROM NOW() - t.created_at) / 7))
            ) AS total_score
        FROM tracks t
        WHERE
            t.is_active = TRUE AND
            t.is_deleted = FALSE AND
            t.file_status = 'ready' AND
            (
                -- Full-text match
                t.search_vector @@ plainto_tsquery('english', %s)
                OR
                -- Fuzzy match fallback (similarity > 0.2)
                similarity(t.title, %s) > 0.2
                OR
                similarity(t.dj_name, %s) > 0.3
            )
        ORDER BY total_score DESC, t.created_at DESC
        LIMIT %s OFFSET %s
    """

    params = [
        query, query, query, query,  # ranking params
        query, query, query,          # WHERE params
        per_page, offset
    ]

    # Apply filters
    if filters:
        if filters.get('genre'):
            sql = sql.replace(
                'ORDER BY',
                f"AND t.genre = '{filters['genre']}'\n        ORDER BY"
            )
        if filters.get('price_max'):
            sql = sql.replace(
                'ORDER BY',
                f"AND t.price <= {filters['price_max'] * 100}\n        ORDER BY"
            )

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        columns = [col[0] for col in cursor.description]
        results = [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]

    return results


def search_djs(query):
    """Separate search for DJs — used in DJ directory"""
    return Profile.objects.filter(
        role__in=['dj'],
        store_paused=False,
        is_deleted=False
    ).filter(
        Q(display_name__trigram_similar=query) |
        Q(username__trigram_similar=query) |
        Q(genre_tags__contains=[query])
    ).order_by('-is_pro_dj', '-is_verified', '-total_sales')
```

---

## Step 4 — Search API Endpoint

```python
@ratelimit(key='ip', rate='30/m', block=True)
def search_api(request):
    query = request.GET.get('q', '').strip()
    genre = request.GET.get('genre', '')
    price_max = request.GET.get('price_max')
    sort = request.GET.get('sort', 'relevance')
    page = int(request.GET.get('page', 1))

    filters = {}
    if genre:
        filters['genre'] = genre
    if price_max:
        try:
            filters['price_max'] = int(price_max)
        except ValueError:
            pass

    tracks = search_tracks(query, filters=filters, page=page)

    return JsonResponse({
        'query': query,
        'results': [serialize_track(t) for t in tracks],
        'page': page,
        'has_more': len(tracks) == 20
    })
```

---
---

# GAP 10 — FILE FORMAT STANDARDS

## Accepted Formats + Validation Rules

```
Format    MIME Type           Max Size    Min Bitrate   Notes
────────────────────────────────────────────────────────────────────
MP3       audio/mpeg          150 MB      192 kbps      Most common
WAV       audio/wav           300 MB      N/A (lossless) Large files
FLAC      audio/flac          300 MB      N/A (lossless) Audiophile
AIFF      audio/aiff          300 MB      N/A (lossless) Mac-native
ZIP       application/zip     500 MB      —             Albums only
```

---

## Audio Integrity Validation

Don't just check MIME type — validate the audio is actually playable:

```python
import subprocess
import json

def validate_audio_integrity(file_path):
    """
    Use ffprobe to validate audio file is not corrupt
    and meets quality standards
    """
    try:
        result = subprocess.run([
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            file_path
        ], capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            return False, "File appears to be corrupt or unreadable"

        data = json.loads(result.stdout)
        streams = data.get('streams', [])
        fmt = data.get('format', {})

        # Check there's at least one audio stream
        audio_streams = [s for s in streams if s.get('codec_type') == 'audio']
        if not audio_streams:
            return False, "No audio stream found in file"

        audio = audio_streams[0]

        # Check duration (must be at least 30 seconds)
        duration = float(fmt.get('duration', 0))
        if duration < 30:
            return False, f"Track too short ({int(duration)}s). Minimum 30 seconds."

        if duration > 7200:  # 2 hours max
            return False, "Track too long. Maximum 2 hours."

        # Check bitrate for MP3
        codec = audio.get('codec_name', '')
        if codec == 'mp3':
            bit_rate = int(audio.get('bit_rate', 0))
            if bit_rate < 192000:  # 192 kbps
                return False, (
                    f"MP3 quality too low ({bit_rate//1000} kbps). "
                    f"Minimum 192 kbps required. "
                    f"Please export at 320 kbps for best results."
                )

        return True, {
            'duration_seconds': int(duration),
            'codec': codec,
            'bit_rate': int(audio.get('bit_rate', 0)),
            'sample_rate': int(audio.get('sample_rate', 0)),
            'channels': audio.get('channels', 0)
        }

    except subprocess.TimeoutExpired:
        return False, "File validation timed out. File may be corrupt."
    except Exception as e:
        return False, f"Validation error: {str(e)}"
```

---

## Format + Quality Info Shown to Buyers

On track detail page, below price:

```
MP3 · 320 kbps · 6:42
```

Or for WAV/FLAC:
```
WAV · Lossless · 6:42
```

- Format badge: DM Mono 12px, muted
- Shows to buyers so they know what they're buying
- Stored in track metadata at upload time

---

## Upload UI — Format Requirements

In DJ upload form, below file picker:

```
Accepted formats: MP3 (min 192 kbps), WAV, FLAC, AIFF
Maximum size: 150 MB (single track) · 500 MB (album ZIP)
Minimum length: 30 seconds

For best results: Export MP3 at 320 kbps or upload WAV/FLAC.
Tracks below 192 kbps will be rejected.
```

---

## DB Schema

```sql
ALTER TABLE tracks
  ADD COLUMN file_format VARCHAR(10),    -- 'mp3' | 'wav' | 'flac' | 'aiff'
  ADD COLUMN file_bitrate INTEGER,       -- in bps (e.g. 320000)
  ADD COLUMN file_sample_rate INTEGER,   -- e.g. 44100
  ADD COLUMN file_channels INTEGER,      -- 1=mono, 2=stereo
  ADD COLUMN duration_seconds INTEGER,
  ADD COLUMN file_size_bytes BIGINT;
```

---
---

# GAP 20 — DUPLICATE PURCHASE GUARD

## The Problem

Two simultaneous requests can both:
1. Check "does user own this?" → both see NO
2. Both proceed to create payment orders
3. Both succeed → user charged twice

---

## DB-Level Constraint

```sql
-- Prevent duplicate active purchases at DB level
-- This is your last line of defense

CREATE UNIQUE INDEX unique_active_purchase
  ON purchases(user_id, content_id)
  WHERE status NOT IN ('refunded', 'failed');

-- This means: one user can only have ONE non-refunded
-- purchase per content item. Period. DB enforces it.
-- Even if application logic fails, DB catches it.
```

---

## Application-Level Guard (Before Payment)

```python
def create_payment_order(request, content_id):
    user_id = request.user_id

    # Check for existing active purchase (race-condition safe)
    existing = Purchase.objects.filter(
        user_id=user_id,
        content_id=content_id,
        status__in=['active', 'pending']
    ).first()

    if existing:
        if existing.status == 'active':
            return JsonResponse({
                'error': 'already_owned',
                'message': 'You already own this track. Find it in your Library.',
                'library_url': '/library'
            }, status=409)
        elif existing.status == 'pending':
            # Payment in progress — return existing order
            return JsonResponse({
                'error': 'payment_in_progress',
                'message': 'A payment for this track is already in progress.',
                'order_id': str(existing.gateway_order_id)
            }, status=409)

    # Create payment order
    track = get_object_or_404(Track, id=content_id, is_active=True)
    price = calculate_buyer_price(track)

    # Create pending purchase record BEFORE creating gateway order
    # This acts as a distributed lock
    try:
        purchase = Purchase.objects.create(
            user_id=user_id,
            content_id=content_id,
            dj_id=track.dj_id,
            original_price=price,
            status='pending',
            payment_gateway=settings.ACTIVE_PAYMENT_GATEWAY
        )
    except IntegrityError:
        # Unique constraint caught a race condition
        return JsonResponse({
            'error': 'already_owned',
            'message': 'You already own this track.'
        }, status=409)

    # Now create gateway order
    gateway = get_active_gateway()
    order = gateway.create_order(amount=price, metadata={
        'purchase_id': str(purchase.id),
        'user_id': str(user_id),
        'content_id': str(content_id)
    })

    purchase.gateway_order_id = order['id']
    purchase.save()

    return JsonResponse({'order': order})
```

---

## Frontend Guard

```javascript
// Disable buy button immediately on click to prevent double-clicks

let purchaseInProgress = false;

buyButton.addEventListener('click', async () => {
  if (purchaseInProgress) return;  // Prevent double-click
  purchaseInProgress = true;
  buyButton.disabled = true;
  buyButton.textContent = 'Processing...';

  try {
    await initiateCheckout(trackId);
  } catch (error) {
    if (error.code === 'already_owned') {
      showAlreadyOwnedMessage();
    }
    // Re-enable only on error — success navigates away
    purchaseInProgress = false;
    buyButton.disabled = false;
    buyButton.textContent = 'Buy & Download';
  }
});
```

---

## Failed Payment Cleanup

```python
# Cron: runs hourly — clean up stuck pending purchases

def cleanup_stuck_pending_purchases():
    """
    Purchases stuck in 'pending' for over 2 hours
    = payment was abandoned. Safe to cancel.
    """
    cutoff = timezone.now() - timedelta(hours=2)
    stuck = Purchase.objects.filter(
        status='pending',
        created_at__lt=cutoff
    )
    count = stuck.update(status='failed')
    logger.info(f"Cleaned up {count} stuck pending purchases")
```

---

*End of Part 1 — Critical Infrastructure Gaps*
*Ad System · Supabase Lockdown · Large File Delivery*
*Background Jobs · Username System · Two-Bucket R2*
*Search Infrastructure · Notifications · File Standards · Duplicate Guard*

---

# 🔧 MIXMINT — FINAL GAPS PROMPT PART 2
### *Medium Priority + Polish Gaps*
### *Covers: #11 Email Unsubscribe · #12 Custom Domain SEO · #13 Buyer Profile · #14 Changelog · #15 Error Pages · #16 Loading States · #17 Price Formatting · #18 Tab Titles · #19 Favicon · Plus: Admin Revenue Input, Notification Preferences, Platform Copy Standards*

---


# ═══════════════════════════════════════════════════
# SECTION F — TESTING, DEBUG & QA
# ═══════════════════════════════════════════════════
### *Full-stack QA: Every flow, every role, every edge case. Find it. Fix it.*

---

## 🎯 TESTING PHILOSOPHY

This is not a checklist — it is a **destructive audit**.
The goal is to break MixMint before real users do.

Test as:
1. A curious first-time visitor
2. A buyer trying to game the system
3. A DJ trying to exploit earnings
4. An admin managing a live platform
5. A bad actor trying to steal files

For every test:
- **Expected:** what should happen
- **Actual:** what actually happens
- **If broken:** root cause + exact fix

---

## 🗂️ TESTING PHASES

```
Phase 1  →  Auth & Registration
Phase 2  →  Browse & Discovery (unauthenticated)
Phase 3  →  Track & Album Pages
Phase 4  →  Checkout & Payment
Phase 5  →  Download System (core engine)
Phase 6  →  User Library
Phase 7  →  DJ Application Flow
Phase 8  →  DJ Dashboard — Full Audit
Phase 9  →  Admin Dashboard — Full Audit
Phase 10 →  Offer & Pricing System
Phase 11 →  Security & Exploit Attempts
Phase 12 →  Mobile & Responsive
Phase 13 →  Theme System (Dark/Light)
Phase 14 →  Email Notifications
Phase 15 →  Cross-browser & Performance
```

---

## PHASE 1 — AUTH & REGISTRATION

### 1.1 Email Registration

| # | Test | Expected | Common Bug |
|---|------|----------|------------|
| 1.1.1 | Register with valid email + strong password | Account created, verification email sent | Email not sent / wrong template |
| 1.1.2 | Register with temporary/disposable email (mailinator, guerrilla, tempmail) | Blocked with message: "Temporary emails not accepted" | Domain blocklist not checked |
| 1.1.3 | Register with already-used email | Error: "Account already exists" | Silent fail or 500 error |
| 1.1.4 | Register with weak password (under 8 chars, no special char) | Blocked with password requirements shown | No server-side validation |
| 1.1.5 | Register with mismatched confirm password | Inline error shown immediately | Only caught on submit |
| 1.1.6 | Submit empty form | Each required field shows error | Only first field errors |
| 1.1.7 | Email verification link — click valid link | Account verified, redirected to homepage | Token expired too fast |
| 1.1.8 | Email verification link — click expired link | Error message + resend option | 500 error or blank page |
| 1.1.9 | Try to log in before verifying email | Blocked with "Please verify your email first" | User logs in unverified |
| 1.1.10 | Resend verification email — spam it (click 5x fast) | Rate limited after 2 attempts (60s cooldown) | Sends 5 emails, no limit |

---

### 1.2 Google OAuth

| # | Test | Expected | Common Bug |
|---|------|----------|------------|
| 1.2.1 | Sign up with Google (new account) | Account created, role=user, redirected to homepage | Role not set in profiles table |
| 1.2.2 | Sign in with Google (existing account) | Logs in, session established | Duplicate profile row created |
| 1.2.3 | Google email already registered via email/password | Links accounts or shows error gracefully | Two separate accounts created |
| 1.2.4 | Cancel Google OAuth popup midway | Returns to login page cleanly | Blank page or broken state |
| 1.2.5 | Google OAuth on mobile (redirect flow vs popup) | Completes successfully | Popup blocked on mobile, no fallback |

---

### 1.3 Login

| # | Test | Expected | Common Bug |
|---|------|----------|------------|
| 1.3.1 | Login with correct credentials | Session created, redirected correctly by role | Redirects to wrong page for DJ vs user |
| 1.3.2 | Login with wrong password | Error: "Incorrect email or password" | Reveals which is wrong (security issue) |
| 1.3.3 | Login with unregistered email | Same generic error as wrong password | Different error message leaks existence |
| 1.3.4 | Brute force login (10 rapid attempts) | Account temporarily locked or CAPTCHA triggered | No rate limiting |
| 1.3.5 | Login with SQL injection in email field | Input sanitized, no DB error | Raw SQL error exposed |
| 1.3.6 | Login with XSS in password field (`<script>alert(1)</script>`) | Sanitized, no script executes | Stored XSS vulnerability |
| 1.3.7 | After login, press browser Back button | Does not go back to login page | Can navigate back to login while logged in |
| 1.3.8 | Session persistence — close browser, reopen | Session restored (if "remember me") or clean login | Session survives incognito |

---

### 1.4 Forgot Password

| # | Test | Expected | Common Bug |
|---|------|----------|------------|
| 1.4.1 | Request reset for valid email | Email sent, success message shown | Error on valid email |
| 1.4.2 | Request reset for unregistered email | Same success message (don't leak existence) | "Email not found" reveals accounts |
| 1.4.3 | Click valid reset link | Password reset form shown | Link works but token not invalidated after use |
| 1.4.4 | Use reset link twice | Second use rejected: "Link already used" | Can reset password multiple times with same link |
| 1.4.5 | Reset link after 24h | Expired message shown | Old links still work |
| 1.4.6 | Set new password same as old | Allowed (or blocked — document policy) | No validation at all |

---

### 1.5 Logout

| # | Test | Expected | Common Bug |
|---|------|----------|------------|
| 1.5.1 | Click logout | Session destroyed, redirected to homepage | Session cookie persists |
| 1.5.2 | After logout, visit /library directly | Redirected to login | Protected page accessible after logout |
| 1.5.3 | After logout, visit /dj-panel | Redirected to login | DJ dashboard accessible after logout |
| 1.5.4 | IP change during active session | Auto-logout triggered, session invalidated | IP change not detected |
| 1.5.5 | Inactive for 12 months | Account flagged/expired | Never expires |

---

## PHASE 2 — BROWSE & DISCOVERY (UNAUTHENTICATED)

| # | Test | Expected | Common Bug |
|---|------|----------|------------|
| 2.1 | Visit homepage without login | Full homepage visible, no login wall | Redirect to login |
| 2.2 | Open any track detail page without login | Full page visible, price visible, Buy button visible | Track page requires login |
| 2.3 | Open any album page without login | Full page visible | Redirect to login |
| 2.4 | Open any DJ storefront without login | Full storefront visible | Requires login |
| 2.5 | Use search bar without login | Results shown freely | Search requires login |
| 2.6 | Apply genre/price/year filters | Results filter correctly | Filters break without auth |
| 2.7 | Scroll to bottom of results | Infinite scroll loads more | Scroll triggers login wall |
| 2.8 | Search with partial spelling (e.g. "hous" for "house") | Fuzzy results returned | Only exact match works |
| 2.9 | Search with empty string | No crash, shows browse state or clears results | 500 error on empty search |
| 2.10 | Search with special characters (`<>'";&`) | Sanitized, no SQL/script injection | DB error or XSS |
| 2.11 | Click `Buy & Download` without login | Auth modal slides up | Redirect to /login (loses track context) |
| 2.12 | After logging in via auth modal | Returns to same track, purchase flow begins | Redirects to homepage losing track |

---

## PHASE 3 — TRACK & ALBUM PAGES

| # | Test | Expected | Common Bug |
|---|------|----------|------------|
| 3.1 | Visit track page with YouTube preview | YouTube embed loads correctly | CSP blocks iframe |
| 3.2 | Visit track page with Instagram preview | Instagram Reel embed loads | Instagram embed broken on some browsers |
| 3.3 | Visit track page with no preview set | "No preview available" shown, no broken embed | Broken iframe or empty space |
| 3.4 | Visit soft-deleted track URL directly | 404 or "Unavailable" page | Shows deleted track |
| 3.5 | Visit track from paused DJ store | Shows track but buy button disabled OR redirects to storefront with paused message | Buy button still works on paused store |
| 3.6 | Price shown on track page | Single clean number, no fee/GST breakdown | Shows itemized breakdown |
| 3.7 | "Inclusive of all charges" sub-label | Always present | Missing on some tracks |
| 3.8 | Responsibility disclaimer shows DJ name | Dynamically shows correct DJ name | Shows "undefined" or wrong DJ |
| 3.9 | Already-owned track — revisit page | Shows "✓ You Own This" + re-download option | Shows "Buy" again |
| 3.10 | Re-download within 2-day lock | Button disabled, shows countdown | Button enabled during lock |
| 3.11 | Re-download eligible (2 days passed) | Button shows 50% price, enabled | Still locked after 2 days |
| 3.12 | Album ZIP page — track list renders | All tracks listed with names | Empty list or [object Object] |
| 3.13 | Album ZIP size shown | Correct size (e.g. "~128 MB") | Shows 0 or NaN |
| 3.14 | Verified DJ badge appears | Only for admin-verified DJs | Shows for all DJs |

---

## PHASE 4 — CHECKOUT & PAYMENT

| # | Test | Expected | Common Bug |
|---|------|----------|------------|
| 4.1 | Checkout shows single total price | One line: "You Pay ₹49" | Shows GST/fee breakdown |
| 4.2 | "Inclusive of all charges" note present | Always visible | Missing |
| 4.3 | Price matches track detail page | Identical number | Discrepancy between pages |
| 4.4 | Active offer banner shows in checkout | Offer notice shown if admin enabled | Offer not reflected |
| 4.5 | GST disabled — no GST in total | Price unaffected by GST | GST still calculated |
| 4.6 | Platform fee disabled — no fee added | Price = track price set by DJ | Platform fee secretly added |
| 4.7 | Razorpay modal opens | Payment gateway loads | Modal fails to open |
| 4.8 | Successful payment | Redirected to download page, purchase record created | Stuck on processing |
| 4.9 | Payment cancelled by user | Returns to track page, no purchase created | Partial purchase record created |
| 4.10 | Payment fails (card declined) | Error shown, retry option | No feedback, stuck |
| 4.11 | Double-click "Proceed to Pay" | Only one payment initiated | Two charges created |
| 4.12 | Browser back during Razorpay | Handled gracefully, payment status verified | Duplicate order or orphaned payment |
| 4.13 | Webhook — payment verified | Download unlocked server-side | Frontend relies on client, backend not verified |
| 4.14 | Purchase of already-owned track | Blocked or warned before payment | Allows duplicate purchase |
| 4.15 | GST invoice generated post-purchase | Invoice available in library + emailed | Invoice not generated |
| 4.16 | Invoice contains correct breakdown | Base price, charges, total, buyer + DJ info | Wrong amounts or missing fields |

---

## PHASE 5 — DOWNLOAD SYSTEM (CORE ENGINE)

**This is the most critical phase. Test every edge.**

### 5.1 Token Generation

| # | Test | Expected | Common Bug |
|---|------|----------|------------|
| 5.1.1 | Token generated immediately after payment | Token created, download page loads | Delay or no token |
| 5.1.2 | Token is single-use | Second use rejected: "Token already used" | Token reusable |
| 5.1.3 | Token expires after 2–5 min | After expiry, download blocked with "Token expired" | Token never expires |
| 5.1.4 | Token bound to IP | Using token from different IP rejected | Token works from any IP |
| 5.1.5 | Token bound to device | Using token from different device rejected | No device binding |
| 5.1.6 | Token misuse (rapid reuse attempts) | Account frozen after threshold | No freeze triggered |
| 5.1.7 | Manual token URL manipulation | Rejected — token validation fails | Accepts manipulated token |

---

### 5.2 Download Flow

| # | Test | Expected | Common Bug |
|---|------|----------|------------|
| 5.2.1 | Click Download Now | File starts downloading via secure proxy | Direct R2 URL exposed in network tab |
| 5.2.2 | Progress bar updates | Real-time % progress shown | Stuck at 0% or jumps to 100% |
| 5.2.3 | Download speed shown | Live MB/s display | Shows NaN or 0 |
| 5.2.4 | Close tab during download | Attempt counted only if completed | Incomplete attempt counted |
| 5.2.5 | Network drops mid-download | Incomplete — eligible for retry/refund | Marked complete despite failure |
| 5.2.6 | Checksum verification | File hash verified after download | No checksum check |
| 5.2.7 | Byte count verification | 100% of bytes confirmed | Marked complete at 95% |
| 5.2.8 | Completed download → history | Appears in library | Doesn't appear until page refresh |
| 5.2.9 | Inspect network tab — check file URL | Proxied URL only, no R2 direct link | R2 URL visible |
| 5.2.10 | Download a second file after completing first | New token generated, works fine | Token from first used |

---

### 5.3 Attempt Limits

| # | Test | Expected | Common Bug |
|---|------|----------|------------|
| 5.3.1 | First download attempt | "Attempt 1 of 3" shown | Shows wrong count |
| 5.3.2 | Second attempt (incomplete first) | "Attempt 2 of 3" + amber warning shown | No warning |
| 5.3.3 | Third attempt | "🚨 Final attempt" red warning shown | No differentiation from 2nd |
| 5.3.4 | Exceed 3 attempts | Download blocked: "Attempt limit reached" | 4th attempt allowed |
| 5.3.5 | Attempt count per IP (not per account) | Same IP on different account also limited | Per-account only, IP bypass works |
| 5.3.6 | VPN switch between attempts | Registers as new IP, resets counter | Intended? Document decision. |

---

### 5.4 Device & IP Locking

| # | Test | Expected | Common Bug |
|---|------|----------|------------|
| 5.4.1 | Successful download — try re-download same device | Locked — shows 2-day countdown | Not locked |
| 5.4.2 | Successful download — try different device immediately | Blocked (IP/device lock) | Works on any device |
| 5.4.3 | After 2 days — try re-download | Re-download button enabled at 50% price | Still locked after 2 days |
| 5.4.4 | Re-download without paying 50% | Blocked — payment required | Free re-download possible |
| 5.4.5 | Grace retry on checksum fail | Retry allowed without consuming attempt | Uses attempt count |

---

## PHASE 6 — USER LIBRARY

| # | Test | Expected | Common Bug |
|---|------|----------|------------|
| 6.1 | Library shows all purchases | Complete list, correct titles + DJ names | Missing purchases |
| 6.2 | Incomplete download shows correct status | "✗ Incomplete" badge | Shows "Downloaded" incorrectly |
| 6.3 | Pending download (token active) | "⏳ Pending" badge | Shows wrong status |
| 6.4 | Re-download countdown accurate | Live countdown matching server-side lock | Client-side only (can be bypassed) |
| 6.5 | Re-download button triggers payment | Razorpay 50% price checkout | Opens full-price checkout |
| 6.6 | Insurance badge shows if purchased | "🛡 Insured" visible | Never shows |
| 6.7 | Download Invoice link works | PDF downloads correctly | 404 or blank PDF |
| 6.8 | Invoice contains correct data | Buyer, DJ, track, amounts accurate | Wrong buyer or amounts |
| 6.9 | Library empty state | Friendly empty state message | Broken layout |
| 6.10 | Switch between Tracks/Albums tabs | Content switches correctly | Tab switch crashes |

---

## PHASE 7 — DJ APPLICATION FLOW

| # | Test | Expected | Common Bug |
|---|------|----------|------------|
| 7.1 | "Become a DJ" click — not logged in | Auth modal opens | Redirects to /login losing context |
| 7.2 | After login via modal | Continues to DJ application form | Goes to homepage |
| 7.3 | Submit application with fee disabled | Submits without payment step | Payment form shows despite fee being OFF |
| 7.4 | Submit application with fee enabled | Payment required before submit | Submittable without paying |
| 7.5 | Content responsibility checkbox | Cannot submit without checking | Pre-checked or not required |
| 7.6 | Submit without filling required fields | Inline errors on each empty field | Submits with empty fields |
| 7.7 | After submission — status in navbar | "Application Pending" pill shown | No status indicator |
| 7.8 | Apply again while pending | Blocked: "Application pending review" | Can submit multiple applications |
| 7.9 | Admin approves — role changes | User's role updates to `dj` immediately | Role cached, needs re-login |
| 7.10 | After approval — DJ Panel appears | Navbar updates on next login | Never appears even after approval |
| 7.11 | Admin rejects — user notified | Rejection email sent | No email sent |
| 7.12 | Rejected user can reapply | Reapplication allowed (per cooldown policy) | Permanently blocked |
| 7.13 | DJ Panel accessible before approval | Blocked — 403 | Accessible if URL is known |

---

## PHASE 8 — DJ DASHBOARD FULL AUDIT

### 8.1 Overview

| # | Test | Expected | Common Bug |
|---|------|----------|------------|
| 8.1.1 | KPI cards load | Correct lifetime/monthly numbers | Shows 0 despite sales |
| 8.1.2 | Revenue chart renders | 12-week line chart visible | Blank chart or JS error |
| 8.1.3 | Chart hover tooltip | Shows exact week amount in DM Mono | Tooltip undefined or NaN |
| 8.1.4 | Top 5 tracks table | Ranked by revenue, correct data | Wrong order or missing tracks |

---

### 8.2 Track Upload

| # | Test | Expected | Common Bug |
|---|------|----------|------------|
| 8.2.1 | Upload valid audio file | File stored in R2 private, metadata injected | File stored publicly |
| 8.2.2 | Upload file over size limit | Blocked with size error | Silent fail or timeout |
| 8.2.3 | Upload unsupported format | Blocked with format error | Accepts any file |
| 8.2.4 | Set price below ₹19 | Blocked: "Minimum price ₹19" | Accepts ₹0 or below minimum |
| 8.2.5 | Price info box updates live | Recalculates as DJ types | Doesn't update until submit |
| 8.2.6 | Commission % in breakdown matches admin setting | Dynamic, not hardcoded | Always shows 15% regardless of promo |
| 8.2.7 | LAUNCH OFFER badge in breakdown | Shows when promo active | Never shows |
| 8.2.8 | Preview type toggle | Switches between YouTube/Instagram input | Field doesn't change on toggle |
| 8.2.9 | Invalid YouTube URL | Validation error | Accepts any string |
| 8.2.10 | Invalid Instagram URL | Validation error | Accepts any string |
| 8.2.11 | Add collaborator — valid DJ username | Found and added | Search returns no results |
| 8.2.12 | Add more than 3 collaborators | Blocked: max 3 | 4th collaborator accepted |
| 8.2.13 | Revenue split totals ≠ 100% | Error: "Split must total 100%" | Submits with wrong total |
| 8.2.14 | Revenue split totals = 100% | Validated, submit enabled | Still shows error |
| 8.2.15 | Content responsibility checkbox | Required, not pre-checked | Pre-checked or skippable |
| 8.2.16 | Submit without checkbox | Blocked with error | Submits without acknowledgment |
| 8.2.17 | Submitted track goes to admin review | Status: "Pending Review" in track list | Publishes immediately |
| 8.2.18 | Metadata injected in file | Check file after download — platform tag present | No metadata injected |
| 8.2.19 | ZIP upload — reprocessed and re-zipped | Metadata in all files inside ZIP | ZIP stored as-is |

---

### 8.3 Track Management

| # | Test | Expected | Common Bug |
|---|------|----------|------------|
| 8.3.1 | Pause track | Track disappears from public browse | Still visible publicly |
| 8.3.2 | Re-activate track | Reappears in browse | Stays hidden |
| 8.3.3 | Soft delete track | Removed from public, archived, DJ notified | Hard deleted or not archived |
| 8.3.4 | Delete confirmation shake animation | Shakes before confirm modal | No animation |
| 8.3.5 | Edit track details | Updates reflected on public page | Old data cached |
| 8.3.6 | Pause entire store | All tracks hidden, storefront shows paused message | Individual tracks still buyable |

---

### 8.4 Earnings & Payouts

| # | Test | Expected | Common Bug |
|---|------|----------|------------|
| 8.4.1 | Earnings reflect completed purchases only | Incomplete downloads not counted | Counts all payments including failed downloads |
| 8.4.2 | Ad revenue appears separately in breakdown | Visible in earnings detail | Never populated |
| 8.4.3 | Collab track earnings split correctly | Each collaborator sees their % | Full amount shown to each DJ |
| 8.4.4 | Payout page without 2FA | Blocked with 2FA prompt | Payout page accessible without 2FA |
| 8.4.5 | Enable 2FA flow | Works end-to-end | 2FA setup broken |
| 8.4.6 | Payout below ₹500 threshold | "Request Payout" disabled, amount shown | Allows payout below threshold |
| 8.4.7 | Payout above threshold | Can request payout | Disabled even above threshold |
| 8.4.8 | Escrow amount tooltip | Explains what escrow means | No tooltip, confuses DJ |
| 8.4.9 | Admin holds payout | Status changes to "Held" in DJ view | No status update shown to DJ |
| 8.4.10 | Held payout reason | Reason visible (if admin provided one) | Just shows "Held" with no context |

---

## PHASE 9 — ADMIN DASHBOARD FULL AUDIT

### 9.1 DJ Applications

| # | Test | Expected | Common Bug |
|---|------|----------|------------|
| 9.1.1 | Approve DJ | Role changes to `dj`, email sent | Role unchanged in DB |
| 9.1.2 | Reject DJ | Email sent, status updated | No email |
| 9.1.3 | Grant Verified Badge | Badge appears on DJ's storefront | Badge not reflected publicly |
| 9.1.4 | Fee toggle ON with confirmation | Fee charged on next application | Fee not charged despite toggle |
| 9.1.5 | Fee amount field grayed when OFF | Not editable when disabled | Editable but value ignored |

---

### 9.2 Content Moderation

| # | Test | Expected | Common Bug |
|---|------|----------|------------|
| 9.2.1 | Soft delete content | Removed from public, archived | Hard deleted |
| 9.2.2 | DJ notification on delete | Email triggered | No email |
| 9.2.3 | Restore deleted content | Reappears publicly | Restore not implemented |
| 9.2.4 | Deleted content in archive | Accessible to admin only | Fully inaccessible |

---

### 9.3 Revenue & Payouts

| # | Test | Expected | Common Bug |
|---|------|----------|------------|
| 9.3.1 | KPI cards accurate | Match actual DB totals | Cached stale data |
| 9.3.2 | Process weekly payouts | All eligible DJs paid, status updated | Payout processed twice |
| 9.3.3 | Hold individual payout | Status → Held, DJ sees it | No DJ-side update |
| 9.3.4 | Global freeze toggle | All payouts frozen immediately | In-flight payouts not caught |
| 9.3.5 | Investor report PDF export | Generates correctly formatted PDF | Export button crashes |

---

### 9.4 Security Controls

| # | Test | Expected | Common Bug |
|---|------|----------|------------|
| 9.4.1 | Add IP to blacklist | All requests from that IP blocked | IP added but not enforced |
| 9.4.2 | Freeze user account | User cannot login or download | Account frozen but active session continues |
| 9.4.3 | Kill switch ON | All downloads globally disabled | Only new downloads blocked, in-progress continue |
| 9.4.4 | Kill switch requires "CONFIRM" | Won't activate without typing CONFIRM | Activates on single click |
| 9.4.5 | Maintenance mode ON | Public site shows maintenance page | Some pages bypass maintenance |
| 9.4.6 | Unblacklist IP | Access restored | Cannot remove from blacklist |

---

### 9.5 Offer & Pricing Controls

| # | Test | Expected | Common Bug |
|---|------|----------|------------|
| 9.5.1 | Change commission rate | New rate reflected in DJ upload breakdown immediately | Cached old rate |
| 9.5.2 | Enable buyer platform fee | Fee added to buyer total silently | Fee shown as line item |
| 9.5.3 | Enable GST | GST calculated and folded into total | GST shown as line item |
| 9.5.4 | Enable offer banner | Banner appears site-wide on next load | Banner not visible |
| 9.5.5 | Disable offer banner | Banner disappears everywhere | Still shows on some pages |
| 9.5.6 | Offer banner close (×) | Session-dismissed, returns on new session | Permanent dismiss or never dismisses |
| 9.5.7 | Offer start/end dates | Banner only shows within date range | Ignores dates |
| 9.5.8 | Page-specific banner visibility | Only shows on selected pages | Shows everywhere regardless |

---

## PHASE 10 — OFFER & PRICING SYSTEM

| # | Test | Expected | Common Bug |
|---|------|----------|------------|
| 10.1 | Homepage floating offer card — timing | Appears after 1.2s delay | Appears instantly or never |
| 10.2 | Card spring animation | Smooth cubic-bezier slide-in | Jumps or no animation |
| 10.3 | Shimmer line loops | Continuous left-to-right shimmer | Runs once then stops |
| 10.4 | Offer card close button | Dismissed for session, returns on new visit | Permanent or never works |
| 10.5 | Announcement strip marquee | Smooth continuous scroll | Jumps or freezes |
| 10.6 | Strip close button | Session dismissed | Permanent dismiss |
| 10.7 | Offer content pulls from backend | Shows admin-typed text | Shows hardcoded placeholder |
| 10.8 | No offer active | No banner, no card, no strip | Empty containers still visible |
| 10.9 | Checkout offer notice | Matches active offer title + tagline | Shows wrong or stale offer |
| 10.10 | DJ upload commission badge | Shows "LAUNCH OFFER" when promo active | Never shows badge |

---

## PHASE 11 — SECURITY & EXPLOIT ATTEMPTS

**Run every one of these. Document and fix any that succeed.**

### 11.1 File Access

| # | Attack | Expected Defense | Fix If Broken |
|---|--------|-----------------|---------------|
| 11.1.1 | Guess R2 file URL directly | 403 — bucket is private | Set R2 bucket to private |
| 11.1.2 | Copy download proxy URL and share it | Token is single-use — second access fails | Enforce token single-use in DB |
| 11.1.3 | Use token after expiry | 401 — token expired | Check `expires_at` server-side |
| 11.1.4 | Use token from different IP | 403 — IP mismatch | Validate IP on every token use |
| 11.1.5 | Modify token string manually | 400 — token not found | Tokens are UUIDs, not guessable |
| 11.1.6 | Download without purchasing | 403 — no ownership record | Check purchases table before token gen |
| 11.1.7 | Replay attack — capture and resend download request | Rejected — token already used | Single-use flag checked atomically |

---

### 11.2 Payment Bypass

| # | Attack | Expected | Fix |
|---|--------|----------|-----|
| 11.2.1 | Skip payment, directly call download API with content_id | 403 — no valid purchase | Always verify payment before token gen |
| 11.2.2 | Modify price in browser before Razorpay opens | Server-side price used, not client | Never trust client-sent price |
| 11.2.3 | Intercept webhook and fake payment success | Webhook signature verified | Verify Razorpay signature on all webhooks |
| 11.2.4 | Replay old webhook | Idempotency key prevents duplicate processing | Webhook idempotency enforced |

---

### 11.3 Account & Role Exploitation

| # | Attack | Expected | Fix |
|---|--------|----------|-----|
| 11.3.1 | Change role to `dj` in local storage/cookie | Role verified server-side on every request | Never trust client-side role |
| 11.3.2 | Access /admin URL directly as buyer | 403 — admin role required | RLS + server-side role check |
| 11.3.3 | Access /dj-panel URL directly as buyer | 403 — dj role required | Server-side guard on all DJ routes |
| 11.3.4 | DJ accesses another DJ's earnings | 403 — RLS prevents cross-DJ access | Supabase RLS on earnings table |
| 11.3.5 | Buyer views another user's library | 403 — own purchases only | RLS on purchases table |
| 11.3.6 | Inject collaborator with 100% split alone | Server validates total = 100% after commission | Server-side split validation |

---

### 11.4 Input Injection

| # | Attack | Expected | Fix |
|---|--------|----------|-----|
| 11.4.1 | XSS in track title field | Sanitized — no script executes | Escape all user-generated content on output |
| 11.4.2 | XSS in DJ bio | Same | Same |
| 11.4.3 | SQL injection in search query | Parameterized queries — no effect | Use ORM parameterization |
| 11.4.4 | Oversized file upload (e.g. 10GB) | Rejected before storage | Server streams to R2 without size check |
| 11.4.5 | Malformed ZIP upload | Rejected or handled gracefully | Crashes ZIP processor |

---

## PHASE 12 — MOBILE & RESPONSIVE

| # | Test | Expected | Common Bug |
|---|------|----------|------------|
| 12.1 | Homepage on 375px (iPhone SE) | Full layout visible, no overflow | Horizontal scroll |
| 12.2 | Track cards in single column | Fill full width, readable | Cards too narrow or overflow |
| 12.3 | Download button 72px touch target | Easy to tap | Too small, mis-taps |
| 12.4 | Filter bottom sheet opens | Slides up smoothly | Doesn't open or covers full screen |
| 12.5 | Auth modal on mobile | Full width, scrollable if tall | Modal overflows screen |
| 12.6 | DJ Dashboard on mobile | Sidebar collapses to hamburger | Sidebar overlaps content |
| 12.7 | Checkout on mobile | Stacked layout, large tap targets | Side-by-side broken layout |
| 12.8 | Offer card on mobile | Positioned correctly, not offscreen | Card partially off-screen |
| 12.9 | Swipe on DJ storefront tabs | Swipe changes tab | No swipe support |
| 12.10 | Haptic on download complete | Single pulse on success | No haptic or constant vibration |
| 12.11 | Price info box collapsible on mobile | Tap to expand "Show buyer price breakdown" | Always expanded, takes too much space |
| 12.12 | Bottom tab bar (logged in) | All 4 tabs work and navigate correctly | One or more tabs broken |

---

## PHASE 13 — THEME SYSTEM

| # | Test | Expected | Common Bug |
|---|------|----------|------------|
| 13.1 | OS set to dark → visit site | Dark theme loads | Light theme ignores OS |
| 13.2 | OS set to light → visit site | Light (warm cream) theme loads | Dark always loads |
| 13.3 | Toggle dark → light | Smooth transition, all elements update | Some elements stay dark |
| 13.4 | Toggle light → dark | Same | Some elements stay light |
| 13.5 | Theme preference saved | Revisiting site uses saved preference | Resets to OS default every visit |
| 13.6 | Theme toggle icon updates | Moon → Sun / Sun → Moon | Icon doesn't change |
| 13.7 | ARIA label updates on toggle | Screen reader reads correct mode | Static label |
| 13.8 | Light theme — text contrast | All text ≥ 4.5:1 on cream background | Mint `#00FFB3` used on cream (FAIL) |
| 13.9 | Dark mode mint on dark bg | `#00FFB3` on `#0A0A0F` — verify contrast | Low contrast passes visually but fails WCAG |
| 13.10 | Toast notifications themed | Match current theme | Always dark toasts on light theme |
| 13.11 | Modals themed | Match current theme | Modal hardcoded dark |
| 13.12 | Third-party embeds (YouTube) | Can't theme — ensure they don't clash | YouTube light iframe on dark page jarring |

---

## PHASE 14 — EMAIL NOTIFICATIONS

For each: trigger the action, check inbox within 2 minutes.

| # | Trigger | Expected Email | Common Bug |
|---|---------|---------------|------------|
| 14.1 | New user registration | Verification email with link | Not sent / goes to spam |
| 14.2 | Forgot password | Reset link email | Not sent |
| 14.3 | Successful purchase | Confirmation + GST invoice PDF | No invoice / wrong amounts |
| 14.4 | 1 download attempt remaining | Warning email | Not sent |
| 14.5 | Download completed successfully | Confirmation email | Not sent |
| 14.6 | DJ application submitted | "We received your application" email | Not sent |
| 14.7 | DJ application approved | Approval email with DJ Panel link | Not sent or wrong link |
| 14.8 | DJ application rejected | Rejection email | Not sent |
| 14.9 | DJ track soft-deleted by admin | Notification email with reason | Not sent |
| 14.10 | Payout processed | Payment confirmation email | Not sent |
| 14.11 | Weekly earnings summary (DJ) | Weekly email with earnings data | Not sent or sent daily |
| 14.12 | Account frozen by admin | Notification email | Not sent |

**Email Quality Checks:**
- No broken links in any email
- Unsubscribe link present (legal requirement)
- Emails don't go to spam (check SPF/DKIM/DMARC for resend.com domain)
- Mobile-rendered correctly (test in Gmail mobile)
- No raw template variables like `{{user_name}}` showing in email body

---

## PHASE 15 — CROSS-BROWSER & PERFORMANCE

### 15.1 Browser Compatibility

Test all critical flows in:
- Chrome (latest)
- Firefox (latest)
- Safari 16+ (macOS)
- Safari iOS 16+ (iPhone)
- Chrome Android

| # | Test | Known Safari Issues |
|---|------|---------------------|
| 15.1.1 | Google OAuth popup | Blocked by Safari popup blocker — needs redirect fallback |
| 15.1.2 | Instagram embed | May not render in Safari — graceful fallback needed |
| 15.1.3 | CSS backdrop-filter | Check nav blur works in all browsers |
| 15.1.4 | CSS custom properties (tokens) | All modern browsers — should be fine |
| 15.1.5 | Download via proxy | Verify `Content-Disposition: attachment` header set |
| 15.1.6 | navigator.vibrate (haptic) | Not supported in Safari — no error should throw |

---

### 15.2 Performance Checks

| # | Test | Target | Tool |
|---|------|--------|------|
| 15.2.1 | Homepage load (cold) | < 3s LCP | Lighthouse |
| 15.2.2 | Search results load | < 1s after query | DevTools Network |
| 15.2.3 | Track page load | < 2s | Lighthouse |
| 15.2.4 | Images lazy loaded | Below-fold images not loaded on first paint | DevTools Network |
| 15.2.5 | No layout shift on load | CLS < 0.1 | Lighthouse |
| 15.2.6 | Download proxy speed | Does not bottleneck file transfer | Compare direct vs proxy speed |
| 15.2.7 | Admin dashboard with large dataset | Loads without hanging | Pagination or virtual scroll needed |

---

## 🐛 BUG REPORTING FORMAT

When a bug is found, document it exactly like this:

```
BUG-[###]
Phase:       [e.g. Phase 5 — Download System]
Severity:    CRITICAL / HIGH / MEDIUM / LOW
Test ID:     [e.g. 5.2.4]

Steps to reproduce:
1.
2.
3.

Expected: [what should have happened]
Actual:   [what actually happened]

Root cause: [identified cause in code/DB/config]
Fix:        [exact fix applied — file, function, line if possible]
Status:     OPEN / FIXED / VERIFIED
```

---

## 🔥 SEVERITY DEFINITIONS

| Level | Definition | Examples |
|-------|-----------|---------|
| **CRITICAL** | Security breach, data loss, financial exploit possible | R2 URL exposed, payment bypass, token reuse |
| **HIGH** | Core feature broken, major user flow fails | Download fails, purchase not recorded, DJ can't upload |
| **MEDIUM** | Feature partially broken, workaround exists | Counter wrong, badge missing, wrong redirect |
| **LOW** | Visual issue, minor UX, copy error | Animation doesn't play, wrong muted color, typo |

---

## ✅ SIGN-OFF CHECKLIST

Before declaring the platform ready, every item below must be confirmed:

**Security:**
- [ ] R2 bucket is private — no public URL accessible
- [ ] All tokens are single-use and expire
- [ ] Payment verified server-side via webhook signature
- [ ] All routes protected by correct role middleware
- [ ] No SQL injection possible in any input
- [ ] No XSS possible in any rendered user content
- [ ] Razorpay webhook signature verified on every event

**Core Flows:**
- [ ] Buy → Pay → Download completes end-to-end
- [ ] Failed download → refund eligibility correctly set
- [ ] DJ upload → admin review → approved → public
- [ ] Collab revenue split calculates correctly after commission
- [ ] Re-download lock enforced for 2 days, then requires 50% payment

**Pricing:**
- [ ] Buyers never see GST or platform fee as separate items
- [ ] Admin commission rate change reflects in DJ upload breakdown immediately
- [ ] Invoice PDF contains correct legal breakdown
- [ ] Platform fee and GST correctly folded into single total when enabled

**Auth:**
- [ ] Browse works without login
- [ ] Buy triggers auth modal, returns to track after login
- [ ] DJ Panel only accessible after admin approval
- [ ] Auto-logout on IP change works

**Offers:**
- [ ] Offer banner content comes from backend, not hardcoded
- [ ] No banner shows when admin disables it
- [ ] Offer card animation plays correctly on homepage

**Email:**
- [ ] All 12 email triggers send correctly
- [ ] No emails go to spam
- [ ] No broken template variables in any email

**Theme:**
- [ ] Both themes load correctly
- [ ] No elements hardcoded to one theme
- [ ] Contrast passes WCAG AA in both themes

---

*End of MixMint Test, Debug & Fix Prompt*
*Version 1.0 — Full platform audit from login to payout*
*Run every phase. Fix every CRITICAL and HIGH before launch.*

---


---

# ═══════════════════════════════════════════════════
# END OF PHASE 1 — FOUNDATION
# ═══════════════════════════════════════════════════

```
Phase 1 complete when:
  ✓ PhonePe processing real payments
  ✓ DJs can upload, buyers can purchase and download
  ✓ Token system working — no direct R2 access
  ✓ Metadata injected into every file before delivery
  ✓ Cloudflare Worker serving all downloads (no Vercel size limit)
  ✓ Background jobs running on Vercel Cron schedule
  ✓ Pro plan billing active — trials, renewals, overage
  ✓ TDS deducted on payouts above ₹30,000/year
  ✓ Fraud detection blocking suspicious purchases
  ✓ 2FA required for all DJ payout requests
  ✓ All 180+ QA test cases passing
  ✓ Zero CRITICAL or HIGH bugs open

→ Proceed to Phase 2: Operations & Trust
```
