"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { useAuth } from "@/lib/AuthContext";

export default function DJApplyPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    dj_name: "",
    slug: "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const res = await fetch("/api/dj/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });

      const data = await res.json();

      if (!res.ok) throw new Error(data.error || "Failed to submit application");

      alert("Application submitted! Redirecting to dashboard...");
      router.push("/dashboard");
    } catch (err: any) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-black">
        <p className="text-white">Please login to apply as a DJ.</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black pt-20 pb-12 px-4">
      <div className="max-w-md mx-auto">
        <Card className="bg-zinc-900 border-zinc-800 text-white">
          <CardHeader>
            <CardTitle className="text-2xl text-mint-studio">Become a MixMint Partner DJ</CardTitle>
            <p className="text-zinc-400 text-sm">
              Apply to start selling your tracks and subscriptions.
            </p>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="dj_name">DJ Name</Label>
                <Input
                  id="dj_name"
                  placeholder="e.g. DJ Minty"
                  className="bg-zinc-800 border-zinc-700 text-white"
                  value={formData.dj_name}
                  onChange={(e) => setFormData({ ...formData, dj_name: e.target.value })}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="slug">Profile URL Slug</Label>
                <div className="flex items-center gap-2">
                  <span className="text-zinc-500 text-sm">mixmint.site/dj/</span>
                  <Input
                    id="slug"
                    placeholder="dj-minty"
                    className="bg-zinc-800 border-zinc-700 text-white"
                    value={formData.slug}
                    onChange={(e) => setFormData({ ...formData, slug: e.target.value.toLowerCase().replace(/\s+/g, '-') })}
                    required
                  />
                </div>
                <p className="text-xs text-zinc-500">This will be your public storefront URL.</p>
              </div>

              <Button
                type="submit"
                className="w-full bg-mint-studio hover:bg-mint-studio/90 text-black font-bold"
                disabled={loading}
              >
                {loading ? "Submitting..." : "Submit Application"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
