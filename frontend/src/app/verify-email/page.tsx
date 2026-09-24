"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { authApi } from "@/lib/api";
import { buttonVariants } from "@/components/ui/button";

type State = "loading" | "success" | "error";

export default function VerifyEmailPage() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [state, setState] = useState<State>("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) { setState("error"); setMessage("No verification token found."); return; }
    authApi
      .verifyEmail(token)
      .then(({ data }) => { setState("success"); setMessage(data.detail); })
      .catch((err) => {
        setState("error");
        setMessage(err?.response?.data?.detail ?? "Invalid or expired verification link.");
      });
  }, [token]);

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm space-y-4 text-center">
        {state === "loading" && <p className="text-muted-foreground">Verifying…</p>}

        {state === "success" && (
          <>
            <div className="text-5xl">✓</div>
            <h1 className="text-2xl font-bold text-green-600">Email verified</h1>
            <p className="text-muted-foreground">{message}</p>
            <Link href="/dashboard" className={buttonVariants() + " w-full justify-center"}>
              Go to dashboard
            </Link>
          </>
        )}

        {state === "error" && (
          <>
            <div className="text-5xl">✕</div>
            <h1 className="text-2xl font-bold text-destructive">Verification failed</h1>
            <p className="text-muted-foreground">{message}</p>
            <Link href="/login" className={buttonVariants({ variant: "outline" }) + " w-full justify-center"}>
              Back to sign in
            </Link>
          </>
        )}
      </div>
    </div>
  );
}
