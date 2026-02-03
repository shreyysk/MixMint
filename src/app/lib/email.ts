import { Resend } from "resend";

const resend = new Resend(process.env.RESEND_API_KEY);
const fromEmail = process.env.RESEND_FROM_EMAIL || "noreply@mixmint.site";

interface PurchaseEmailParams {
  to: string;
  userName: string;
  contentTitle: string;
  contentType: "track" | "album";
  price: number;
  downloadUrl: string;
}

interface SubscriptionEmailParams {
  to: string;
  userName: string;
  djName: string;
  plan: string;
  trackQuota: number;
  zipQuota: number;
  expiresAt: string;
}

/**
 * Send purchase confirmation email with download link
 */
export async function sendPurchaseEmail(params: PurchaseEmailParams): Promise<void> {
  const { to, userName, contentTitle, contentType, price, downloadUrl } = params;

  const contentTypeLabel = contentType === "track" ? "Track" : "Album Pack";

  const html = `
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #7c3aed 0%, #a78bfa 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }
        .button { display: inline-block; padding: 12px 30px; background: #7c3aed; color: white; text-decoration: none; border-radius: 8px; font-weight: bold; }
        .footer { text-align: center; margin-top: 30px; color: #666; font-size: 12px; }
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <h1 style="margin: 0;">🎵 Purchase Confirmed!</h1>
        </div>
        <div class="content">
          <p>Hi <strong>${userName}</strong>,</p>
          <p>Thank you for your purchase on <strong>MixMint</strong>!</p>
          
          <h3>Order Details:</h3>
          <ul>
            <li><strong>Content:</strong> ${contentTitle}</li>
            <li><strong>Type:</strong> ${contentTypeLabel}</li>
            <li><strong>Amount:</strong> ₹${price}</li>
          </ul>

          <p>Your ${contentTypeLabel.toLowerCase()} is ready to download:</p>
          <p style="text-align: center; margin: 30px 0;">
            <a href="${downloadUrl}" class="button">Download Now</a>
          </p>

          <p style="color: #666; font-size: 14px;">
            <strong>Note:</strong> This download link will expire in 5 minutes for security. 
            If expired, visit your library to generate a new link.
          </p>
        </div>
        <div class="footer">
          <p>© ${new Date().getFullYear()} MixMint — Home of DJ Releases</p>
          <p>Questions? Reply to this email or visit mixmint.site</p>
        </div>
      </div>
    </body>
    </html>
  `;

  await sendEmailWithRetry({
    to,
    subject: `✅ ${contentTypeLabel} Purchase Confirmed - ${contentTitle}`,
    html,
  });
}

/**
 * Send subscription confirmation email
 */
export async function sendSubscriptionEmail(params: SubscriptionEmailParams): Promise<void> {
  const { to, userName, djName, plan, trackQuota, zipQuota, expiresAt } = params;

  const expiryDate = new Date(expiresAt).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  const html = `
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #7c3aed 0%, #a78bfa 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }
        .quota-box { background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #7c3aed; }
        .footer { text-align: center; margin-top: 30px; color: #666; font-size: 12px; }
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <h1 style="margin: 0;">🎉 Subscription Activated!</h1>
        </div>
        <div class="content">
          <p>Hi <strong>${userName}</strong>,</p>
          <p>Your subscription to <strong>${djName}</strong> is now active!</p>
          
          <div class="quota-box">
            <h3 style="margin-top: 0;">Your ${plan.toUpperCase()} Plan Benefits:</h3>
            <ul>
              <li><strong>${trackQuota}</strong> track downloads per month</li>
              <li><strong>${zipQuota}</strong> album pack downloads per month</li>
              <li>Valid until <strong>${expiryDate}</strong></li>
            </ul>
          </div>

          <p>Start exploring ${djName}'s exclusive content now!</p>
          
          <p style="text-align: center; margin: 30px 0;">
            <a href="${process.env.NEXT_PUBLIC_APP_URL}/dj/${djName.toLowerCase().replace(/\s+/g, '-')}" 
               style="display: inline-block; padding: 12px 30px; background: #7c3aed; color: white; text-decoration: none; border-radius: 8px; font-weight: bold;">
              Visit DJ Profile
            </a>
          </p>

          <p style="color: #666; font-size: 14px;">
            <strong>Note:</strong> Your quotas reset monthly. Purchased content doesn't count towards quotas.
          </p>
        </div>
        <div class="footer">
          <p>© ${new Date().getFullYear()} MixMint — Home of DJ Releases</p>
          <p>Questions? Reply to this email or visit mixmint.site</p>
        </div>
      </div>
    </body>
    </html>
  `;

  await sendEmailWithRetry({
    to,
    subject: `🎵 ${plan.toUpperCase()} Subscription Active - ${djName}`,
    html,
  });
}

/**
 * Retry wrapper with logging (non-blocking)
 */
async function sendEmailWithRetry(
  params: { to: string; subject: string; html: string },
  maxRetries = 3
): Promise<void> {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      const { data, error } = await resend.emails.send({
        from: fromEmail,
        to: params.to,
        subject: params.subject,
        html: params.html,
      });

      if (error) {
        throw error;
      }

      console.log(`[EMAIL_SENT] To: ${params.to} | ID: ${data?.id} | Attempt: ${attempt}`);
      return; // Success

    } catch (error: any) {
      console.error(`[EMAIL_ERROR] Attempt ${attempt}/${maxRetries}:`, error.message);

      if (attempt === maxRetries) {
        console.error(`[EMAIL_FAILED] Failed to send to ${params.to} after ${maxRetries} attempts`);
        // Don't throw - email failure should not block purchase/subscription
      } else {
        // Wait before retry (exponential backoff)
        await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
      }
    }
  }
}
