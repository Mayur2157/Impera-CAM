export interface Limits {
  maxFiles: number;
  maxMb: number;
}

export interface Rejection {
  name: string;
  reason: string;
}

/**
 * Which picked files can join the upload. Mirrors the server's checks
 * (PDF only, size per file, files per job) so users hear early; the server
 * still decides — it also reads the file's first bytes and its password.
 */
export function checkFiles(
  picked: File[],
  current: File[],
  limits: Limits | null,
): { accepted: File[]; rejected: Rejection[] } {
  const accepted: File[] = [];
  const rejected: Rejection[] = [];
  const seen = new Set(current.map((f) => `${f.name}:${f.size}`));

  for (const f of picked) {
    const key = `${f.name}:${f.size}`;
    if (!f.name.toLowerCase().endsWith(".pdf")) {
      rejected.push({ name: f.name, reason: "isn't a PDF — only PDF bank statements can be analysed" });
    } else if (seen.has(key)) {
      rejected.push({ name: f.name, reason: "is already in the list" });
    } else if (limits && f.size > limits.maxMb * 1024 * 1024) {
      rejected.push({ name: f.name, reason: `is larger than your plan's ${limits.maxMb} MB limit per file` });
    } else if (limits && current.length + accepted.length >= limits.maxFiles) {
      rejected.push({
        name: f.name,
        reason: `wasn't added — your plan allows ${limits.maxFiles} files per upload`,
      });
    } else {
      accepted.push(f);
      seen.add(key);
    }
  }
  return { accepted, rejected };
}
