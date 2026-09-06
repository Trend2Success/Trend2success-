// Fuzzy header matching: lets users upload CSVs with slightly different column
// names (e.g. "Player" instead of "player_name") and still map cleanly onto
// SlateEdge's expected schema. Matching is local, deterministic string
// comparison only — no network calls.

export interface ColumnSpec {
  key: string;
  required: boolean;
  aliases: string[];
}

function normalize(header: string): string {
  return header.trim().toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
}

export interface ColumnMappingResult {
  mapping: Record<string, string | null>; // expected key -> actual header found (or null)
  unmatchedRequired: string[];
  unrecognizedHeaders: string[];
}

export function mapHeaders(headers: string[], specs: ColumnSpec[]): ColumnMappingResult {
  const normalizedHeaders = headers.map((h) => ({ raw: h, norm: normalize(h) }));
  const mapping: Record<string, string | null> = {};
  const usedHeaders = new Set<string>();

  for (const spec of specs) {
    const candidateNorms = [spec.key, ...spec.aliases].map(normalize);
    const match = normalizedHeaders.find(
      (h) => !usedHeaders.has(h.raw) && candidateNorms.includes(h.norm)
    );
    if (match) {
      mapping[spec.key] = match.raw;
      usedHeaders.add(match.raw);
    } else {
      mapping[spec.key] = null;
    }
  }

  const unmatchedRequired = specs.filter((s) => s.required && !mapping[s.key]).map((s) => s.key);
  const unrecognizedHeaders = headers.filter((h) => !usedHeaders.has(h));

  return { mapping, unmatchedRequired, unrecognizedHeaders };
}
