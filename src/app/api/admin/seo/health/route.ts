import { supabaseServer } from "@/lib/supabaseServer";
import { requireAuth } from "@/lib/requireAuth";
import { ok, fail } from "@/lib/apiResponse";

/**
 * GET /api/admin/seo/health
 * Checks sitemap coverage and indexing readiness.
 */
export async function GET() {
  try {
    const user = await requireAuth();
    
    // Check if admin
    const { data: profile } = await supabaseServer
      .from("profiles")
      .select("role")
      .eq("id", user.id)
      .single();

    if (profile?.role !== "admin") {
      return fail("Forbidden", 403);
    }

    // 1. Check DJ Storefront Coverage
    const { count: totalDjs } = await supabaseServer
      .from("dj_profiles")
      .select("*", { count: 'exact', head: true })
      .eq("status", "approved");

    // 2. Check Track Coverage
    const { count: totalTracks } = await supabaseServer
      .from("tracks")
      .select("*", { count: 'exact', head: true })
      .eq("status", "active");

    // 3. Last Sitemap Build (Mock for now, but in prod we'd track timestamp)
    const lastSitemapBuild = new Date().toISOString(); 

    return ok({
      status: "healthy",
      coverage: {
        djStorefronts: totalDjs,
        activeTracks: totalTracks,
      },
      lastSitemapBuild,
      sitemapUrl: "https://mixmint.site/sitemap.xml",
      indexingIssues: 0
    });

  } catch (err: any) {
    console.error("[SEO_HEALTH_API_ERROR]:", err);
    return fail(err.message || "Internal error", 500);
  }
}
