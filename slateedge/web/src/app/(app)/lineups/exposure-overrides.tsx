'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input, Label } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import type { PlayerExposureOverride } from '@/lib/optimizer/types';

export function ExposureOverrides({
  playerOptions,
  overrides,
  setOverrides,
}: {
  playerOptions: { id: string; label: string }[];
  overrides: PlayerExposureOverride[];
  setOverrides: (o: PlayerExposureOverride[]) => void;
}) {
  const [playerId, setPlayerId] = useState('');
  const [min, setMin] = useState('');
  const [max, setMax] = useState('');

  function add() {
    if (!playerId) return;
    const label = playerOptions.find((p) => p.id === playerId)?.label ?? playerId;
    const next = overrides.filter((o) => o.player_id !== playerId);
    next.push({
      player_id: playerId,
      label,
      min: min ? Number(min) : undefined,
      max: max ? Number(max) : undefined,
    });
    setOverrides(next);
    setPlayerId('');
    setMin('');
    setMax('');
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-4">
        <div className="flex flex-col gap-1 sm:col-span-2">
          <Label htmlFor="exposure-override-player">Player</Label>
          <select
            id="exposure-override-player"
            className="se-focus-ring h-9 rounded-md border border-graphite-600 bg-graphite-900 px-2 text-sm"
            value={playerId}
            onChange={(e) => setPlayerId(e.target.value)}
          >
            <option value="">Select a player…</option>
            {playerOptions.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="exposure-override-min">Min exposure %</Label>
          <Input id="exposure-override-min" type="number" min="0" max="100" value={min} onChange={(e) => setMin(e.target.value)} />
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="exposure-override-max">Max exposure %</Label>
          <Input id="exposure-override-max" type="number" min="0" max="100" value={max} onChange={(e) => setMax(e.target.value)} />
        </div>
      </div>
      <div>
        <Button type="button" variant="secondary" size="sm" onClick={add} disabled={!playerId || (!min && !max)}>
          Add override
        </Button>
      </div>

      {overrides.length > 0 ? (
        <ul className="flex flex-col gap-1">
          {overrides.map((o) => (
            <li key={o.player_id} className="flex items-center justify-between rounded-md border border-graphite-700 px-3 py-1.5 text-xs">
              <span>
                {o.label}{' '}
                {o.min !== undefined ? <Badge variant="outline" className="ml-1">min {o.min}%</Badge> : null}
                {o.max !== undefined ? <Badge variant="outline" className="ml-1">max {o.max}%</Badge> : null}
              </span>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={() => setOverrides(overrides.filter((x) => x.player_id !== o.player_id))}
              >
                Remove
              </Button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-xs text-ink-400">
          Per-player overrides always win over the global max/min exposure percentages above.
        </p>
      )}
    </div>
  );
}
