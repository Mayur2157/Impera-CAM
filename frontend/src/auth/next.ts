/** Only relative paths inside the app, so ?next= can't send users to another site. */
export function safeNext(next: string | null): string {
  return next && next.startsWith("/") && !next.startsWith("//") ? next : "/app";
}
