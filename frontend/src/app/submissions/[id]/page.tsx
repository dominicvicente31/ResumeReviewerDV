"use client";

import { use, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/context/auth";
import { profilesApi, submissionsApi } from "@/lib/api";
import { scoreColor, scoreBg, verdictColor, verdictLabel } from "@/lib/score";
import { Badge } from "@/components/ui/badge";
import { Navbar } from "@/components/navbar";
import type { Verdict } from "@/types";

function ScoreRing({ score, capped }: { score: number; capped: boolean }) {
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const fill = circumference - (score / 100) * circumference;
  const color = capped || score < 50 ? "#ef4444" : score < 80 ? "#f59e0b" : "#22c55e";

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width="140" height="140" className="-rotate-90">
        <circle cx="70" cy="70" r={radius} strokeWidth="10" stroke="#e5e7eb" fill="none" />
        <circle
          cx="70" cy="70" r={radius} strokeWidth="10" fill="none"
          stroke={color}
          strokeDasharray={circumference}
          strokeDashoffset={fill}
          strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 0.8s ease" }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className={`text-3xl font-bold ${scoreColor(score, capped)}`}>
          {Math.round(score)}
        </span>
        <span className="text-xs text-muted-foreground">/ 100</span>
      </div>
    </div>
  );
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const bg = pct >= 70 ? "bg-green-500" : pct >= 40 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
        <div className={`h-full rounded-full ${bg}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-muted-foreground w-8 text-right">{pct}%</span>
    </div>
  );
}

export default function SubmissionPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [loading, user, router]);

  const { data: submission } = useQuery({
    queryKey: ["submission", id],
    queryFn: () => submissionsApi.get(Number(id)).then((r) => r.data),
    enabled: !!user,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "pending" || status === "processing" ? 2000 : false;
    },
  });

  const { data: profile } = useQuery({
    queryKey: ["profile", submission?.job_profile_id],
    queryFn: () =>
      profilesApi.get(submission!.job_profile_id).then((r) => r.data),
    enabled: !!submission,
  });

  if (loading || !user) return null;

  const isPending =
    !submission ||
    submission.status === "pending" ||
    submission.status === "processing";

  const reqMap = new Map(profile?.requirements.map((r) => [r.id, r]));

  return (
    <div className="flex flex-col min-h-screen">
      <Navbar />
      <main className="flex-1 max-w-3xl mx-auto w-full px-4 py-10 space-y-8">
        {isPending ? (
          <div className="flex flex-col items-center justify-center py-32 gap-4">
            <div className="h-12 w-12 rounded-full border-4 border-muted border-t-foreground animate-spin" />
            <p className="text-muted-foreground font-medium">Analyzing your resume…</p>
            <p className="text-xs text-muted-foreground">This takes 20–40 seconds</p>
          </div>
        ) : submission.status === "failed" ? (
          <div className="text-center py-20 space-y-2">
            <p className="text-destructive font-semibold text-lg">Scoring failed</p>
            <p className="text-sm text-muted-foreground">
              Something went wrong. Please try submitting again.
            </p>
          </div>
        ) : (
          <>
            {/* Score header */}
            <div className="flex flex-col sm:flex-row items-center gap-6 rounded-xl border bg-card p-6">
              <ScoreRing
                score={submission.overall_score!}
                capped={submission.capped_by_must_have}
              />
              <div className="space-y-2 text-center sm:text-left">
                <h1 className="text-xl font-bold">
                  {profile?.title ?? `Submission #${id}`}
                </h1>
                <p className={`text-sm font-medium ${scoreColor(submission.overall_score, submission.capped_by_must_have)}`}>
                  {submission.capped_by_must_have
                    ? "Score capped — a must-have requirement was not met"
                    : submission.overall_score! >= 80
                    ? "Strong match"
                    : submission.overall_score! >= 50
                    ? "Partial match"
                    : "Weak match"}
                </p>
                <p className="text-xs text-muted-foreground">
                  {new Date(submission.created_at).toLocaleString()}
                </p>
              </div>
            </div>

            {/* Per-requirement results */}
            <div className="space-y-3">
              <h2 className="font-semibold text-sm uppercase tracking-wide text-muted-foreground">
                Requirements
              </h2>
              {submission.results.map((r) => {
                const req = reqMap.get(r.requirement_id);
                return (
                  <div
                    key={r.requirement_id}
                    className={`rounded-lg border p-4 space-y-3 ${verdictColor(r.verdict as Verdict)}`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="space-y-1 flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-medium text-sm">
                            {req?.text ?? `Requirement #${r.requirement_id}`}
                          </span>
                          {req?.must_have && (
                            <span className="text-xs font-semibold uppercase tracking-wide bg-foreground/10 px-1.5 py-0.5 rounded">
                              Must-have
                            </span>
                          )}
                        </div>
                        {req && (
                          <p className="text-xs opacity-70">
                            Weight: {req.weight}
                          </p>
                        )}
                      </div>
                      <span
                        className={`shrink-0 text-xs font-semibold px-2.5 py-1 rounded-full border ${verdictColor(r.verdict as Verdict)}`}
                      >
                        {verdictLabel(r.verdict as Verdict)}
                      </span>
                    </div>

                    {r.evidence && (
                      <blockquote className="border-l-2 pl-3 text-xs italic opacity-80">
                        {r.evidence}
                        {!r.evidence_verified && (
                          <span className="ml-1 not-italic opacity-60">(unverified)</span>
                        )}
                      </blockquote>
                    )}

                    <div className="space-y-1">
                      <p className="text-xs opacity-70">{r.rationale}</p>
                      <ConfidenceBar value={r.confidence} />
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
