'use client';

import { useTransition } from 'react';
import { useRouter } from 'next/navigation';
import { linkContestResultToLineupAction } from '@/server/actions/results';

export function LinkLineupSelect({
  resultId,
  linkedLineupId,
  options,
}: {
  resultId: string;
  linkedLineupId: string | null;
  options: { id: string; label: string }[];
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  if (options.length === 0) {
    return <span className="text-xs text-ink-600">No lineups for this slate</span>;
  }

  return (
    <select
      className="se-focus-ring h-8 rounded-md border border-graphite-600 bg-graphite-900 px-2 text-xs text-ink-50"
      value={linkedLineupId ?? ''}
      disabled={pending}
      onChange={(e) => {
        const fd = new FormData();
        fd.set('resultId', resultId);
        fd.set('lineupId', e.target.value);
        startTransition(async () => {
          await linkContestResultToLineupAction(fd);
          router.refresh();
        });
      }}
    >
      <option value="">Not linked</option>
      {options.map((o) => (
        <option key={o.id} value={o.id}>
          {o.label}
        </option>
      ))}
    </select>
  );
}
