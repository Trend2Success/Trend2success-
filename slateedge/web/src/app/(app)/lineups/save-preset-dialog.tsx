'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useFormState, useFormStatus } from 'react-dom';
import { Button } from '@/components/ui/button';
import { Input, Label } from '@/components/ui/input';
import { Callout } from '@/components/ui/callout';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogTrigger } from '@/components/ui/dialog';
import { saveLineupPresetAction, PresetFormState } from '@/server/actions/presets';

function SubmitButton() {
  const { pending } = useFormStatus();
  return (
    <Button type="submit" disabled={pending}>
      {pending ? 'Saving…' : 'Save preset'}
    </Button>
  );
}

export function SavePresetDialog({ getSnapshotJson }: { getSnapshotJson: () => string }) {
  const [open, setOpen] = useState(false);
  const [state, formAction] = useFormState(saveLineupPresetAction, {} as PresetFormState);
  const router = useRouter();

  useEffect(() => {
    if (state?.success) router.refresh();
  }, [state?.success, router]);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button type="button" variant="outline" size="sm">
          Save current settings as preset
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Save preset</DialogTitle>
          <DialogDescription>
            Saves every Lineup Builder setting on this page (roster, exposure, stacking, groups, weights) under a
            name you choose. A starting point you can keep editing — not a proven strategy.
          </DialogDescription>
        </DialogHeader>
        <form action={formAction} className="flex flex-col gap-3">
          <input type="hidden" name="settingsJson" value={getSnapshotJson()} />
          <div className="flex flex-col gap-1">
            <Label htmlFor="preset-name">Preset name</Label>
            <Input id="preset-name" name="name" placeholder="e.g. My Sunday GPP setup" required />
          </div>
          {state?.error ? <Callout variant="danger">{state.error}</Callout> : null}
          {state?.success ? <Callout variant="info">{state.success}</Callout> : null}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              Close
            </Button>
            <SubmitButton />
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
