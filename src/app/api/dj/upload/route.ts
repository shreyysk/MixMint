import { PutObjectCommand } from "@aws-sdk/client-s3";
import { r2 } from "@/app/lib/r2";
import { supabaseServer } from "@/app/lib/supabaseServer";
import { getDJStoragePath } from "@/app/lib/djStorage";
import { requireAuth } from "@/app/lib/requireAuth";
import { requireDJ } from "@/app/lib/requireDJ";
import { ok, fail } from "@/app/lib/apiResponse";
import { logger } from "@/app/lib/logger";
import { checkRateLimit, getClientIp } from "@/app/lib/rateLimit";

/**
 * GET /api/dj/upload
 * Returns a status message for browser verification.
 */
export async function GET() {
    return ok({ message: "Unified DJ Upload API is active. Use POST to upload tracks or album packs." });
}

/**
 * POST /api/dj/tracks/upload
 * 
 * Production-grade uploader for DJs.
 * Supports individual tracks (.mp3, .wav, etc.) and album packs (.zip, .rar, .7z).
 * Attaches mandatory MixMint platform metadata to R2 objects.
 */
export async function POST(req: Request) {
    let user: any = null;
    try {
        /* ─────────────────────────────────────────────────────────────
           1. AUTHENTICATION & AUTHORIZATION (PHASE H1)
        ───────────────────────────────────────────────────────────── */
        user = await requireAuth();
        await requireDJ(user.id);

        // --- RATE LIMITING ---
        const ip = getClientIp(req);
        const rl = await checkRateLimit("dj_upload", ip, 20, 3600); // 20 uploads per hour
        if (!rl.success) {
            return fail("Too many upload attempts. Please wait an hour.", 429, "UPLOAD");
        }

        // Fetch profile for additional metadata (fullname) and activation
        const { data: coreProfile, error: coreError } = await supabaseServer
            .from("profiles")
            .select("role, full_name")
            .eq("id", user.id)
            .single();

        if (coreError || !coreProfile) {
            return fail("Profile not found", 404, "UPLOAD");
        }

        // Validate full_name exists (required for storage path)
        if (!coreProfile.full_name) {
            return fail("Profile incomplete: full_name required", 400, "UPLOAD");
        }

        // 1c. Self-Healing DJ Profile activation
        const { data: djProfile, error: profileError } = await supabaseServer
            .from("dj_profiles")
            .select("id, status")
            .eq("user_id", user.id)
            .single();

        let finalDjProfileId = djProfile?.id;

        if (profileError || !djProfile || djProfile.status !== "approved") {
            // Invisible Activation: Create or Update to approved if core role is DJ
            logger.info("UPLOAD", "Self-healing DJ profile activation", { user: user.email });

            const profileData = {
                user_id: user.id,
                dj_name: user.email?.split("@")[0] || "DJ " + user.id.slice(0, 4),
                slug: djProfile ? undefined : `dj-${user.id.slice(0, 8)}`, // Only set slug on insert
                status: "approved",
                bio: "Professional DJ",
            };

            const { data: activated, error: activateErr } = await supabaseServer
                .from("dj_profiles")
                .upsert(profileData, { onConflict: 'user_id' })
                .select("id")
                .single();

            if (activateErr || !activated) {
                logger.error("UPLOAD", "DJ profile activation failed", activateErr, { user: user.id });
                return fail("Failed to activate DJ profile", 500, "UPLOAD");
            }
            finalDjProfileId = activated.id;
        }

        /* ─────────────────────────────────────────────────────────────
           2. FORM DATA PARSING & VALIDATION
        ───────────────────────────────────────────────────────────── */
        const formData = await req.formData();
        const file = formData.get("file") as File;
        const title = formData.get("title") as string;
        const price = Number(formData.get("price"));
        const description = formData.get("description") as string | null;
        const contentTypeParam = formData.get("content_type") as string;
        const isFanOnly = formData.get("is_fan_only") === "true";

        if (!file || !(file instanceof File)) {
            return fail("No file provided or invalid file input", 400, "UPLOAD");
        }

        if (!title || isNaN(price)) {
            return fail("Missing title or price", 400, "UPLOAD");
        }

        /* ─────────────────────────────────────────────────────────────
           3. FILE VALIDATION & ISOLATION
        ───────────────────────────────────────────────────────────── */
        const fileName = file.name;
        const fileExt = fileName.split(".").pop()?.toLowerCase();
        const allowedZipExt = ["zip", "rar", "7z"];

        // Determine if it's an album pack (ZIP) or a track based on extension or param
        const isZip = allowedZipExt.includes(fileExt || "") || contentTypeParam === "zip";
        const folder = isZip ? "zips" : "tracks";

        // STRICT ZIP VALIDATION (PHASE 3.2 - BOUNDARY CONTROL)
        if (isZip) {
            // MIME type validation (varies by OS/browser)
            const allowedZipTypes = [
                "application/zip",
                "application/x-zip-compressed",
                "application/octet-stream", // some browsers
                "application/x-rar-compressed",
                "application/x-7z-compressed",
            ];

            if (!allowedZipTypes.includes(file.type)) {
                return fail(`Invalid MIME type for ZIP: ${file.type}. Only ZIP/RAR/7Z allowed.`, 400, "UPLOAD");
            }

            // ZIP size limit: 500MB
            const MAX_ZIP_SIZE = 500 * 1024 * 1024;
            if (file.size > MAX_ZIP_SIZE) {
                return fail("ZIP too large (max 500MB)", 400, "UPLOAD");
            }
        }

        // Strict validation for extension mismatch
        if (contentTypeParam === "zip" && !allowedZipExt.includes(fileExt || "")) {
            return fail("Only ZIP, RAR, or 7Z files are allowed for album packs", 400, "UPLOAD");
        }

        /* ─────────────────────────────────────────────────────────────
           4. R2 UPLOAD WITH METADATA (PHASE 3.2 - NON-NEGOTIABLE)
        ───────────────────────────────────────────────────────────── */
        const buffer = Buffer.from(await file.arrayBuffer());
        const timestamp = Date.now();
        // NEW PATH FORMAT: <dj_slug>_<dj_id>/tracks|albums/<timestamp>-<filename>
        const fileKey = getDJStoragePath(
            coreProfile.full_name,
            user.id,
            isZip ? "albums" : "tracks",
            fileName
        );

        // Debug logging to track duplicate uploads
        const uploadId = `${timestamp}-${Math.random().toString(36).substring(7)}`;
        logger.info("UPLOAD", "Upload started", { uploadId, user: user.email, fileName, type: isZip ? 'ZIP' : 'TRACK' });

        const metadata = {
            "platform": "MixMint",
            "platform_url": "https://mixmint.site",
            "upload_source": "MixMint DJ Upload",
            "dj_id": user.id,
            "uploaded_at": new Date().toISOString(),
            "content_type": isZip ? "album_pack" : "track",  // 🚨 Legal + Audit Trail
            "is_fan_only": isFanOnly.toString(),
        };

        await r2.send(
            new PutObjectCommand({
                Bucket: process.env.R2_BUCKET_NAME!,
                Key: fileKey,
                Body: buffer,
                ContentType: file.type || "application/octet-stream",
                Metadata: metadata,
            })
        );

        logger.info("UPLOAD", "R2 upload success", { uploadId, fileKey });

        /* ─────────────────────────────────────────────────────────────
           5. DATABASE PERSISTENCE (PHASE 3)
           CRITICAL FK CONSTRAINTS:
           - album_packs.dj_id → profiles.id (use user.id)
           - tracks.dj_id → dj_profiles.id (use finalDjProfileId)
        ───────────────────────────────────────────────────────────── */
        if (isZip) {
            const { error: dbError } = await supabaseServer.from("album_packs").insert({
                dj_id: user.id,  // ✅ FK to profiles.id
                title,
                description,
                price,
                file_key: fileKey,
                file_size: file.size,
                is_fan_only: isFanOnly,
                created_at: new Date().toISOString(),
            });

            if (dbError) throw dbError;
        } else {
            const { error: dbError } = await supabaseServer.from("tracks").insert({
                dj_id: finalDjProfileId,  // ✅ FK to dj_profiles.id
                title,
                price,
                file_key: fileKey,
                is_fan_only: isFanOnly,
                created_at: new Date().toISOString(),
            });

            if (dbError) throw dbError;
        }

        return ok({
            success: true,
            fileKey,
            message: `${isZip ? "Album pack" : "Track"} uploaded successfully`,
        });

    } catch (err: any) {
        if (err.message === "UNAUTHORIZED") {
            return fail("Unauthorized", 401, "UPLOAD");
        }
        if (err.message === "FORBIDDEN") {
            return fail("DJ access required", 403, "UPLOAD");
        }

        logger.error("UPLOAD", "DJ upload failure", err, { userId: user?.id });
        return fail(err.message || "Internal server error", 500, "UPLOAD");
    }
}
