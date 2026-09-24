"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/context/auth";
import { profilesApi, submissionsApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Alert } from "@/components/ui/alert";
import { Navbar } from "@/components/navbar";

const MAX_BYTES = 10 * 1024 * 1024; // 10 MB

export default function SubmitPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [loading, user, router]);

  const { data: profiles } = useQuery({
    queryKey: ["profiles"],
    queryFn: () => profilesApi.list().then((r) => r.data),
    enabled: !!user,
  });

  const [profileId, setProfileId] = useState<number | "">("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFile = (f: File | null) => {
    if (!f) { setFile(null); return; }
    if (f.size > MAX_BYTES) {
      setError("File exceeds the 10 MB limit.");
      setFile(null);
      if (fileRef.current) fileRef.current.value = "";
      return;
    }
    const ext = f.name.split(".").pop()?.toLowerCase();
    if (!["pdf", "docx"].includes(ext ?? "")) {
      setError("Only PDF and DOCX files are accepted.");
      setFile(null);
      if (fileRef.current) fileRef.current.value = "";
      return;
    }
    setError("");
    setFile(f);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!profileId || !file) { setError("Select a job profile and attach a file."); return; }
    setError("");
    setSubmitting(true);
    try {
      const { data } = await submissionsApi.submit(Number(profileId), file);
      router.push(`/submissions/${data.id}`);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? "Submission failed. Please try again.");
      setSubmitting(false);
    }
  };

  if (loading || !user) return null;

  const activeProfiles = profiles?.filter((p) => p.is_active) ?? [];

  return (
    <div className="flex flex-col min-h-screen">
      <Navbar />
      <main className="flex-1 max-w-lg mx-auto w-full px-4 py-10 space-y-6">
        <h1 className="text-2xl font-bold">Submit Resume</h1>

        {error && <Alert variant="destructive">{error}</Alert>}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-2">
            <Label>Job Profile</Label>
            {activeProfiles.length === 0 ? (
              <p className="text-sm text-muted-foreground">No active job profiles available.</p>
            ) : (
              <div className="space-y-2">
                {activeProfiles.map((p) => (
                  <label
                    key={p.id}
                    className={`flex items-start gap-3 rounded-lg border p-3 cursor-pointer transition-colors ${
                      profileId === p.id ? "border-foreground bg-muted/40" : "hover:bg-muted/20"
                    }`}
                  >
                    <input
                      type="radio"
                      name="profile"
                      value={p.id}
                      checked={profileId === p.id}
                      onChange={() => setProfileId(p.id)}
                      className="mt-0.5"
                    />
                    <div>
                      <p className="font-medium text-sm">{p.title}</p>
                      {p.description && (
                        <p className="text-xs text-muted-foreground mt-0.5">{p.description}</p>
                      )}
                      <p className="text-xs text-muted-foreground mt-1">
                        {p.requirements.length} requirement{p.requirements.length !== 1 ? "s" : ""}
                      </p>
                    </div>
                  </label>
                ))}
              </div>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="resume">Resume (PDF or DOCX, max 10 MB)</Label>
            <div
              className="rounded-lg border-2 border-dashed p-8 text-center cursor-pointer hover:bg-muted/20 transition-colors"
              onClick={() => fileRef.current?.click()}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                handleFile(e.dataTransfer.files[0] ?? null);
              }}
            >
              {file ? (
                <div className="space-y-1">
                  <p className="text-sm font-medium">{file.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {(file.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                  <button
                    type="button"
                    className="text-xs text-destructive underline"
                    onClick={(e) => { e.stopPropagation(); setFile(null); if (fileRef.current) fileRef.current.value = ""; }}
                  >
                    Remove
                  </button>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Drag & drop or click to select
                </p>
              )}
            </div>
            <input
              ref={fileRef}
              id="resume"
              type="file"
              accept=".pdf,.docx"
              className="hidden"
              onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
            />
          </div>

          <Button type="submit" className="w-full" disabled={submitting || !profileId || !file}>
            {submitting ? "Submitting…" : "Submit Resume"}
          </Button>
        </form>
      </main>
    </div>
  );
}
