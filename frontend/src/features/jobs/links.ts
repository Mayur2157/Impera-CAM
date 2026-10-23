import type { FileTask, Job } from "@/api/types";

/** Where a statement row leads: its analysis once done, otherwise its upload's progress. */
export function fileHref(job: Job, index: number, file: FileTask): string {
  return file.status === "done" ? `/app/statements/${job.id}/files/${index}` : `/app/statements/${job.id}`;
}
