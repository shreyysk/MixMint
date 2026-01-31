import { supabase } from "@/app/lib/supabaseClient";

export async function downloadContent(
  contentId: string,
  contentType: "track" | "album" | "fan_upload"
) {
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) {
    alert("Please login to download");
    return;
  }

  // 1. Generate fresh token
  const res = await fetch("/api/download-token", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${session.access_token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      content_id: contentId,
      content_type: contentType,
    }),
  });

  const data = await res.json();

  if (!res.ok) {
    alert(data.error || "Unable to download");
    return;
  }

  // 2. Trigger download immediately
  window.location.href = `/api/download?token=${data.token}`;
}
