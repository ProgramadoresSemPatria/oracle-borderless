import type { KnowledgeDoc } from "../lib/demo/demoData";
import { DEMO_DOCUMENTS } from "../lib/demo/demoData";

const DEMO = import.meta.env.VITE_DEMO_MODE === "true";

/**
 * There is no backend documents endpoint yet. In demo mode we return the seeded
 * list; when a real `/documents` endpoint exists, branch on !DEMO here.
 */
export function listDocuments(): Promise<KnowledgeDoc[]> {
  if (DEMO) return Promise.resolve(DEMO_DOCUMENTS);
  return Promise.resolve(DEMO_DOCUMENTS);
}
