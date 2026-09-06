'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogTrigger } from '@/components/ui/dialog';
import { useUndoable } from '@/components/undo-provider';
import { deleteContestResultAction } from '@/server/actions/results';

export function DeleteResultButton({ resultId, contestName }: { resultId: string; contestName: string }) {
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const { scheduleUndoable } = useUndoable();

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" variant="ghost">
          Delete
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete this result?</DialogTitle>
          <DialogDescription>
            Removes "{contestName}" from your tracked results. You'll have a few seconds to undo after confirming.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button
            type="button"
            variant="destructive"
            onClick={() => {
              setOpen(false);
              scheduleUndoable(`"${contestName}" will be deleted.`, async () => {
                const fd = new FormData();
                fd.set('resultId', resultId);
                await deleteContestResultAction(fd);
                router.refresh();
              });
            }}
          >
            Delete result
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
