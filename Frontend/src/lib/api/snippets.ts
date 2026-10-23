// Static code samples for the API docs, built from the contract only.
export const API_BASE_DISPLAY = ((import.meta.env["VITE_API_BASE_URL"] as string | undefined) || "https://api.your-impera-host.example").replace(/\/$/, "");
export const PLACEHOLDER_KEY = "icam_live_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX";

export type Lang = "curl" | "python" | "node" | "java";
export const LANGS: { id: Lang; label: string }[] = [
  { id: "curl", label: "cURL" }, { id: "python", label: "Python" }, { id: "node", label: "Node" }, { id: "java", label: "Java" },
];

const B = API_BASE_DISPLAY;

export const SNIPPETS: Record<Lang, string> = {
  curl: `# 1. Upload a statement
curl -X POST "${B}/api/v1/jobs" \\
  -H "X-API-Key: $IMPERA_API_KEY" \\
  -F "files[]=@statement.pdf" \\
  -F "use_ocr=true" -F "dpi=300"
# → {"job_id":"job_…","files":[…]}

# 2. Poll until status is "done" or "error" (wait 2–10 s between calls)
curl "${B}/api/v1/jobs/$JOB_ID" -H "X-API-Key: $IMPERA_API_KEY"

# 3. Fetch the CAM result for file 0
curl "${B}/api/v1/jobs/$JOB_ID/files/0/result" -H "X-API-Key: $IMPERA_API_KEY"

# 4. Download the Excel workbook
curl -o cam.xlsx "${B}/api/v1/jobs/$JOB_ID/files/0/download" -H "X-API-Key: $IMPERA_API_KEY"`,

  python: `import os, time, requests

BASE = "${B}"
H = {"X-API-Key": os.environ["IMPERA_API_KEY"]}

# 1. Upload
with open("statement.pdf", "rb") as f:
    r = requests.post(f"{BASE}/api/v1/jobs", headers=H,
                      files={"files[]": ("statement.pdf", f, "application/pdf")},
                      data={"use_ocr": "true", "dpi": "300"})
r.raise_for_status()
job_id = r.json()["job_id"]

# 2. Poll with backoff
delay = 2
while True:
    r = requests.get(f"{BASE}/api/v1/jobs/{job_id}", headers=H)
    if r.status_code == 429:
        time.sleep(int(r.headers.get("Retry-After", "10"))); continue
    r.raise_for_status()
    job = r.json()
    if job["status"] in ("done", "error"):
        break
    time.sleep(delay)
    delay = min(delay * 1.5, 10)

# 3. Result
cam = requests.get(f"{BASE}/api/v1/jobs/{job_id}/files/0/result", headers=H).json()
print(cam["score"]["credit_score_index"], cam["score"]["risk_rating"])

# 4. Excel
x = requests.get(f"{BASE}/api/v1/jobs/{job_id}/files/0/download", headers=H)
open("cam.xlsx", "wb").write(x.content)`,

  node: `import { readFile, writeFile } from "node:fs/promises";

const BASE = "${B}";
const H = { "X-API-Key": process.env.IMPERA_API_KEY };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// 1. Upload
const fd = new FormData();
fd.append("files[]", new Blob([await readFile("statement.pdf")], { type: "application/pdf" }), "statement.pdf");
fd.append("use_ocr", "true");
fd.append("dpi", "300");
const up = await fetch(\`\${BASE}/api/v1/jobs\`, { method: "POST", headers: H, body: fd });
if (!up.ok) throw new Error(\`Upload failed: \${up.status}\`);
const { job_id } = await up.json();

// 2. Poll with backoff
let delay = 2000, job;
for (;;) {
  const r = await fetch(\`\${BASE}/api/v1/jobs/\${job_id}\`, { headers: H });
  if (r.status === 429) { await sleep(Number(r.headers.get("Retry-After") ?? 10) * 1000); continue; }
  job = await r.json();
  if (job.status === "done" || job.status === "error") break;
  await sleep(delay);
  delay = Math.min(delay * 1.5, 10000);
}

// 3. Result
const cam = await (await fetch(\`\${BASE}/api/v1/jobs/\${job_id}/files/0/result\`, { headers: H })).json();
console.log(cam.score.credit_score_index, cam.score.risk_rating);

// 4. Excel
const x = await fetch(\`\${BASE}/api/v1/jobs/\${job_id}/files/0/download\`, { headers: H });
await writeFile("cam.xlsx", Buffer.from(await x.arrayBuffer()));`,

  java: `import java.net.URI;
import java.net.http.*;
import java.nio.file.*;
import java.util.UUID;

public class ImperaCam {
  static final String BASE = "${B}";
  static final String KEY = System.getenv("IMPERA_API_KEY");
  static final HttpClient http = HttpClient.newHttpClient();

  public static void main(String[] a) throws Exception {
    // 1. Upload (multipart)
    String boundary = UUID.randomUUID().toString();
    byte[] pdf = Files.readAllBytes(Path.of("statement.pdf"));
    var body = new java.io.ByteArrayOutputStream();
    body.write(("--" + boundary + "\\r\\nContent-Disposition: form-data; name=\\"files[]\\"; filename=\\"statement.pdf\\"\\r\\n"
        + "Content-Type: application/pdf\\r\\n\\r\\n").getBytes());
    body.write(pdf);
    body.write(("\\r\\n--" + boundary + "--\\r\\n").getBytes());
    var up = http.send(HttpRequest.newBuilder(URI.create(BASE + "/api/v1/jobs"))
        .header("X-API-Key", KEY).header("Content-Type", "multipart/form-data; boundary=" + boundary)
        .POST(HttpRequest.BodyPublishers.ofByteArray(body.toByteArray())).build(),
        HttpResponse.BodyHandlers.ofString());
    String jobId = up.body().replaceAll(".*\\"job_id\\"\\\\s*:\\\\s*\\"([^\\"]+)\\".*", "$1"); // use a JSON library in production

    // 2. Poll with backoff
    long delay = 2000;
    while (true) {
      var r = http.send(get("/api/v1/jobs/" + jobId), HttpResponse.BodyHandlers.ofString());
      if (r.statusCode() == 429) { Thread.sleep(1000L * Long.parseLong(r.headers().firstValue("Retry-After").orElse("10"))); continue; }
      if (r.body().contains("\\"status\\":\\"done\\"") || r.body().contains("\\"status\\":\\"error\\"")) break;
      Thread.sleep(delay); delay = Math.min((long) (delay * 1.5), 10000);
    }

    // 3. Result
    var cam = http.send(get("/api/v1/jobs/" + jobId + "/files/0/result"), HttpResponse.BodyHandlers.ofString());
    System.out.println(cam.body());

    // 4. Excel
    http.send(get("/api/v1/jobs/" + jobId + "/files/0/download"), HttpResponse.BodyHandlers.ofFile(Path.of("cam.xlsx")));
  }

  static HttpRequest get(String path) {
    return HttpRequest.newBuilder(URI.create(BASE + path)).header("X-API-Key", KEY).GET().build();
  }
}`,
};

