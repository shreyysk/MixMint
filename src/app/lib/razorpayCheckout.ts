// Razorpay payment utility for frontend

declare global {
  interface Window {
    Razorpay: any;
  }
}

interface RazorpayOptions {
  key: string;
  amount: number;
  currency: string;
  name: string;
  description: string;
  order_id: string;
  handler: (response: RazorpayResponse) => void;
  prefill?: {
    name?: string;
    email?: string;
  };
  theme?: {
    color?: string;
  };
}

interface RazorpayResponse {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
}

/**
 * Load Razorpay checkout script
 */
export function loadRazorpayScript(): Promise<boolean> {
  return new Promise((resolve) => {
    if (typeof window.Razorpay !== "undefined") {
      resolve(true);
      return;
    }

    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
}

/**
 * Initialize Razorpay payment
 */
export async function initiateRazorpayPayment(
  options: RazorpayOptions
): Promise<void> {
  const loaded = await loadRazorpayScript();

  if (!loaded) {
    throw new Error("Failed to load Razorpay SDK");
  }

  const razorpay = new window.Razorpay(options);
  razorpay.open();
}

/**
 * Complete purchase flow (create order + payment + verify)
 */
export async function purchaseContent(params: {
  contentId: string;
  contentType: "track" | "zip";
  userEmail?: string;
  userName?: string;
  onSuccess?: () => void;
  onFailure?: (error: string) => void;
}): Promise<void> {
  try {
    // Step 1: Create payment order
    const orderRes = await fetch("/api/payment/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        content_type: params.contentType,
        content_id: params.contentId,
      }),
    });

    const orderData = await orderRes.json();

    if (!orderRes.ok) {
      throw new Error(orderData.error || "Failed to create order");
    }

    // Step 2: Show Razorpay checkout
    await initiateRazorpayPayment({
      key: orderData.keyId,
      amount: orderData.amount,
      currency: orderData.currency,
      name: "MixMint",
      description: orderData.description,
      order_id: orderData.orderId,
      prefill: {
        email: params.userEmail,
        name: params.userName,
      },
      theme: {
        color: "#7c3aed",
      },
      handler: async (response) => {
        // Step 3: Verify payment
        try {
          const verifyRes = await fetch("/api/payment/verify", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              orderId: response.razorpay_order_id,
              paymentId: response.razorpay_payment_id,
              signature: response.razorpay_signature,
              content_type: params.contentType,
              content_id: params.contentId,
            }),
          });

          const verifyData = await verifyRes.json();

          if (verifyRes.ok) {
            params.onSuccess?.();
            window.location.href = "/payment/success";
          } else {
            throw new Error(verifyData.error);
          }
        } catch (err: any) {
          params.onFailure?.(err.message);
          window.location.href = "/payment/failed";
        }
      },
    });
  } catch (err: any) {
    params.onFailure?.(err.message);
    alert(`Payment failed: ${err.message}`);
  }
}

/**
 * Subscribe to DJ flow
 */
export async function subscribeToDJ(params: {
  djId: string;
  plan: "basic" | "pro" | "super";
  userEmail?: string;
  userName?: string;
  onSuccess?: () => void;
  onFailure?: (error: string) => void;
}): Promise<void> {
  try {
    // Create subscription payment order
    const orderRes = await fetch("/api/payment/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        content_type: "subscription",
        content_id: params.djId,
        plan: params.plan,
      }),
    });

    const orderData = await orderRes.json();

    if (!orderRes.ok) {
      throw new Error(orderData.error || "Failed to create subscription order");
    }

    await initiateRazorpayPayment({
      key: orderData.keyId,
      amount: orderData.amount,
      currency: orderData.currency,
      name: "MixMint",
      description: orderData.description,
      order_id: orderData.orderId,
      prefill: {
        email: params.userEmail,
        name: params.userName,
      },
      theme: {
        color: "#7c3aed",
      },
      handler: async (response) => {
        try {
          const verifyRes = await fetch("/api/payment/verify", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              orderId: response.razorpay_order_id,
              paymentId: response.razorpay_payment_id,
              signature: response.razorpay_signature,
              content_type: "subscription",
              content_id: params.djId,
              plan: params.plan,
            }),
          });

          const verifyData = await verifyRes.json();

          if (verifyRes.ok) {
            params.onSuccess?.();
            window.location.href = "/payment/success";
          } else {
            throw new Error(verifyData.error);
          }
        } catch (err: any) {
          params.onFailure?.(err.message);
          window.location.href = "/payment/failed";
        }
      },
    });
  } catch (err: any) {
    params.onFailure?.(err.message);
    alert(`Subscription failed: ${err.message}`);
  }
}
