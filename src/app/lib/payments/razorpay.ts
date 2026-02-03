import Razorpay from "razorpay";
import crypto from "crypto";
import type {
  PaymentProviderInterface,
  PaymentMode,
  OrderParams,
  OrderResponse,
  PaymentVerificationParams,
  PaymentStatus,
  WebhookPayload,
} from "./types";

export class RazorpayProvider implements PaymentProviderInterface {
  private razorpay: Razorpay;
  private mode: PaymentMode;
  private keyId: string;
  private keySecret: string;
  private webhookSecret: string;

  constructor(mode: PaymentMode) {
    this.mode = mode;
    this.keyId = process.env.NEXT_PUBLIC_RAZORPAY_KEY_ID!;
    this.keySecret = process.env.RAZORPAY_KEY_SECRET!;
    this.webhookSecret = process.env.RAZORPAY_WEBHOOK_SECRET!;

    if (!this.keyId || !this.keySecret) {
      throw new Error("[RAZORPAY_ERROR] Missing Razorpay credentials");
    }

    this.razorpay = new Razorpay({
      key_id: this.keyId,
      key_secret: this.keySecret,
    });

    console.log(`[RAZORPAY] Initialized in ${mode} mode`);
  }

  /**
   * Create a Razorpay order
   */
  async createOrder(params: OrderParams): Promise<OrderResponse> {
    try {
      const order = await this.razorpay.orders.create({
        amount: params.amount,
        currency: params.currency,
        receipt: params.receipt,
        notes: params.notes,
      });

      console.log(`[RAZORPAY_ORDER_CREATED] ${order.id} - ₹${params.amount / 100}`);

      return {
        orderId: order.id,
        amount: Number(order.amount),
        currency: order.currency,
        keyId: this.keyId, // For frontend Razorpay checkout
      };
    } catch (error: any) {
      console.error("[RAZORPAY_ORDER_ERROR]", error);
      throw new Error(`Failed to create Razorpay order: ${error.message}`);
    }
  }

  /**
   * Verify Razorpay payment signature
   */
  async verifyPayment(params: PaymentVerificationParams): Promise<boolean> {
    try {
      const { orderId, paymentId, signature } = params;

      // Generate expected signature
      const text = `${orderId}|${paymentId}`;
      const expectedSignature = crypto
        .createHmac("sha256", this.keySecret)
        .update(text)
        .digest("hex");

      const isValid = expectedSignature === signature;

      if (isValid) {
        console.log(`[RAZORPAY_PAYMENT_VERIFIED] ${paymentId}`);
      } else {
        console.error(`[RAZORPAY_SIGNATURE_MISMATCH] ${paymentId}`);
      }

      return isValid;
    } catch (error: any) {
      console.error("[RAZORPAY_VERIFY_ERROR]", error);
      return false;
    }
  }

  /**
   * Verify Razorpay webhook signature
   */
  async verifyWebhook(payload: WebhookPayload): Promise<boolean> {
    try {
      if (!payload.signature || !this.webhookSecret) {
        console.error("[RAZORPAY_WEBHOOK_ERROR] Missing signature or secret");
        return false;
      }

      const expectedSignature = crypto
        .createHmac("sha256", this.webhookSecret)
        .update(JSON.stringify(payload.data))
        .digest("hex");

      const isValid = expectedSignature === payload.signature;

      if (isValid) {
        console.log(`[RAZORPAY_WEBHOOK_VERIFIED] Event: ${payload.event}`);
      } else {
        console.error(`[RAZORPAY_WEBHOOK_INVALID] Event: ${payload.event}`);
      }

      return isValid;
    } catch (error: any) {
      console.error("[RAZORPAY_WEBHOOK_ERROR]", error);
      return false;
    }
  }

  /**
   * Get payment status from Razorpay
   */
  async getPaymentStatus(paymentId: string): Promise<PaymentStatus> {
    try {
      const payment = await this.razorpay.payments.fetch(paymentId);

      let status: "success" | "failed" | "pending";
      if (payment.status === "captured" || payment.status === "authorized") {
        status = "success";
      } else if (payment.status === "failed") {
        status = "failed";
      } else {
        status = "pending";
      }

      return {
        status,
        orderId: payment.order_id,
        paymentId: payment.id,
        amount: Number(payment.amount),
        method: payment.method,
        errorCode: payment.error_code ?? undefined,
        errorDescription: payment.error_description ?? undefined,
      };
    } catch (error: any) {
      console.error("[RAZORPAY_STATUS_ERROR]", error);
      throw new Error(`Failed to fetch payment status: ${error.message}`);
    }
  }
}
