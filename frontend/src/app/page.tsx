"use client";

import Link from "next/link";
import { useAuth } from "@/context/auth";
import { buttonVariants } from "@/components/ui/button";
import { Navbar } from "@/components/navbar";

export default function LandingPage() {
  const { user } = useAuth();

  return (
    <div className="flex flex-col min-h-screen">
      <Navbar />
      <main className="flex-1 flex flex-col items-center justify-center px-4 text-center gap-6 py-24">
        <div className="max-w-2xl space-y-4">
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
            AI-Powered Resume Screening
          </h1>
          <p className="text-lg text-muted-foreground">
            Upload your resume and get an instant alignment score against job
            requirements — with per-requirement verdicts, evidence quotes, and
            confidence ratings backed by Claude AI.
          </p>
        </div>

        <div className="flex gap-3">
          {user ? (
            <Link href="/submit" className={buttonVariants({ size: "lg" })}>
              Submit Resume
            </Link>
          ) : (
            <>
              <Link href="/signup" className={buttonVariants({ size: "lg" })}>
                Get started
              </Link>
              <Link href="/login" className={buttonVariants({ size: "lg", variant: "outline" })}>
                Sign in
              </Link>
            </>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mt-8 text-left max-w-3xl w-full">
          {[
            {
              title: "Structured Scoring",
              body: "Weighted requirements with must-have flags. Missing a critical skill caps your score at 50.",
            },
            {
              title: "Evidence-Backed",
              body: "Every verdict includes a direct quote from your resume and a confidence rating derived from two independent AI runs.",
            },
            {
              title: "Async & Fast",
              body: "Results are queued and processed in parallel. Submit and check back — no waiting on the page.",
            },
          ].map(({ title, body }) => (
            <div key={title} className="rounded-lg border bg-card p-5 space-y-2">
              <h3 className="font-semibold">{title}</h3>
              <p className="text-sm text-muted-foreground">{body}</p>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
