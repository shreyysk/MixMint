
import { supabaseAdmin } from "@/lib/supabaseServer";

export class DJService {
  /**
   * Apply for a DJ profile
   */
  static async apply(userId: string, data: { dj_name: string; slug: string }) {
    const { dj_name, slug } = data;

    if (!dj_name || !slug) {
      throw new Error("DJ Name and Slug are required");
    }

    // 1. Check if slug is taken
    const { data: existing } = await supabaseAdmin
      .from("dj_profiles")
      .select("slug")
      .eq("slug", slug)
      .single();

    if (existing) {
      throw new Error("This slug is already taken");
    }

    // 2. Create DJ Profile
    const { error: insertError } = await supabaseAdmin
      .from("dj_profiles")
      .insert({
        user_id: userId,
        dj_name,
        slug,
        status: "pending"
      });

    if (insertError) {
      if (insertError.code === "23505") { // Unique violation
          throw new Error("You already have an active or pending DJ profile");
      }
      throw insertError;
    }

    return { message: "DJ application submitted successfully", status: "pending" };
  }

  /**
   * Activate a DJ profile (Admin function)
   */
  static async activate(userId: string, email?: string) {
    // 1. Force update the core profile to 'dj'
    const { error: profileError } = await supabaseAdmin
        .from("profiles")
        .upsert({ id: userId, role: "dj" });

    if (profileError) throw profileError;

    // 2. Ensure DJ profile is created and approved
    const { data: existing } = await supabaseAdmin
        .from("dj_profiles")
        .select("id")
        .eq("user_id", userId)
        .single();

    if (existing) {
        const { error: updateError } = await supabaseAdmin
            .from("dj_profiles")
            .update({ status: "approved" })
            .eq("user_id", userId);
        if (updateError) throw updateError;
    } else {
        const { error: insertError } = await supabaseAdmin
            .from("dj_profiles")
            .insert({
                user_id: userId,
                dj_name: email?.split("@")[0] || "New DJ",
                slug: `dj-${userId.slice(0, 8)}`,
                status: "approved",
                bio: "Activated via admin",
            });
        if (insertError) throw insertError;
    }

    return { success: true, message: "DJ Account Fully Activated" };
  }

  /**
   * Get DJ Profile by User ID
   */
  static async getProfileByUserId(userId: string) {
      const { data, error } = await supabaseAdmin
          .from("dj_profiles")
          .select("*")
          .eq("user_id", userId)
          .single();
      
      if (error && error.code !== 'PGRST116') throw error;
      return data;
  }
}
