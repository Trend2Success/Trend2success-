'use client';

import { useFormState, useFormStatus } from 'react-dom';
import { Button } from '@/components/ui/button';
import { Input, Label } from '@/components/ui/input';
import type { SlateFormState } from '@/server/actions/slates';

function SubmitButton() {
  const { pending } = useFormStatus();
  return (
    <Button type="submit" disabled={pending}>
      {pending ? 'Creating…' : 'Create slate'}
    </Button>
  );
}

export function CreateSlateForm({
  action,
}: {
  action: (prev: SlateFormState, formData: FormData) => Promise<SlateFormState>;
}) {
  const [state, formAction] = useFormState(action, {} as SlateFormState);

  return (
    <form action={formAction} className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      <div className="flex flex-col gap-1">
        <Label htmlFor="slateName">Slate name</Label>
        <Input id="slateName" name="slateName" placeholder="Sunday Main Slate" required />
      </div>
      <div className="flex flex-col gap-1">
        <Label htmlFor="sport">Sport</Label>
        <Input id="sport" name="sport" defaultValue="NFL" />
      </div>
      <div className="flex flex-col gap-1">
        <Label htmlFor="contestDate">Contest date</Label>
        <Input id="contestDate" name="contestDate" type="datetime-local" required />
      </div>
      <div className="sm:col-span-3">
        {state?.error ? <p className="mb-2 text-xs text-rose-400">{state.error}</p> : null}
        <SubmitButton />
      </div>
    </form>
  );
}
