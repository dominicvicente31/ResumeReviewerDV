"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/context/auth";
import { submissionsApi } from "@/lib/api";
import { scoreColor } from "@/lib/score";
import { buttonVariants } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Navbar } from "@/components/navbar";
import type { SubmissionListItem } from "@/types";

function statusBadge(status: SubmissionListItem["status"]) {
  const variants: Record<string, string> = {
    pending: "bg-muted text-muted-foreground",
    processing: "bg-amber-100 text-amber-700",
    completed: "bg-green-100 text-green-700",
    failed: "bg-red-100 text-red-700",
  };
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${variants[status]}`}>
      {status}
    </span>
  );
}

export default function DashboardPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [loading, user, router]);

  const { data: submissions, isLoading } = useQuery({
    queryKey: ["submissions", "mine"],
    queryFn: () => submissionsApi.mine().then((r) => r.data),
    enabled: !!user,
  });

  if (loading || !user) return null;

  return (
    <div className="flex flex-col min-h-screen">
      <Navbar />
      <main className="flex-1 max-w-4xl mx-auto w-full px-4 py-10 space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">My Submissions</h1>
          <Link href="/submit" className={buttonVariants()}>
            Submit Resume
          </Link>
        </div>

        {!user.is_verified && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-700">
            Your email is not verified. Check your inbox or{" "}
            <button
              className="underline"
              onClick={() =>
                fetch("/api/resend-verification", { method: "POST" })
              }
            >
              resend the link
            </button>
            .
          </div>
        )}

        {isLoading && (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 rounded-lg bg-muted animate-pulse" />
            ))}
          </div>
        )}

        {!isLoading && submissions?.length === 0 && (
          <div className="text-center py-20 text-muted-foreground">
            No submissions yet.{" "}
            <Link href="/submit" className="underline">
              Submit your resume
            </Link>{" "}
            to get started.
          </div>
        )}

        {!isLoading && submissions && submissions.length > 0 && (
          <div className="divide-y rounded-lg border">
            {submissions.map((s) => (
              <Link
                key={s.id}
                href={`/submissions/${s.id}`}
                className="flex items-center justify-between px-4 py-3 hover:bg-muted/40 transition-colors"
              >
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">
                      Submission #{s.id}
                    </span>
                    {statusBadge(s.status)}
                    {s.capped_by_must_have && (
                      <Badge variant="destructive" className="text-xs">
                        Must-have failed
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {new Date(s.created_at).toLocaleString()}
                  </p>
                </div>
                <div className={`text-2xl font-bold ${scoreColor(s.overall_score, s.capped_by_must_have)}`}>
                  {s.overall_score !== null ? `${Math.round(s.overall_score)}` : "—"}
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
