'use client';

import { useFormState, useFormStatus } from 'react-dom';
import { Button } from '@/components/ui/button';
import { Input, Label } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Callout } from '@/components/ui/callout';
import { runSimulationAction, SimulationFormState } from '@/server/actions/simulations';
import { useState } from 'react';

function SubmitButton() {
  const { pending } = useFormStatus();
  return (
    <Button type="submit" disabled={pending}>
      {pending ? 'Simulating…' : 'Run simulation'}
    </Button>
  );
}

export function RunSimulationForm({ slateId, runs }: { slateId: string; runs: { id: string; label: string }[] }) {
  const [state, formAction] = useFormState(runSimulationAction, {} as SimulationFormState);
  const [reproducible, setReproducible] = useState(false);

  return (
    <form action={formAction} className="flex flex-col gap-4">
      <input type="hidden" name="slateId" value={slateId} />
      <input type="hidden" name="reproducible" value={String(reproducible)} />

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="flex flex-col gap-1">
          <Label>Distribution</Label>
          <Select name="distribution" defaultValue="truncated_normal">
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="truncated_normal">Truncated normal</SelectItem>
              <SelectItem value="lognormal">Log-normal</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-1">
          <Label>Simulations (1,000–20,000)</Label>
          <Input name="numSimulations" type="number" min="1000" max="20000" defaultValue="10000" />
        </div>
        <div className="flex flex-col gap-1">
          <Label>Score threshold (optional)</Label>
          <Input name="threshold" type="number" placeholder="e.g. 150" />
        </div>
        <div className="flex flex-col gap-1">
          <Label>Compare a lineup run (optional)</Label>
          <select name="lineupRunId" className="se-focus-ring h-9 rounded-md border border-graphite-600 bg-graphite-900 px-2 text-sm">
            <option value="">None</option>
            {runs.map((r) => (
              <option key={r.id} value={r.id}>
                {r.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div className="flex flex-col gap-1">
          <Label>QB ↔ own pass-catcher correlation</Label>
          <Input name="corrQbPassCatcher" type="number" step="0.05" min="-1" max="1" defaultValue="0.6" />
        </div>
        <div className="flex flex-col gap-1">
          <Label>Same-game offense correlation</Label>
          <Input name="corrSameGame" type="number" step="0.05" min="-1" max="1" defaultValue="0.15" />
        </div>
        <div className="flex flex-col gap-1">
          <Label>DST vs opposing offense correlation</Label>
          <Input name="corrDstOpp" type="number" step="0.05" min="-1" max="1" defaultValue="-0.2" />
        </div>
      </div>

      <div className="flex items-center gap-3">
        <label className="flex items-center gap-2 text-xs text-ink-200">
          <Checkbox checked={reproducible} onCheckedChange={(v) => setReproducible(v === true)} />
          Reproducible run (fixed seed)
        </label>
        {reproducible ? <Input name="randomSeed" type="number" defaultValue="42" className="w-28" /> : null}
      </div>

      {state?.error ? <Callout variant="danger">{state.error}</Callout> : null}
      {state?.success ? <Callout variant="info">{state.success}</Callout> : null}

      <div>
        <SubmitButton />
      </div>
    </form>
  );
}
