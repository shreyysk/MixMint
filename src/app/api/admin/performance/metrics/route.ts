import { supabaseServer } from "@/lib/supabaseServer";
import { requireAuth } from "@/lib/requireAuth";
import { ok, fail } from "@/lib/apiResponse";

/**
 * GET /api/admin/performance/metrics
 * Returns aggregated performance metrics for admin dashboard
 */
export async function GET(req: Request) {
  try {
    const user = await requireAuth();

    // Check admin role
    const { data: profile } = await supabaseServer
      .from("profiles")
      .select("role")
      .eq("id", user.id)
      .single();

    if (profile?.role !== "admin") {
      return fail("Forbidden", 403);
    }

    const { searchParams } = new URL(req.url);
    const hours = Number(searchParams.get("hours")) || 24;

    const startTime = new Date(Date.now() - hours * 60 * 60 * 1000).toISOString();

    // 1. Get endpoint performance stats
    const { data: metrics } = await supabaseServer
      .from("api_metrics")
      .select("endpoint, method, response_time_ms, status_code")
      .gte("created_at", startTime);

    if (!metrics) {
      return ok({ summary: {}, endpoints: [] });
    }

    // 2. Calculate aggregates
    const endpointStats = new Map<string, {
      count: number;
      avgResponseTime: number;
      p95ResponseTime: number;
      errorRate: number;
      errors: number;
    }>();

    metrics.forEach(m => {
      const key = `${m.method} ${m.endpoint}`;
      const stats = endpointStats.get(key) || {
        count: 0,
        avgResponseTime: 0,
        p95ResponseTime: 0,
        errorRate: 0,
        errors: 0
      };

      stats.count++;
      stats.avgResponseTime += m.response_time_ms;
      if (m.status_code >= 400) stats.errors++;

      endpointStats.set(key, stats);
    });

    // 3. Finalize calculations
    const endpoints = Array.from(endpointStats.entries()).map(([endpoint, stats]) => {
      const avgResponseTime = Math.round(stats.avgResponseTime / stats.count);
      const errorRate = (stats.errors / stats.count) * 100;

      // Calculate p95 (simplified - would need proper percentile calculation)
      const responseTimes = metrics
        .filter(m => `${m.method} ${m.endpoint}` === endpoint)
        .map(m => m.response_time_ms)
        .sort((a, b) => a - b);
      const p95Index = Math.floor(responseTimes.length * 0.95);
      const p95ResponseTime = responseTimes[p95Index] || avgResponseTime;

      return {
        endpoint,
        count: stats.count,
        avgResponseTime,
        p95ResponseTime,
        errorRate: Math.round(errorRate * 100) / 100
      };
    });

    // 4. Overall summary
    const totalRequests = metrics.length;
    const totalErrors = metrics.filter(m => m.status_code >= 400).length;
    const avgResponseTime = Math.round(
      metrics.reduce((sum, m) => sum + m.response_time_ms, 0) / totalRequests
    );

    return ok({
      summary: {
        totalRequests,
        totalErrors,
        errorRate: ((totalErrors / totalRequests) * 100).toFixed(2),
        avgResponseTime,
        timeframe: `Last ${hours} hours`
      },
      endpoints: endpoints.sort((a, b) => b.count - a.count).slice(0, 20)
    });

  } catch (err: any) {
    if (err.message === "UNAUTHORIZED") return fail("Unauthorized", 401);
    return fail(err.message || "Internal error", 500);
  }
}
