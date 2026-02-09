
"use client";

import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { supabase } from "@/lib/supabaseClient";
import { useAuth } from "@/lib/AuthContext";
import { useState } from "react";
import { Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";

const schema = z.object({
    title: z.string().min(1, "Title is required"),
    price: z.preprocess((a) => parseFloat(z.string().parse(a)), z.number().positive("Price must be a positive number")),
    youtube_url: z.string().url("Invalid YouTube URL").optional().or(z.literal('')),
    track_file: z.any().refine(files => files?.length == 1, "Track file is required.")
});


export function UploadTrackForm() {
    const { user } = useAuth();
    const router = useRouter();
    const [isSubmitting, setIsSubmitting] = useState(false);
    const { register, handleSubmit, control, formState: { errors } } = useForm({
        resolver: zodResolver(schema)
    });

    const onSubmit = async (data: any) => {
        if (!user) return;
        setIsSubmitting(true);

        const file = data.track_file[0];
        const fileName = `${user.id}/${Date.now()}-${file.name}`;

        const { data: fileData, error: fileError } = await supabase.storage
            .from('tracks')
            .upload(fileName, file, {
                cacheControl: "3600",
                upsert: false,
                metadata: {
                    dj_id: user.id,
                    platform: "MixMint",
                    platform_url: "https://mixmint.site",
                    uploaded_at: new Date().toISOString()
                }
            });

        if (fileError) {
            console.error("File upload error:", fileError);
            alert("Error uploading file.");
            setIsSubmitting(false);
            return;
        }

        const { data: djProfile, error: djError } = await supabase
            .from('dj_profiles')
            .select('id')
            .eq('user_id', user.id)
            .single();

        if (djError || !djProfile) {
            console.error("Error fetching DJ profile:", djError);
            alert("Could not find your DJ profile.");
            setIsSubmitting(false);
            return;
        }

        const { error: dbError } = await supabase.from('tracks').insert({
            title: data.title,
            price: data.price,
            youtube_url: data.youtube_url,
            dj_id: djProfile.id,
            file_key: fileData.path,
            status: 'active'
        });

        if (dbError) {
            console.error("Database insert error:", dbError);
            alert("Error creating track record.");
        } else {
            alert("Track uploaded successfully!");
            router.push("/dashboard");
        }
        setIsSubmitting(false);
    };

    return (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            <div>
                <label htmlFor="title" className="block text-sm font-medium text-zinc-300">Track Title</label>
                <Input id="title" {...register("title")} />
                {errors.title && <p className="text-red-500 text-sm mt-1">{errors.title.message as string}</p>}
            </div>

            <div>
                <label htmlFor="price" className="block text-sm font-medium text-zinc-300">Price (₹)</label>
                <Input id="price" type="number" step="0.01" {...register("price")} />
                {errors.price && <p className="text-red-500 text-sm mt-1">{errors.price.message as string}</p>}
            </div>

            <div>
                <label htmlFor="youtube_url" className="block text-sm font-medium text-zinc-300">YouTube Preview URL (Optional)</label>
                <Input id="youtube_url" {...register("youtube_url")} />
                {errors.youtube_url && <p className="text-red-500 text-sm mt-1">{errors.youtube_url.message as string}</p>}
            </div>

            <div>
                <label htmlFor="track_file" className="block text-sm font-medium text-zinc-300">Track File (MP3, WAV)</label>
                <Input id="track_file" type="file" accept=".mp3,.wav" {...register("track_file")} />
                {errors.track_file && <p className="text-red-500 text-sm mt-1">{errors.track_file.message as string}</p>}
            </div>

            <Button type="submit" disabled={isSubmitting}>
                {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Upload Track
            </Button>
        </form>
    )
}
