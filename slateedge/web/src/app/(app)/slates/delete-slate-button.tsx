'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogTrigger } from '@/components/ui/dialog';

export function DeleteSlateButton({
  slateId,
  slateName,
  action,
}: {
  slateId: string;
  slateName: string;
  action: (formData: FormData) => void;
}) {
  const [open, setOpen] = useState(false);
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
            This permanently removes the slate, its player pool, projections, lineups, and simulation runs. This
            cannot be undone.
          </DialogDescription>
        </DialogHeader>
        <form action={action}>
          <input type="hidden" name="slateId" value={slateId} />
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="destructive">
              Delete slate
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
