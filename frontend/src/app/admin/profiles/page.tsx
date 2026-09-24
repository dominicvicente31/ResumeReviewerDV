"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/context/auth";
import { profilesApi } from "@/lib/api";
import { Button, buttonVariants } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Navbar } from "@/components/navbar";

export default function AdminProfilesPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const qc = useQueryClient();

  useEffect(() => {
    if (!loading && (!user || user.role !== "admin")) router.push("/dashboard");
  }, [loading, user, router]);

  const { data: profiles, isLoading } = useQuery({
    queryKey: ["profiles", "all"],
    queryFn: () => profilesApi.list().then((r) => r.data),
    enabled: user?.role === "admin",
  });

  const toggle = useMutation({
    mutationFn: ({ id, is_active }: { id: number; is_active: boolean }) =>
      profilesApi.update(id, { is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["profiles"] }),
  });

  if (loading || !user) return null;

  return (
    <div className="flex flex-col min-h-screen">
      <Navbar />
      <main className="flex-1 max-w-4xl mx-auto w-full px-4 py-10 space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Job Profiles</h1>
          <Link href="/admin/profiles/new" className={buttonVariants()}>
            New Profile
          </Link>
        </div>

        {isLoading && (
          <div className="space-y-3">
            {[1, 2].map((i) => (
              <div key={i} className="h-20 rounded-lg bg-muted animate-pulse" />
            ))}
          </div>
        )}

        {!isLoading && profiles?.length === 0 && (
          <p className="text-muted-foreground text-sm">No profiles yet. Create one to get started.</p>
        )}

        <div className="divide-y rounded-lg border">
          {profiles?.map((p) => (
            <div key={p.id} className="flex items-center justify-between px-4 py-3">
              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-sm">{p.title}</span>
                  <Badge variant={p.is_active ? "default" : "secondary"}>
                    {p.is_active ? "Active" : "Inactive"}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground">
                  {p.requirements.length} requirement{p.requirements.length !== 1 ? "s" : ""}
                  {p.description ? ` · ${p.description}` : ""}
                </p>
              </div>
              <div className="flex gap-2">
                <Link href={`/admin/profiles/${p.id}`} className={buttonVariants({ variant: "outline", size: "sm" })}>
                  Edit
                </Link>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => toggle.mutate({ id: p.id, is_active: !p.is_active })}
                >
                  {p.is_active ? "Deactivate" : "Activate"}
                </Button>
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
