import Link from 'next/link';
import { requireUser } from '@/lib/auth';
import { prisma } from '@/lib/db';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input, Label } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { EmptyState } from '@/components/ui/callout';
import { createSlateAction, deleteSlateAction } from '@/server/actions/slates';
import { CreateSlateForm } from './create-slate-form';
import { DeleteSlateButton } from './delete-slate-button';

export default async function SlatesPage() {
  const user = await requireUser();
  const slates = await prisma.slate.findMany({
    where: { userId: user.id },
    orderBy: { createdAt: 'desc' },
    include: { _count: { select: { players: true } } },
  });

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold">Slate Data Import</h1>
        <p className="text-sm text-ink-400">
          Upload salary, projection, and results CSVs. Nothing is ever fetched or scraped from DraftKings or any other
          site — only files you upload here.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Create a slate manually</CardTitle>
          <CardDescription>
            Optional — importing a salary CSV will also create (or update) a slate automatically from its slate_id.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <CreateSlateForm action={createSlateAction} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Your slates</CardTitle>
        </CardHeader>
        <CardContent>
          {slates.length === 0 ? (
            <EmptyState title="No slates yet" description="Create one above or upload a salary CSV to get started." />
          ) : (
            <ul className="flex flex-col divide-y divide-graphite-700">
              {slates.map((s) => (
                <li key={s.id} className="flex items-center justify-between gap-3 py-3">
                  <div>
                    <p className="text-sm font-medium">
                      {s.slateName} {s.isDemo ? <Badge variant="amber" className="ml-1">Demo</Badge> : null}
                    </p>
                    <p className="text-xs text-ink-400">
                      {s.sport} · {new Date(s.contestDate).toLocaleString()} · {s._count.players} players
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button asChild size="sm" variant="secondary">
                      <Link href={`/slates/${s.id}`}>Manage data</Link>
                    </Button>
                    <DeleteSlateButton slateId={s.id} slateName={s.slateName} action={deleteSlateAction} />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
