'use client';

import { useTransition } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { deleteLineupAction, deleteLineupRunAction } from '@/server/actions/lineups';

export function DeleteLineupButton({ lineupId }: { lineupId: string }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  return (
    <Button
      size="sm"
      variant="ghost"
      disabled={pending}
      onClick={() => {
        const fd = new FormData();
        fd.set('lineupId', lineupId);
        startTransition(async () => {
          await deleteLineupAction(fd);
          router.refresh();
        });
      }}
    >
      Delete
    </Button>
  );
}

export function DeleteRunButton({ runId }: { runId: string }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  return (
    <Button
      size="sm"
      variant="destructive"
      disabled={pending}
      onClick={() => {
        if (!confirm('Delete this entire run and all its lineups?')) return;
        const fd = new FormData();
        fd.set('runId', runId);
        startTransition(async () => {
          await deleteLineupRunAction(fd);
          router.refresh();
        });
      }}
    >
      Delete run
    </Button>
  );
}
