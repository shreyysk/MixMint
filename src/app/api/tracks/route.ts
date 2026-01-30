import { NextResponse } from "next/server";
import { supabase } from "@/app/lib/supabaseClient";

export async function POST(req: Request) {
  const authHeader = req.headers.get("authorization");
  if (!authHeader) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const token = authHeader.replace("Bearer ", "");
  const { data: userData } = await supabase.auth.getUser(token);

  if (!userData?.user) {
    return NextResponse.json({ error: "Invalid user" }, { status: 401 });
  }

  const body = await req.json();

  const { title, price, youtube_url, file_key } = body;

  const { data: dj } = await supabase
    .from("dj_profiles")
    .select("id")
    .eq("user_id", userData.user.id)
    .eq("status", "approved")
    .single();

  if (!dj) {
    return NextResponse.json({ error: "Not a DJ" }, { status: 403 });
  }

  const { error } = await supabase.from("tracks").insert({
    dj_id: dj.id,
    title,
    price,
    youtube_url,
    file_key,
  });

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 400 });
  }

  return NextResponse.json({ success: true });
}
