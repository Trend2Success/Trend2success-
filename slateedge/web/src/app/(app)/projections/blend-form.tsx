'use client';

import { useFormState, useFormStatus } from 'react-dom';
import { Button } from '@/components/ui/button';
import { Input, Label } from '@/components/ui/input';
import { Callout } from '@/components/ui/callout';
import { applyBlendWeightsAction, ProjectionFormState } from '@/server/actions/projections';

function SubmitButton() {
  const { pending } = useFormStatus();
  return (
    <Button type="submit" disabled={pending}>
      {pending ? 'Recomputing…' : 'Apply blend weights'}
    </Button>
  );
}

export function BlendForm({ slateId, sources }: { slateId: string; sources: { id: string; sourceLabel: string }[] }) {
  const [state, formAction] = useFormState(applyBlendWeightsAction, {} as ProjectionFormState);

  return (
    <form action={formAction} className="flex flex-col gap-3">
      <input type="hidden" name="slateId" value={slateId} />
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {sources.map((s) => (
          <div key={s.id} className="flex flex-col gap-1">
            <Label htmlFor={`weight_${s.id}`}>{s.sourceLabel}</Label>
            <Input id={`weight_${s.id}`} name={`weight_${s.id}`} type="number" step="0.1" min="0" defaultValue="1" />
          </div>
        ))}
      </div>
      {state?.error ? <Callout variant="danger">{state.error}</Callout> : null}
      {state?.success ? <Callout variant="info">{state.success}</Callout> : null}
      <div>
        <SubmitButton />
      </div>
    </form>
  );
}
