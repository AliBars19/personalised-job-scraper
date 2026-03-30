/**
 * Validate that a URL has a safe scheme (http/https only).
 * Prevents javascript: and data: URI injection in href attributes.
 */
export function safeUrl(url: string | null | undefined): string {
  if (!url) return "#";
  try {
    const parsed = new URL(url);
    if (parsed.protocol === "https:" || parsed.protocol === "http:") {
      return url;
    }
  } catch {
    // Invalid URL
  }
  return "#";
}
