import { NextResponse } from "next/server";
import { PutObjectCommand } from "@aws-sdk/client-s3";
import { r2 } from "@/app/lib/r2Client";
import { supabase } from "@/app/lib/supabaseClient";

export async function POST(req: Request) {
  try {
    const authHeader = req.headers.get("authorization");
    if (!authHeader) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const token = authHeader.replace("Bearer ", "");
    const { data: userData } = await supabase.auth.getUser(token);

    if (!userData?.user) {
      return NextResponse.json({ error: "Invalid session" }, { status: 401 });
    }

    const { data: profile } = await supabase
      .from("profiles")
      .select("role")
      .eq("id", userData.user.id)
      .single();

    if (profile?.role !== "dj" && profile?.role !== "admin") {
      return NextResponse.json({ error: "Not allowed" }, { status: 403 });
    }

    const formData = await req.formData();
    const file = formData.get("file") as File;

    if (!file) {
      return NextResponse.json({ error: "No file provided" }, { status: 400 });
    }

    const allowed = ["audio/mpeg", "audio/wav", "application/zip"];
    if (!allowed.includes(file.type)) {
      return NextResponse.json({ error: "Invalid file type" }, { status: 400 });
    }

    const buffer = Buffer.from(await file.arrayBuffer());
    const fileKey = `uploads/${userData.user.id}/${Date.now()}-${file.name}`;

    await r2.send(
      new PutObjectCommand({
        Bucket: process.env.R2_BUCKET_NAME!,
        Key: fileKey,
        Body: buffer,
        ContentType: file.type,
      })
    );

    return NextResponse.json({ fileKey });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
