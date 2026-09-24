import type { Verdict } from "@/types";

export function scoreColor(score: number | null, capped = false): string {
  if (score === null) return "text-muted-foreground";
  if (capped || score < 50) return "text-red-500";
  if (score < 80) return "text-amber-500";
  return "text-green-500";
}

export function scoreBg(score: number | null, capped = false): string {
  if (score === null) return "bg-muted";
  if (capped || score < 50) return "bg-red-500";
  if (score < 80) return "bg-amber-500";
  return "bg-green-500";
}

export function verdictColor(verdict: Verdict): string {
  if (verdict === "met") return "text-green-600 bg-green-50 border-green-200";
  if (verdict === "partial") return "text-amber-600 bg-amber-50 border-amber-200";
  return "text-red-600 bg-red-50 border-red-200";
}

export function verdictLabel(verdict: Verdict): string {
  if (verdict === "met") return "Met";
  if (verdict === "partial") return "Partial";
  return "Not Met";
}
