import { notFound } from 'next/navigation';
import { requireUser } from '@/lib/auth';
import { prisma } from '@/lib/db';
import { CsvUploadCard } from '@/components/csv-upload-card';
import {
  previewSalaryCsvAction,
  commitSalaryCsvAction,
  previewProjectionCsvAction,
  commitProjectionCsvAction,
  previewResultsCsvAction,
  commitResultsCsvAction,
} from '@/server/actions/imports';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Label, Input } from '@/components/ui/input';

export default async function SlateDetailPage({ params }: { params: { id: string } }) {
  const user = await requireUser();
  const slate = await prisma.slate.findFirst({ where: { id: params.id, userId: user.id } });
  if (!slate) notFound();

  const [batches, sources] = await Promise.all([
    prisma.importBatch.findMany({ where: { slateId: slate.id }, orderBy: { createdAt: 'desc' } }),
    prisma.projectionSource.findMany({ where: { slateId: slate.id } }),
  ]);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold">{slate.slateName}</h1>
        <p className="text-sm text-ink-400">
          {slate.sport} · {new Date(slate.contestDate).toLocaleString()} · slate_id: {slate.slateId}
        </p>
      </div>

      <CsvUploadCard
        title="Salary CSV"
        description="Creates/updates this slate and the player roster. One slate per file."
        templateHref="/api/templates/salary"
        previewAction={previewSalaryCsvAction}
        commitAction={commitSalaryCsvAction}
      />

      <CsvUploadCard
        title="Projection CSV"
        description="Attaches projections to the currently selected slate. Import multiple sources and blend them in the Projection Lab."
        templateHref="/api/templates/projection"
        previewAction={previewProjectionCsvAction}
        commitAction={commitProjectionCsvAction}
        hiddenFields={{ slateId: slate.id }}
        extraFields={
          <div className="flex flex-col gap-1">
            <Label htmlFor="sourceLabel">Source label</Label>
            <Input id="sourceLabel" name="sourceLabel" defaultValue="User Upload" placeholder="e.g. My Model v2" />
          </div>
        }
      />

      <CsvUploadCard
        title="Results CSV"
        description="Contest results reference slates by slate_id — import each slate's salary CSV first."
        templateHref="/api/templates/results"
        previewAction={previewResultsCsvAction}
        commitAction={commitResultsCsvAction}
      />

      <Card>
        <CardHeader>
          <CardTitle>Data provenance</CardTitle>
          <CardDescription>Every import is logged with its source and row counts.</CardDescription>
        </CardHeader>
        <CardContent>
          {batches.length === 0 ? (
            <p className="text-xs text-ink-400">No imports yet.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>When</TableHead>
                  <TableHead>Kind</TableHead>
                  <TableHead>Source</TableHead>
                  <TableHead>File</TableHead>
                  <TableHead>Rows</TableHead>
                  <TableHead>Errors</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {batches.map((b) => (
                  <TableRow key={b.id}>
                    <TableCell>{new Date(b.createdAt).toLocaleString()}</TableCell>
                    <TableCell><Badge variant="teal">{b.kind}</Badge></TableCell>
                    <TableCell>{b.sourceLabel}</TableCell>
                    <TableCell>{b.fileName ?? '—'}</TableCell>
                    <TableCell>{b.rowCount}</TableCell>
                    <TableCell>{b.errorCount}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {sources.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>Projection sources on this slate</CardTitle>
            <CardDescription>Blend and weight these in the Projection Lab.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {sources.map((s) => (
              <Badge key={s.id} variant="outline">
                {s.sourceLabel}
              </Badge>
            ))}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
