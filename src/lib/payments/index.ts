import { supabaseServer } from "@/lib/supabaseServer";
import { RazorpayProvider } from "./razorpay";
import { PhonePeProvider } from "./phonepe";
import type { PaymentProviderInterface, PaymentProvider, PaymentMode } from "./types";

interface PaymentGatewayConfig {
  provider: PaymentProvider;
  mode: PaymentMode;
}

/**
 * Get active payment gateway configuration from system_settings
 */
export async function getPaymentConfig(): Promise<PaymentGatewayConfig> {
  const { data, error } = await supabaseServer
    .from("system_settings")
    .select("value")
    .eq("key", "payment_gateway")
    .single();

  if (error || !data) {
    console.error("[PAYMENT_CONFIG_ERROR]", error);
    // Default fallback
    return { provider: "razorpay", mode: "test" };
  }

  return data.value as PaymentGatewayConfig;
}

/**
 * Factory function to get the active payment provider instance
 */
export async function getPaymentProvider(): Promise<PaymentProviderInterface> {
  const config = await getPaymentConfig();

  console.log(`[PAYMENT_PROVIDER] Using ${config.provider} in ${config.mode} mode`);

  if (config.provider === "razorpay") {
    return new RazorpayProvider(config.mode);
  } else if (config.provider === "phonepe") {
    return new PhonePeProvider(config.mode);
  }

  throw new Error(`Unsupported payment provider: ${config.provider}`);
}

/**
 * Update payment gateway configuration (Admin only)
 */
export async function updatePaymentConfig(
  provider: PaymentProvider,
  mode: PaymentMode,
  adminUserId: string
): Promise<void> {
  const { error } = await supabaseServer
    .from("system_settings")
    .update({
      value: { provider, mode },
      updated_at: new Date().toISOString(),
      updated_by: adminUserId,
    })
    .eq("key", "payment_gateway");

  if (error) {
    throw new Error(`Failed to update payment config: ${error.message}`);
  }

  console.log(`[PAYMENT_CONFIG_UPDATED] ${provider} - ${mode} by ${adminUserId}`);
}
