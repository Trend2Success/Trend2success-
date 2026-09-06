'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input, Label } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import type { GroupRule } from '@/lib/optimizer/types';

const GROUP_LABELS: Record<GroupRule['type'], string> = {
  at_least: 'At least N of these players',
  at_most: 'At most N of these players',
  exactly: 'Exactly N of these players',
  if_then: 'If player A is used, player B must be used',
  exclude_together: 'Never use these players together',
};

export function GroupBuilder({
  playerOptions,
  groups,
  setGroups,
}: {
  playerOptions: { id: string; label: string }[];
  groups: GroupRule[];
  setGroups: (g: GroupRule[]) => void;
}) {
  const [type, setType] = useState<GroupRule['type']>('at_least');
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [count, setCount] = useState('1');
  const [ifId, setIfId] = useState('');
  const [thenId, setThenId] = useState('');

  function addGroup() {
    if (type === 'if_then') {
      if (!ifId || !thenId) return;
      setGroups([...groups, { type, player_ids: [], if_player_id: ifId, then_player_id: thenId }]);
    } else {
      if (selectedIds.length < 2 && type === 'exclude_together') return;
      if (selectedIds.length === 0) return;
      setGroups([...groups, { type, player_ids: selectedIds, count: Number(count) }]);
    }
    setSelectedIds([]);
    setIfId('');
    setThenId('');
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-4">
        <div className="flex flex-col gap-1">
          <Label>Group type</Label>
          <Select value={type} onValueChange={(v) => setType(v as GroupRule['type'])}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(GROUP_LABELS).map(([k, v]) => (
                <SelectItem key={k} value={k}>
                  {v}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {type === 'if_then' ? (
          <>
            <div className="flex flex-col gap-1">
              <Label>If player</Label>
              <select
                className="se-focus-ring h-9 rounded-md border border-graphite-600 bg-graphite-900 px-2 text-sm"
                value={ifId}
                onChange={(e) => setIfId(e.target.value)}
              >
                <option value="">Select…</option>
                {playerOptions.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <Label>Then player</Label>
              <select
                className="se-focus-ring h-9 rounded-md border border-graphite-600 bg-graphite-900 px-2 text-sm"
                value={thenId}
                onChange={(e) => setThenId(e.target.value)}
              >
                <option value="">Select…</option>
                {playerOptions.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.label}
                  </option>
                ))}
              </select>
            </div>
          </>
        ) : (
          <>
            <div className="flex flex-col gap-1 sm:col-span-2">
              <Label>Players (ctrl/cmd-click for multiple)</Label>
              <select
                multiple
                className="se-focus-ring h-24 rounded-md border border-graphite-600 bg-graphite-900 px-2 text-sm"
                value={selectedIds}
                onChange={(e) => setSelectedIds(Array.from(e.target.selectedOptions).map((o) => o.value))}
              >
                {playerOptions.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.label}
                  </option>
                ))}
              </select>
            </div>
            {type !== 'exclude_together' ? (
              <div className="flex flex-col gap-1">
                <Label>Count (N)</Label>
                <Input type="number" min="1" value={count} onChange={(e) => setCount(e.target.value)} />
              </div>
            ) : null}
          </>
        )}
      </div>
      <div>
        <Button type="button" variant="secondary" size="sm" onClick={addGroup}>
          Add rule
        </Button>
      </div>

      {groups.length > 0 ? (
        <ul className="flex flex-col gap-1">
          {groups.map((g, i) => (
            <li key={i} className="flex items-center justify-between rounded-md border border-graphite-700 px-3 py-1.5 text-xs">
              <span>
                <Badge variant="outline" className="mr-2">
                  {GROUP_LABELS[g.type]}
                </Badge>
                {g.type === 'if_then'
                  ? `${label(playerOptions, g.if_player_id)} → ${label(playerOptions, g.then_player_id)}`
                  : `${g.player_ids.map((id) => label(playerOptions, id)).join(', ')}${g.count ? ` (N=${g.count})` : ''}`}
              </span>
              <Button type="button" size="sm" variant="ghost" onClick={() => setGroups(groups.filter((_, idx) => idx !== i))}>
                Remove
              </Button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function label(options: { id: string; label: string }[], id?: string) {
  return options.find((o) => o.id === id)?.label ?? id ?? '';
}
