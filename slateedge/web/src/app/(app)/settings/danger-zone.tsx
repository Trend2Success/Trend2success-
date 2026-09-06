'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogTrigger } from '@/components/ui/dialog';
import { deleteAllDataAction } from '@/server/actions/settings';

export function DeleteAllDataButton() {
  const [open, setOpen] = useState(false);
  const [confirmation, setConfirmation] = useState('');

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="destructive">Delete all local data</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete all local data</DialogTitle>
          <DialogDescription>
            This permanently deletes every slate, player, projection, lineup, and simulation run for your account.
            Your account and settings are kept. This cannot be undone. Type DELETE to confirm.
          </DialogDescription>
        </DialogHeader>
        <Input value={confirmation} onChange={(e) => setConfirmation(e.target.value)} placeholder="DELETE" />
        <form action={deleteAllDataAction}>
          <input type="hidden" name="confirmation" value={confirmation} />
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="destructive" disabled={confirmation !== 'DELETE'}>
              Permanently delete everything
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
