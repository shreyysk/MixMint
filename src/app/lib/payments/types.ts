// Payment Provider Type Definitions

export type PaymentProvider = "razorpay" | "phonepe";
export type PaymentMode = "test" | "production";

export interface OrderParams {
  amount: number; // in smallest currency unit (paise for INR)
  currency: string;
  receipt: string;
  notes?: Record<string, string>;
}

export interface OrderResponse {
  orderId: string;
  amount: number;
  currency: string;
  keyId?: string; // For frontend checkout
  checkoutUrl?: string; // For redirect-based providers
}

export interface PaymentVerificationParams {
  orderId: string;
  paymentId: string;
  signature: string;
}

export interface PaymentStatus {
  status: "success" | "failed" | "pending";
  orderId: string;
  paymentId?: string;
  amount: number;
  method?: string;
  errorCode?: string;
  errorDescription?: string;
}

export interface WebhookPayload {
  event: string;
  data: any;
  signature?: string;
}

export interface PaymentProviderInterface {
  createOrder(params: OrderParams): Promise<OrderResponse>;
  verifyPayment(params: PaymentVerificationParams): Promise<boolean>;
  verifyWebhook(payload: WebhookPayload): Promise<boolean>;
  getPaymentStatus(orderId: string): Promise<PaymentStatus>;
}
