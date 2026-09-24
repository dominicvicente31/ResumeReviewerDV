"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/context/auth";
import { submissionsApi } from "@/lib/api";
import { scoreColor } from "@/lib/score";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Navbar } from "@/components/navbar";

export default function AdminSubmissionsPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const qc = useQueryClient();

  useEffect(() => {
    if (!loading && (!user || user.role !== "admin")) router.push("/dashboard");
  }, [loading, user, router]);

  const { data: submissions, isLoading } = useQuery({
    queryKey: ["submissions", "all"],
    queryFn: () => submissionsApi.all().then((r) => r.data),
    enabled: user?.role === "admin",
  });

  const rescore = useMutation({
    mutationFn: (id: number) => submissionsApi.rescore(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["submissions"] }),
  });

  if (loading || !user) return null;

  return (
    <div className="flex flex-col min-h-screen">
      <Navbar />
      <main className="flex-1 max-w-5xl mx-auto w-full px-4 py-10 space-y-6">
        <h1 className="text-2xl font-bold">All Submissions</h1>

        {isLoading && (
          <div className="space-y-2">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-14 rounded-lg bg-muted animate-pulse" />
            ))}
          </div>
        )}

        {!isLoading && submissions?.length === 0 && (
          <p className="text-muted-foreground text-sm">No submissions yet.</p>
        )}

        {!isLoading && submissions && submissions.length > 0 && (
          <div className="rounded-lg border divide-y">
            <div className="grid grid-cols-[1fr_auto_auto_auto_auto] gap-4 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              <span>ID / Date</span>
              <span>Profile</span>
              <span>Status</span>
              <span className="text-right">Score</span>
              <span />
            </div>
            {submissions.map((s) => (
              <div
                key={s.id}
                className="grid grid-cols-[1fr_auto_auto_auto_auto] gap-4 items-center px-4 py-3"
              >
                <div>
                  <Link href={`/submissions/${s.id}`} className="text-sm font-medium hover:underline">
                    #{s.id}
                  </Link>
                  <p className="text-xs text-muted-foreground">
                    {new Date(s.created_at).toLocaleString()}
                  </p>
                </div>
                <span className="text-xs text-muted-foreground">#{s.job_profile_id}</span>
                <span className="text-xs capitalize">{s.status}</span>
                <div className="text-right">
                  <span className={`text-lg font-bold ${scoreColor(s.overall_score, s.capped_by_must_have)}`}>
                    {s.overall_score !== null ? Math.round(s.overall_score) : "—"}
                  </span>
                  {s.capped_by_must_have && (
                    <Badge variant="destructive" className="ml-1 text-xs">
                      Capped
                    </Badge>
                  )}
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={
                    s.status === "pending" ||
                    s.status === "processing" ||
                    rescore.isPending
                  }
                  onClick={() => rescore.mutate(s.id)}
                >
                  Rescore
                </Button>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
