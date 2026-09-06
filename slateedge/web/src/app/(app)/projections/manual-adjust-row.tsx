'use client';

import { useState, useTransition } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { manualAdjustProjectionAction } from '@/server/actions/projections';

export function ManualAdjustRow({ playerId }: { playerId: string }) {
  const [kind, setKind] = useState<'points' | 'percent'>('points');
  const [delta, setDelta] = useState('0');
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  function apply() {
    const fd = new FormData();
    fd.set('playerId', playerId);
    fd.set('kind', kind);
    fd.set('delta', delta);
    startTransition(async () => {
      await manualAdjustProjectionAction(fd);
      router.refresh();
    });
  }

  return (
    <div className="flex items-center gap-1">
      <Input
        type="number"
        step="0.1"
        value={delta}
        onChange={(e) => setDelta(e.target.value)}
        className="h-8 w-20"
      />
      <Select value={kind} onValueChange={(v) => setKind(v as 'points' | 'percent')}>
        <SelectTrigger className="h-8 w-20">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="points">pts</SelectItem>
          <SelectItem value="percent">%</SelectItem>
        </SelectContent>
      </Select>
      <Button size="sm" variant="secondary" onClick={apply} disabled={pending}>
        {pending ? '…' : 'Apply'}
      </Button>
    </div>
  );
}
