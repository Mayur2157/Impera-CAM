import { describe, expect, it } from "vitest";

import { jobPollInterval } from "@/api/hooks";
import { safeNext } from "@/auth/next";
import { checkFiles } from "@/features/upload/fileChecks";

import { formatDate, formatINR, parseApiDate, plural } from "./format";

describe("format", () => {
  it("groups rupees the Indian way", () => {
    expect(formatINR(1234567.8)).toBe("₹12,34,567.80");
    expect(formatINR(null)).toBe("—");
  });

  it("reads the API's naive timestamps as UTC", () => {
    expect(parseApiDate("2026-10-23T09:15:00")?.toISOString()).toBe("2026-10-23T09:15:00.000Z");
    expect(parseApiDate("2026-10-23T09:15:00+05:30")?.toISOString()).toBe("2026-10-23T03:45:00.000Z");
    expect(formatDate("not a date")).toBe("—");
  });

  it("pluralises", () => {
    expect(plural(1, "statement")).toBe("1 statement");
    expect(plural(1200, "statement")).toBe("1,200 statements");
  });
});

describe("job polling", () => {
  it("backs off from 2 s and never waits more than 10 s", () => {
    expect(jobPollInterval(0)).toBe(2000);
    expect(jobPollInterval(1)).toBe(2500);
    expect(jobPollInterval(50)).toBe(10000);
  });
});

describe("safeNext", () => {
  it("only follows paths inside the app", () => {
    expect(safeNext("/app/statements?page=2")).toBe("/app/statements?page=2");
    expect(safeNext("//evil.example")).toBe("/app");
    expect(safeNext("https://evil.example")).toBe("/app");
    expect(safeNext(null)).toBe("/app");
  });
});

describe("checkFiles", () => {
  const pdf = (name: string, mb: number) => new File([new Uint8Array(Math.round(mb * 1024 * 1024))], name);
  const limits = { maxFiles: 2, maxMb: 1 };

  it("accepts PDFs within the plan and explains every rejection", () => {
    const current = [pdf("a.pdf", 0.1)];
    const { accepted, rejected } = checkFiles(
      [pdf("notes.docx", 0.1), pdf("a.pdf", 0.1), pdf("big.PDF", 1.5), pdf("b.pdf", 0.1), pdf("c.pdf", 0.1)],
      current,
      limits,
    );
    expect(accepted.map((f) => f.name)).toEqual(["b.pdf"]);
    expect(rejected.map((r) => [r.name, r.reason])).toEqual([
      ["notes.docx", "isn't a PDF — only PDF bank statements can be analysed"],
      ["a.pdf", "is already in the list"],
      ["big.PDF", "is larger than your plan's 1 MB limit per file"],
      ["c.pdf", "wasn't added — your plan allows 2 files per upload"],
    ]);
  });

  it("leaves size and count to the server when the plan is unknown", () => {
    expect(checkFiles([pdf("x.pdf", 30)], [], null).accepted).toHaveLength(1);
  });
});
