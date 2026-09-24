"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/context/auth";
import { profilesApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Navbar } from "@/components/navbar";

export default function EditProfilePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { user, loading } = useAuth();
  const router = useRouter();
  const qc = useQueryClient();

  useEffect(() => {
    if (!loading && (!user || user.role !== "admin")) router.push("/dashboard");
  }, [loading, user, router]);

  const { data: profile, isLoading } = useQuery({
    queryKey: ["profile", Number(id)],
    queryFn: () => profilesApi.get(Number(id)).then((r) => r.data),
    enabled: user?.role === "admin",
  });

  const [editingReq, setEditingReq] = useState<number | null>(null);
  const [weight, setWeight] = useState(1);
  const [mustHave, setMustHave] = useState(false);
  const [error, setError] = useState("");

  const patchReq = useMutation({
    mutationFn: ({ reqId, w, mh }: { reqId: number; w: number; mh: boolean }) =>
      profilesApi.patchRequirement(Number(id), reqId, { weight: w, must_have: mh }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["profile", Number(id)] });
      setEditingReq(null);
    },
    onError: () => setError("Failed to save changes."),
  });

  const toggleActive = useMutation({
    mutationFn: () => profilesApi.update(Number(id), { is_active: !profile!.is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["profile", Number(id)] }),
  });

  if (loading || !user) return null;

  return (
    <div className="flex flex-col min-h-screen">
      <Navbar />
      <main className="flex-1 max-w-3xl mx-auto w-full px-4 py-10 space-y-6">
        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => <div key={i} className="h-12 bg-muted rounded animate-pulse" />)}
          </div>
        ) : profile ? (
          <>
            <div className="flex items-start justify-between gap-4">
              <div>
                <h1 className="text-2xl font-bold">{profile.title}</h1>
                {profile.description && (
                  <p className="text-muted-foreground text-sm mt-1">{profile.description}</p>
                )}
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <Badge variant={profile.is_active ? "default" : "secondary"}>
                  {profile.is_active ? "Active" : "Inactive"}
                </Badge>
                <Button variant="outline" size="sm" onClick={() => toggleActive.mutate()}>
                  {profile.is_active ? "Deactivate" : "Activate"}
                </Button>
              </div>
            </div>

            {error && <Alert variant="destructive">{error}</Alert>}

            <div className="space-y-3">
              <h2 className="font-semibold text-sm uppercase tracking-wide text-muted-foreground">
                Requirements
              </h2>
              {profile.requirements.map((req) => (
                <div key={req.id} className="rounded-lg border p-4 space-y-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1 flex-1">
                      <p className="text-sm">{req.text}</p>
                      <div className="flex items-center gap-3 text-xs text-muted-foreground">
                        <span>Weight: <strong>{req.weight}</strong></span>
                        {req.must_have && (
                          <span className="font-semibold text-foreground">Must-have</span>
                        )}
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setEditingReq(req.id);
                        setWeight(req.weight);
                        setMustHave(req.must_have);
                        setError("");
                      }}
                    >
                      Edit
                    </Button>
                  </div>

                  {editingReq === req.id && (
                    <div className="flex items-center gap-4 pt-2 border-t">
                      <div className="flex items-center gap-2">
                        <Label className="text-xs">Weight</Label>
                        <Input
                          type="number"
                          min={1}
                          max={10}
                          className="w-16 h-7 text-xs"
                          value={weight}
                          onChange={(e) => setWeight(Number(e.target.value))}
                        />
                      </div>
                      <label className="flex items-center gap-1.5 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={mustHave}
                          onChange={(e) => setMustHave(e.target.checked)}
                        />
                        <span className="text-xs">Must-have</span>
                      </label>
                      <div className="flex gap-2 ml-auto">
                        <Button
                          size="sm"
                          onClick={() => patchReq.mutate({ reqId: req.id, w: weight, mh: mustHave })}
                          disabled={patchReq.isPending}
                        >
                          Save
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setEditingReq(null)}
                        >
                          Cancel
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </>
        ) : (
          <p className="text-muted-foreground">Profile not found.</p>
        )}
      </main>
    </div>
  );
}
