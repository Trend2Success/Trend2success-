'use client';

import { useRef } from 'react';
import { useFormState, useFormStatus } from 'react-dom';
import { Button } from '@/components/ui/button';
import { Input, Label } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Callout } from '@/components/ui/callout';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import type { ImportFormState } from '@/server/actions/imports';

const emptyState: ImportFormState = {};

function ActionButton({ label, variant }: { label: string; variant?: 'default' | 'secondary' }) {
  const { pending } = useFormStatus();
  return (
    <Button type="submit" variant={variant} disabled={pending}>
      {pending ? 'Working…' : label}
    </Button>
  );
}

export function CsvUploadCard({
  title,
  description,
  templateHref,
  previewAction,
  commitAction,
  hiddenFields,
  extraFields,
}: {
  title: string;
  description: string;
  templateHref: string;
  previewAction: (prev: ImportFormState, formData: FormData) => Promise<ImportFormState>;
  commitAction: (prev: ImportFormState, formData: FormData) => Promise<ImportFormState>;
  hiddenFields?: Record<string, string>;
  extraFields?: React.ReactNode;
}) {
  const [previewState, previewFormAction] = useFormState(previewAction, emptyState);
  const [commitState, commitFormAction] = useFormState(commitAction, emptyState);
  const formRef = useRef<HTMLFormElement>(null);

  const state = commitState.committed ? commitState : previewState;

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-2">
        <div>
          <CardTitle>{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </div>
        <a href={templateHref} className="text-xs text-teal-400 hover:underline">
          Download template
        </a>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <form ref={formRef} className="flex flex-col gap-3">
          {Object.entries(hiddenFields ?? {}).map(([k, v]) => (
            <input key={k} type="hidden" name={k} value={v} />
          ))}
          {extraFields}
          <div className="flex flex-col gap-1">
            <Label htmlFor={`file-${title}`}>CSV file</Label>
            <Input id={`file-${title}`} name="file" type="file" accept=".csv,text/csv" required />
          </div>
          <div className="flex gap-2">
            <Button type="submit" formAction={previewFormAction} variant="secondary">
              Preview & validate
            </Button>
            <SubmitCommit commitFormAction={commitFormAction} />
          </div>
        </form>

        {state?.error ? <Callout variant="danger">{state.error}</Callout> : null}
        {state?.success ? <Callout variant={commitState.committed ? 'info' : 'warning'}>{state.success}</Callout> : null}

        {state?.unmatchedRequired && state.unmatchedRequired.length > 0 ? (
          <Callout variant="danger" title="Missing required columns">
            {state.unmatchedRequired.join(', ')}
          </Callout>
        ) : null}

        {state?.unrecognizedHeaders && state.unrecognizedHeaders.length > 0 ? (
          <p className="text-xs text-ink-400">Unrecognized columns ignored: {state.unrecognizedHeaders.join(', ')}</p>
        ) : null}

        {state?.errors && state.errors.length > 0 ? (
          <div>
            <p className="mb-1 text-xs font-medium text-amber-300">Row-level errors ({state.errors.length}):</p>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Row</TableHead>
                  <TableHead>Issues</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {state.errors.slice(0, 50).map((e, i) => (
                  <TableRow key={i}>
                    <TableCell>{e.rowNumber || '—'}</TableCell>
                    <TableCell className="whitespace-normal text-xs text-ink-200">{e.messages.join('; ')}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

function SubmitCommit({ commitFormAction }: { commitFormAction: (formData: FormData) => void }) {
  return (
    <Button type="submit" formAction={commitFormAction}>
      <CommitLabel />
    </Button>
  );
}

function CommitLabel() {
  const { pending } = useFormStatus();
  return <>{pending ? 'Importing…' : 'Import valid rows'}</>;
}