export interface EndpointDoc {
  method: "GET" | "POST"; path: string; summary: string; scope: "jobs:read" | "jobs:write";
  params?: { name: string; where: "path" | "query" | "form"; desc: string }[];
  request: string; response: string; errors: number[];
}

export const ENDPOINTS: EndpointDoc[] = [
  {
    method: "POST", path: "/api/v1/jobs", summary: "Upload one or more statement PDFs.", scope: "jobs:write",
    params: [
      { name: "files[]", where: "form", desc: "PDF files. Up to your plan's files-per-job and size limits." },
      { name: "password", where: "form", desc: "Optional PDF password. Used once, never stored." },
      { name: "use_ocr", where: "form", desc: "true | false, default true." },
      { name: "dpi", where: "form", desc: "200 | 300 | 400, default 300." },
      { name: "bank", where: "form", desc: "Optional. Only when the PDF shows the bank as a logo." },
    ],
    request: `curl -X POST "${B}/api/v1/jobs" -H "X-API-Key: $KEY" -F "files[]=@statement.pdf"`,
    response: `201 Created
{
  "job_id": "job_7Hq2",
  "files": [{ "id": "f_1", "name": "statement.pdf", "status": "queued", "progress": 0,
              "message": "queued", "error": null, "result": null }]
}`,
    errors: [400, 401, 403, 429, 503],
  },
  {
    method: "GET", path: "/api/v1/jobs", summary: "List jobs, newest first.", scope: "jobs:read",
    params: [{ name: "limit", where: "query", desc: "Default 20." }, { name: "offset", where: "query", desc: "Default 0." }],
    request: `curl "${B}/api/v1/jobs?limit=20&offset=0" -H "X-API-Key: $KEY"`,
    response: `{ "items": [ { "id": "job_7Hq2", "status": "done", "created": "2026-10-14T09:12:00Z", "progress": 100, "files": [ … ] } ], "total": 42 }`,
    errors: [401, 403, 429],
  },
  {
    method: "GET", path: "/api/v1/jobs/{job_id}", summary: "Job status with per-file progress. Poll this.", scope: "jobs:read",
    params: [{ name: "job_id", where: "path", desc: "From the upload response." }],
    request: `curl "${B}/api/v1/jobs/job_7Hq2" -H "X-API-Key: $KEY"`,
    response: `{
  "id": "job_7Hq2", "status": "running", "created": "2026-10-14T09:12:00Z",
  "use_ocr": true, "dpi": 300, "bank": null, "progress": 64,
  "files": [{ "id": "f_1", "name": "statement.pdf", "status": "running", "progress": 64,
              "message": "reading pages", "error": null, "result": null }]
}`,
    errors: [401, 403, 404, 429],
  },
  {
    method: "GET", path: "/api/v1/jobs/{job_id}/files/{index}/result", summary: "The full CamResult for one file.", scope: "jobs:read",
    params: [{ name: "job_id", where: "path", desc: "Job ID." }, { name: "index", where: "path", desc: "0-based file position in the job." }],
    request: `curl "${B}/api/v1/jobs/job_7Hq2/files/0/result" -H "X-API-Key: $KEY"`,
    response: `{
  "file": { "rows": 412, "chain": 1, "flagged": 0, "is_partial": false, … },
  "account": { "account_holder": "…", "bank_name": "…", "account_number_masked": "••••1234", … },
  "score": { "credit_score_index": 82, "risk_rating": "PRIME", "score_before_caps": 82, … },
  "metrics": { "abb": 412500, "dscr": 2.1, … },
  "monthly": [ … ], "income": { … }, "debt": { … }, "counterparties": { … },
  "risk": { … }, "validation": { "pass_rate": 1, "flagged_rows": [] }
}`,
    errors: [401, 403, 404, 409, 410, 429],
  },
  {
    method: "GET", path: "/api/v1/jobs/{job_id}/files/{index}/transactions", summary: "Parsed transactions, paged.", scope: "jobs:read",
    params: [{ name: "offset", where: "query", desc: "Default 0." }, { name: "limit", where: "query", desc: "Default 100." }],
    request: `curl "${B}/api/v1/jobs/job_7Hq2/files/0/transactions?offset=0&limit=100" -H "X-API-Key: $KEY"`,
    response: `{ "items": [ { "sno": 1, "date": "2024-04-01", "narration": "…", "debit": null, "credit": 25000,
              "balance": 182000, "category": "…", "status": "OK", "page": 1 } ], "total": 412 }`,
    errors: [401, 403, 404, 409, 410, 429],
  },
  {
    method: "GET", path: "/api/v1/jobs/{job_id}/files/{index}/download", summary: "Excel workbook (.xlsx, binary).", scope: "jobs:read",
    request: `curl -o cam.xlsx "${B}/api/v1/jobs/job_7Hq2/files/0/download" -H "X-API-Key: $KEY"`,
    response: `200 OK  Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`,
    errors: [401, 403, 404, 409, 410, 429],
  },
];

export const ERROR_CODES: Record<number, string> = {
  400: "Bad request — not a PDF, wrong PDF password, or file too big.",
  401: "Missing or invalid API key.",
  403: "Key lacks the needed scope, or the organisation is suspended.",
  404: "Job or file not found in your organisation.",
  409: "Result not ready yet — keep polling the job.",
  410: "Result expired under the retention policy — upload again.",
  429: "Too many requests or too many files still processing. Wait for the Retry-After header (seconds).",
  503: "Processing queue temporarily unavailable. Retry with backoff.",
};
