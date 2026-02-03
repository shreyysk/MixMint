import type {
  PaymentProviderInterface,
  PaymentMode,
  OrderParams,
  OrderResponse,
  PaymentVerificationParams,
  PaymentStatus,
  WebhookPayload,
} from "./types";

/**
 * PhonePe Payment Provider (DISABLED - Awaiting Credentials)
 * 
 * This provider is implemented but disabled until PhonePe credentials are provided.
 * To enable:
 * 1. Add PhonePe credentials to .env.local
 * 2. Admin switches payment gateway in settings
 * 3. This class will handle PhonePe payments
 */
export class PhonePeProvider implements PaymentProviderInterface {
  private mode: PaymentMode;

  constructor(mode: PaymentMode) {
    this.mode = mode;
    
    // Check if credentials exist
    const merchantId = process.env.PHONEPE_MERCHANT_ID;
    const saltKey = process.env.PHONEPE_SALT_KEY;

    if (!merchantId || !saltKey) {
      console.warn("[PHONEPE_DISABLED] Missing credentials. PhonePe payments unavailable.");
    }
  }

  async createOrder(params: OrderParams): Promise<OrderResponse> {
    throw new Error(
      "[PHONEPE_DISABLED] PhonePe integration is not yet configured. " +
      "Please provide PhonePe credentials or switch to Razorpay in admin settings."
    );
  }

  async verifyPayment(params: PaymentVerificationParams): Promise<boolean> {
    throw new Error("[PHONEPE_DISABLED] PhonePe verification unavailable.");
  }

  async verifyWebhook(payload: WebhookPayload): Promise<boolean> {
    throw new Error("[PHONEPE_DISABLED] PhonePe webhook verification unavailable.");
  }

  async getPaymentStatus(orderId: string): Promise<PaymentStatus> {
    throw new Error("[PHONEPE_DISABLED] PhonePe status check unavailable.");
  }
}

/**
 * NOTE: Complete PhonePe implementation will be added when credentials are provided.
 * 
 * Required environment variables:
 * - PHONEPE_MERCHANT_ID
 * - PHONEPE_SALT_KEY
 * - PHONEPE_WEBHOOK_SECRET
 * - PHONEPE_ENVIRONMENT (sandbox/production)
 * 
 * Implementation will follow PhonePe API v3 documentation:
 * - Payment initiation
 * - Redirect flow
 * - Webhook verification with HMAC-SHA256
 * - Transaction status check
 */
