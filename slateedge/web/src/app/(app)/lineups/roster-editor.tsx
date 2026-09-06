'use client';

import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/input';
import { X } from 'lucide-react';

const ALL_POSITIONS = ['QB', 'RB', 'WR', 'TE', 'DST', 'FLEX'] as const;
const FLEX_ELIGIBLE = ['RB', 'WR', 'TE'] as const;

export function RosterEditor({
  rosterSlots,
  setRosterSlots,
  flexPositions,
  setFlexPositions,
}: {
  rosterSlots: string[];
  setRosterSlots: (slots: string[]) => void;
  flexPositions: string[];
  setFlexPositions: (positions: string[]) => void;
}) {
  const hasFlex = rosterSlots.includes('FLEX');

  function updateSlot(index: number, value: string) {
    const next = [...rosterSlots];
    next[index] = value;
    setRosterSlots(next);
  }

  function removeSlot(index: number) {
    setRosterSlots(rosterSlots.filter((_, i) => i !== index));
  }

  function addSlot() {
    setRosterSlots([...rosterSlots, 'RB']);
  }

  function toggleFlexEligible(position: string) {
    setFlexPositions(
      flexPositions.includes(position) ? flexPositions.filter((p) => p !== position) : [...flexPositions, position]
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap gap-2">
        {rosterSlots.map((slot, i) => (
          <div key={i} className="flex items-center gap-1 rounded-md border border-graphite-600 bg-graphite-900 p-1">
            <Select value={slot} onValueChange={(v) => updateSlot(i, v)}>
              <SelectTrigger className="h-8 w-24 border-0 bg-transparent">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ALL_POSITIONS.map((p) => (
                  <SelectItem key={p} value={p}>
                    {p}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <button
              type="button"
              onClick={() => removeSlot(i)}
              className="se-focus-ring rounded p-1 text-ink-600 hover:text-rose-400"
              aria-label={`Remove slot ${i + 1}`}
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
        <Button type="button" size="sm" variant="outline" onClick={addSlot}>
          + Add slot
        </Button>
      </div>
      <p className="text-xs text-ink-400">{rosterSlots.length} roster spots total.</p>

      {hasFlex ? (
        <div>
          <Label className="mb-1 block">FLEX eligibility</Label>
          <div className="flex gap-4">
            {FLEX_ELIGIBLE.map((p) => (
              <label key={p} className="flex items-center gap-2 text-xs text-ink-200">
                <Checkbox checked={flexPositions.includes(p)} onCheckedChange={() => toggleFlexEligible(p)} />
                {p}
              </label>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
