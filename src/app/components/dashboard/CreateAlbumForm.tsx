
"use client";

import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Input } from "@/app/components/ui/Input";
import { Button } from "@/app/components/ui/Button";
import { supabase } from "@/app/lib/supabaseClient";
import { useAuth } from "@/app/lib/AuthContext";
import { useState, useEffect } from "react";
import { Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { Checkbox } from "@/app/components/ui/Checkbox";

const schema = z.object({
  title: z.string().min(1, "Title is required"),
  price: z.preprocess((a) => parseFloat(z.string().parse(a)), z.number().positive("Price must be a positive number")),
  track_ids: z.array(z.string()).min(1, "Select at least one track")
});

interface Track {
    id: string;
    title: string;
}

export function CreateAlbumForm() {
    const { user } = useAuth();
    const router = useRouter();
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [tracks, setTracks] = useState<Track[]>([]);
    const { register, handleSubmit, control, formState: { errors } } = useForm({
        resolver: zodResolver(schema),
        defaultValues: {
            track_ids: []
        }
    });

    useEffect(() => {
        if(user) fetchTracks();
    }, [user]);

    async function fetchTracks() {
         if (!user) return;
        const { data: djProfile, error: djError } = await supabase
            .from('dj_profiles')
            .select('id')
            .eq('user_id', user.id)
            .single();
        
        if(djError || !djProfile) return;

        const { data, error } = await supabase
            .from("tracks")
            .select("id, title")
            .eq("dj_id", djProfile.id)
            .eq('status', 'active');
        if(data) setTracks(data);
    }

    const onSubmit = async (data: any) => {
        if (!user) return;
        setIsSubmitting(true);

        const { data: djProfile, error: djError } = await supabase
            .from('dj_profiles')
            .select('id')
            .eq('user_id', user.id)
            .single();

        if (djError || !djProfile) {
            alert("Could not find your DJ profile.");
            setIsSubmitting(false);
            return;
        }

        const { data: albumData, error: albumError } = await supabase.from('album_packs').insert({
            title: data.title,
            price: data.price,
            dj_id: djProfile.id,
        }).select().single();

        if (albumError || !albumData) {
            console.error("Album creation error:", albumError);
            alert("Error creating album.");
            setIsSubmitting(false);
            return;
        }

        const trackAlbumRelations = data.track_ids.map((track_id: string) => ({
            album_id: albumData.id,
            track_id: track_id
        }));

        const { error: relationError } = await supabase.from('album_tracks').insert(trackAlbumRelations);

        if (relationError) {
            console.error("Album track relation error:", relationError);
            alert("Error associating tracks with album.");
        } else {
            alert("Album created successfully!");
            router.push("/dashboard");
        }

        setIsSubmitting(false);
    };

    return (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            <div>
                <label htmlFor="title" className="block text-sm font-medium text-zinc-300">Album Title</label>
                <Input id="title" {...register("title")} />
                {errors.title && <p className="text-red-500 text-sm mt-1">{errors.title.message as string}</p>}
            </div>

            <div>
                <label htmlFor="price" className="block text-sm font-medium text-zinc-300">Album Price ($)</label>
                <Input id="price" type="number" step="0.01" {...register("price")} />
                {errors.price && <p className="text-red-500 text-sm mt-1">{errors.price.message as string}</p>}
            </div>

             <div>
                <label className="block text-sm font-medium text-zinc-300">Select Tracks</label>
                 <Controller
                    name="track_ids"
                    control={control}
                    render={({ field }) => (
                        <div className="space-y-2 pt-2">
                            {tracks.map(track => (
                                <div key={track.id} className="flex items-center gap-2">
                                    <Checkbox 
                                        id={`track-${track.id}`}
                                        checked={field.value?.includes(track.id)}
                                        onCheckedChange={(checked) => {
                                            return checked 
                                                ? field.onChange([...field.value, track.id]) 
                                                : field.onChange(field.value?.filter(id => id !== track.id))
                                        }}
                                    />
                                    <label htmlFor={`track-${track.id}`} className="text-sm text-zinc-200">{track.title}</label>
                                </div>
                            ))}
                        </div>
                    )}
                />
                {errors.track_ids && <p className="text-red-500 text-sm mt-1">{errors.track_ids.message as string}</p>}
            </div>

            <Button type="submit" disabled={isSubmitting}>
                {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} 
                Create Album
            </Button>
        </form>
    )
}
