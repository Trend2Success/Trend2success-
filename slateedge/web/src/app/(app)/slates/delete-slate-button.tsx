'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogTrigger } from '@/components/ui/dialog';
import { useUndoable } from '@/components/undo-provider';

export function DeleteSlateButton({
  slateId,
  slateName,
  action,
}: {
  slateId: string;
  slateName: string;
  action: (formData: FormData) => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const { scheduleUndoable } = useUndoable();

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" variant="destructive">
          Delete
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete "{slateName}"?</DialogTitle>
          <DialogDescription>
            This removes the slate, its player pool, projections, lineups, and simulation runs. You'll have a few
            seconds to undo after confirming.
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
              scheduleUndoable(`"${slateName}" will be deleted.`, async () => {
                const fd = new FormData();
                fd.set('slateId', slateId);
                await action(fd);
                router.refresh();
              });
            }}
          >
            Delete slate
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
