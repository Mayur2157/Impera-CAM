import { requestBlob } from "@/api/client";

/** Fetch a file with the session's token and hand it to the browser to save. */
export async function downloadFile(path: string, fallbackName: string): Promise<void> {
  const { blob, filename } = await requestBlob(path);
  const href = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = href;
  a.download = filename || fallbackName;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(href), 1_000);
}
