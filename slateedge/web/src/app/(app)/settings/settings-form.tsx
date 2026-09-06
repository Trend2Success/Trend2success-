'use client';

import { useFormState, useFormStatus } from 'react-dom';
import { Button } from '@/components/ui/button';
import { Input, Label } from '@/components/ui/input';
import { Callout } from '@/components/ui/callout';
import { updateSettingsAction, SettingsFormState } from '@/server/actions/settings';

function SubmitButton() {
  const { pending } = useFormStatus();
  return (
    <Button type="submit" disabled={pending}>
      {pending ? 'Saving…' : 'Save settings'}
    </Button>
  );
}

export function SettingsForm({
  defaults,
}: {
  defaults: {
    sessionBudget: number;
    stopLoss: number;
    chalkThresholdPct: number;
    contrarianOwnershipPct: number;
    contrarianCeilingPctile: number;
    defaultSalaryCap: number;
  };
}) {
  const [state, formAction] = useFormState(updateSettingsAction, {} as SettingsFormState);

  return (
    <form action={formAction} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <div className="flex flex-col gap-1">
        <Label htmlFor="sessionBudget">Session / entertainment budget ($)</Label>
        <Input id="sessionBudget" name="sessionBudget" type="number" step="0.01" min="0" defaultValue={defaults.sessionBudget.toFixed(2)} />
      </div>
      <div className="flex flex-col gap-1">
        <Label htmlFor="stopLoss">Stop-loss reminder ($)</Label>
        <Input id="stopLoss" name="stopLoss" type="number" step="0.01" min="0" defaultValue={defaults.stopLoss.toFixed(2)} />
      </div>
      <div className="flex flex-col gap-1">
        <Label htmlFor="chalkThresholdPct">Chalk threshold (ownership %)</Label>
        <Input id="chalkThresholdPct" name="chalkThresholdPct" type="number" min="0" max="100" defaultValue={defaults.chalkThresholdPct} />
      </div>
      <div className="flex flex-col gap-1">
        <Label htmlFor="contrarianOwnershipPct">Contrarian threshold (ownership % below)</Label>
        <Input id="contrarianOwnershipPct" name="contrarianOwnershipPct" type="number" min="0" max="100" defaultValue={defaults.contrarianOwnershipPct} />
      </div>
      <div className="flex flex-col gap-1">
        <Label htmlFor="contrarianCeilingPctile">Contrarian threshold (ceiling percentile above)</Label>
        <Input id="contrarianCeilingPctile" name="contrarianCeilingPctile" type="number" min="0" max="100" defaultValue={defaults.contrarianCeilingPctile} />
      </div>
      <div className="flex flex-col gap-1">
        <Label htmlFor="defaultSalaryCap">Default salary cap</Label>
        <Input id="defaultSalaryCap" name="defaultSalaryCap" type="number" min="1000" defaultValue={defaults.defaultSalaryCap} />
      </div>

      {state?.error ? <Callout variant="danger" className="sm:col-span-2">{state.error}</Callout> : null}
      {state?.success ? <Callout variant="info" className="sm:col-span-2">{state.success}</Callout> : null}

      <div className="sm:col-span-2">
        <SubmitButton />
      </div>
    </form>
  );
}
