'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input, Label } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

export function ExportControls({ runId, defaultSlots }: { runId: string; defaultSlots: string[] }) {
  const [slotsText, setSlotsText] = useState(defaultSlots.join(','));
  const [field, setField] = useState<'name' | 'id'>('name');

  const slotsParam = slotsText
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
    .join(',');
  const href = `/api/export/lineups?runId=${runId}&field=${field}${slotsParam ? `&slots=${encodeURIComponent(slotsParam)}` : ''}`;

  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:gap-3">
      <div className="flex flex-col gap-1">
        <Label className="text-[10px]">Column order (comma-separated slot labels)</Label>
        <Input value={slotsText} onChange={(e) => setSlotsText(e.target.value)} className="h-8 w-64 text-xs" />
      </div>
      <div className="flex flex-col gap-1">
        <Label className="text-[10px]">Cell contents</Label>
        <Select value={field} onValueChange={(v) => setField(v as 'name' | 'id')}>
          <SelectTrigger className="h-8 w-36">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="name">Name (ID)</SelectItem>
            <SelectItem value="id">ID only</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <Button asChild variant="secondary" size="sm">
        <a href={href}>Export CSV</a>
      </Button>
    </div>
  );
}
