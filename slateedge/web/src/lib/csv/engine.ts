import Papa from 'papaparse';
import { z } from 'zod';
import { ColumnSpec, mapHeaders } from './columnMap';

export interface RowError {
  rowNumber: number; // 1-based, aligned to spreadsheet row (header = row 1)
  messages: string[];
  raw: Record<string, string>;
}

export interface ParseResult<T> {
  validRows: T[];
  errors: RowError[];
  duplicatesRemoved: number;
  mapping: Record<string, string | null>;
  unmatchedRequired: string[];
  unrecognizedHeaders: string[];
  totalRows: number;
}

export function parseAndValidate<T>(
  csvText: string,
  specs: ColumnSpec[],
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  rowSchema: z.ZodType<T, z.ZodTypeDef, any>,
  opts: { dedupeKey?: (row: T) => string } = {}
): ParseResult<T> {
  const parsed = Papa.parse<Record<string, string>>(csvText, {
    header: true,
    skipEmptyLines: true,
  });

  const headers = parsed.meta.fields ?? [];
  const { mapping, unmatchedRequired, unrecognizedHeaders } = mapHeaders(headers, specs);

  if (unmatchedRequired.length > 0) {
    return {
      validRows: [],
      errors: [],
      duplicatesRemoved: 0,
      mapping,
      unmatchedRequired,
      unrecognizedHeaders,
      totalRows: parsed.data.length,
    };
  }

  const errors: RowError[] = [];
  const validRows: T[] = [];
  const seen = new Set<string>();
  let duplicatesRemoved = 0;

  parsed.data.forEach((rawRow, idx) => {
    const remapped: Record<string, string> = {};
    for (const spec of specs) {
      const actualHeader = mapping[spec.key];
      remapped[spec.key] = actualHeader ? (rawRow[actualHeader] ?? '').toString().trim() : '';
    }
    const result = rowSchema.safeParse(remapped);
    if (!result.success) {
      errors.push({
        rowNumber: idx + 2,
        messages: result.error.issues.map((i) => `${i.path.join('.')}: ${i.message}`),
        raw: rawRow,
      });
      return;
    }
    if (opts.dedupeKey) {
      const key = opts.dedupeKey(result.data);
      if (seen.has(key)) {
        duplicatesRemoved += 1;
        return;
      }
      seen.add(key);
    }
    validRows.push(result.data);
  });

  return {
    validRows,
    errors,
    duplicatesRemoved,
    mapping,
    unmatchedRequired,
    unrecognizedHeaders,
    totalRows: parsed.data.length,
  };
}

export function toCsv(headers: string[], rows: (string | number)[][]): string {
  return Papa.unparse({ fields: headers, data: rows });
}
