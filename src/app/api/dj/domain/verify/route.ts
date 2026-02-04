import { supabaseServer } from "@/app/lib/supabaseServer";
import { requireAuth } from "@/app/lib/requireAuth";
import { requireDJ } from "@/app/lib/requireDJ";
import { ok, fail } from "@/app/lib/apiResponse";
import { logger } from "@/app/lib/logger";
import dns from "dns";
import { promisify } from "util";

const resolveCname = promisify(dns.resolveCname);
const resolveA = promisify(dns.resolve);

/**
 * POST /api/dj/domain/verify
 * 
 * Verifies if a custom domain's DNS records are correctly pointing to MixMint.
 */
export async function POST(req: Request) {
    let user: any = null;
    try {
        user = await requireAuth();
        await requireDJ(user.id);

        const { domain } = await req.json();

        if (!domain) {
            return fail("Domain is required", 400, "SYSTEM");
        }

        // 1. Fetch the DJ profile to ensure this domain belongs to them
        const { data: djProfile, error: profileError } = await supabaseServer
            .from("dj_profiles")
            .select("id, custom_domain")
            .eq("user_id", user.id)
            .single();

        if (profileError || !djProfile) {
            return fail("DJ profile not found", 404, "SYSTEM");
        }

        if (djProfile.custom_domain !== domain) {
            // If not set yet, update it first
            await supabaseServer
                .from("dj_profiles")
                .update({ custom_domain: domain, domain_verified: false })
                .eq("id", djProfile.id);
        }

        // 2. Perform DNS Lookup
        // In a real production setup, we would check for a specific CNAME (e.g., cname.mixmint.site)
        // or a specific IP for A records.
        const EXPECTED_CNAME = process.env.NEXT_PUBLIC_APP_URL?.replace("https://", "").replace("http://", "") || "mixmint.site";

        let verified = false;
        try {
            const cnames = await resolveCname(domain);
            if (cnames.includes(EXPECTED_CNAME)) {
                verified = true;
            }
        } catch (e) {
            // If CNAME fails, try A record
            try {
                const aRecords = await resolveA(domain);
                // In production, compare with MixMint's static IP
                if (aRecords.length > 0) {
                    // For now, if any A record exists and we can resolve it, 
                    // we'll consider it a "manual check needed" or auto-verify for demo
                    // verified = true; 
                    logger.info("SYSTEM", "A record found for custom domain", { domain, aRecords });
                }
            } catch (ae) {
                logger.warn("SYSTEM", "DNS resolution failed", { domain });
            }
        }

        // For simulation/dev purposes, we'll mark as verified if successfully resolved at all
        // In reality, this would be much stricter.
        if (verified) {
            await supabaseServer
                .from("dj_profiles")
                .update({ domain_verified: true })
                .eq("id", djProfile.id);

            logger.info("SYSTEM", "Custom domain verified successfully", { domain, dj: user.email });
            return ok({ success: true, message: "Domain verified successfully" });
        } else {
            return fail(`Domain ${domain} is not pointing to ${EXPECTED_CNAME} yet. Please wait for DNS propagation.`, 400, "SYSTEM");
        }

    } catch (err: any) {
        logger.error("SYSTEM", "Domain verification failure", err);
        return fail(err.message || "Verification failed", 500, "SYSTEM");
    }
}
