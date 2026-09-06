'use client';

import { useTransition } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { useUndoable } from '@/components/undo-provider';
import { deleteLineupAction, deleteLineupRunAction, regenerateLineupAction } from '@/server/actions/lineups';

export function DeleteLineupButton({ lineupId, index }: { lineupId: string; index: number }) {
  const router = useRouter();
  const { scheduleUndoable } = useUndoable();

  return (
    <Button
      size="sm"
      variant="ghost"
      onClick={() => {
        scheduleUndoable(`Lineup #${index + 1} will be deleted.`, async () => {
          const fd = new FormData();
          fd.set('lineupId', lineupId);
          await deleteLineupAction(fd);
          router.refresh();
        });
      }}
    >
      Delete
    </Button>
  );
}

export function RegenerateLineupButton({ lineupId }: { lineupId: string }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  return (
    <Button
      size="sm"
      variant="secondary"
      disabled={pending}
      onClick={() => {
        const fd = new FormData();
        fd.set('lineupId', lineupId);
        startTransition(async () => {
          const result = await regenerateLineupAction(fd);
          if (result.error) {
            alert(result.error);
          }
          router.refresh();
        });
      }}
    >
      {pending ? 'Regenerating…' : 'Regenerate'}
    </Button>
  );
}

export function DeleteRunButton({ runId }: { runId: string }) {
  const router = useRouter();
  const { scheduleUndoable } = useUndoable();

  return (
    <Button
      size="sm"
      variant="destructive"
      onClick={() => {
        scheduleUndoable('This entire run and all its lineups will be deleted.', async () => {
          const fd = new FormData();
          fd.set('runId', runId);
          await deleteLineupRunAction(fd);
          router.refresh();
        });
      }}
    >
      Delete run
    </Button>
  );
}
