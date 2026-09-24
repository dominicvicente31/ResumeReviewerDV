"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/auth";
import { profilesApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Alert } from "@/components/ui/alert";
import { Navbar } from "@/components/navbar";

interface Req { text: string; weight: number; must_have: boolean }

export default function NewProfilePage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && (!user || user.role !== "admin")) router.push("/dashboard");
  }, [loading, user, router]);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [requirements, setRequirements] = useState<Req[]>([
    { text: "", weight: 1, must_have: false },
  ]);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const addReq = () =>
    setRequirements((r) => [...r, { text: "", weight: 1, must_have: false }]);

  const removeReq = (i: number) =>
    setRequirements((r) => r.filter((_, idx) => idx !== i));

  const updateReq = (i: number, patch: Partial<Req>) =>
    setRequirements((r) => r.map((req, idx) => (idx === i ? { ...req, ...patch } : req)));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) { setError("Title is required."); return; }
    const filled = requirements.filter((r) => r.text.trim());
    if (filled.length === 0) { setError("Add at least one requirement."); return; }
    setError("");
    setSaving(true);
    try {
      await profilesApi.create({ title, description, requirements: filled });
      router.push("/admin/profiles");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? "Failed to create profile.");
      setSaving(false);
    }
  };

  if (loading || !user) return null;

  return (
    <div className="flex flex-col min-h-screen">
      <Navbar />
      <main className="flex-1 max-w-2xl mx-auto w-full px-4 py-10 space-y-6">
        <h1 className="text-2xl font-bold">New Job Profile</h1>

        {error && <Alert variant="destructive">{error}</Alert>}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-4 rounded-lg border p-4">
            <div className="space-y-1">
              <Label>Title</Label>
              <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Senior Software Engineer" />
            </div>
            <div className="space-y-1">
              <Label>Description <span className="text-muted-foreground">(optional)</span></Label>
              <Textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} />
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label>Requirements</Label>
              <Button type="button" variant="outline" size="sm" onClick={addReq}>
                + Add
              </Button>
            </div>

            {requirements.map((req, i) => (
              <div key={i} className="rounded-lg border p-3 space-y-2">
                <div className="flex gap-2">
                  <Textarea
                    rows={2}
                    className="flex-1"
                    placeholder="Describe the requirement…"
                    value={req.text}
                    onChange={(e) => updateReq(i, { text: e.target.value })}
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => removeReq(i)}
                    className="self-start text-muted-foreground"
                  >
                    ✕
                  </Button>
                </div>
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <Label className="text-xs">Weight</Label>
                    <Input
                      type="number"
                      min={1}
                      max={10}
                      className="w-16 h-7 text-xs"
                      value={req.weight}
                      onChange={(e) => updateReq(i, { weight: Number(e.target.value) })}
                    />
                  </div>
                  <label className="flex items-center gap-1.5 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={req.must_have}
                      onChange={(e) => updateReq(i, { must_have: e.target.checked })}
                    />
                    <span className="text-xs">Must-have</span>
                  </label>
                </div>
              </div>
            ))}
          </div>

          <div className="flex gap-3">
            <Button type="submit" disabled={saving}>
              {saving ? "Saving…" : "Create Profile"}
            </Button>
            <Button type="button" variant="outline" onClick={() => router.back()}>
              Cancel
            </Button>
          </div>
        </form>
      </main>
    </div>
  );
}
