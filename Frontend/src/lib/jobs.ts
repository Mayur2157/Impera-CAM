import type { Job, RiskRating } from "@/lib/api/types";

const ORDER: RiskRating[] = ["PRIME", "MODERATE-LOW", "MODERATE", "HIGH", "VERY HIGH"];

export function bestChain(j: Job): number | null {
  const v = j.files.map((f) => f.result?.chain).filter((x): x is number => x != null);
  return v.length ? Math.max(...v) : null;
}

export function worstGrade(j: Job): RiskRating | null {
  const v = j.files.map((f) => f.result?.risk_rating).filter((x): x is RiskRating => !!x);
  if (!v.length) return null;
  return v.reduce((a, b) => (ORDER.indexOf(b) > ORDER.indexOf(a) ? b : a));
}
