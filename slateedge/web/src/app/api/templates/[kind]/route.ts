import { NextRequest, NextResponse } from 'next/server';
import { toCsv } from '@/lib/csv/engine';
import { SALARY_TEMPLATE_HEADERS, SALARY_TEMPLATE_SAMPLE_ROW } from '@/lib/csv/salary';
import { PROJECTION_TEMPLATE_HEADERS, PROJECTION_TEMPLATE_SAMPLE_ROW } from '@/lib/csv/projection';
import { RESULTS_TEMPLATE_HEADERS, RESULTS_TEMPLATE_SAMPLE_ROW } from '@/lib/csv/results';

const TEMPLATES: Record<string, { headers: string[]; sample: (string | number)[] }> = {
  salary: { headers: SALARY_TEMPLATE_HEADERS, sample: SALARY_TEMPLATE_SAMPLE_ROW },
  projection: { headers: PROJECTION_TEMPLATE_HEADERS, sample: PROJECTION_TEMPLATE_SAMPLE_ROW },
  results: { headers: RESULTS_TEMPLATE_HEADERS, sample: RESULTS_TEMPLATE_SAMPLE_ROW },
};

export async function GET(_req: NextRequest, { params }: { params: { kind: string } }) {
  const template = TEMPLATES[params.kind];
  if (!template) return NextResponse.json({ error: 'Unknown template' }, { status: 404 });

  const csv = toCsv(template.headers, [template.sample]);
  return new NextResponse(csv, {
    headers: {
      'Content-Type': 'text/csv; charset=utf-8',
      'Content-Disposition': `attachment; filename="slateedge-${params.kind}-template.csv"`,
    },
  });
}
