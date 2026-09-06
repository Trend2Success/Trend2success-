'use client';

import { usePathname } from 'next/navigation';
import { setActiveSlateAction } from '@/lib/activeSlate';

export interface SlateOption {
  id: string;
  slateName: string;
  contestDate: string;
  isDemo: boolean;
}

export function SlateSwitcher({ slates, activeSlateId }: { slates: SlateOption[]; activeSlateId?: string }) {
  const pathname = usePathname();

  if (slates.length === 0) {
    return <span className="text-xs text-ink-400">No slates yet</span>;
  }

  return (
    <form action={setActiveSlateAction} className="flex items-center gap-2">
      <input type="hidden" name="redirectTo" value={pathname} />
      <select
        name="slateId"
        defaultValue={activeSlateId}
        onChange={(e) => e.currentTarget.form?.requestSubmit()}
        className="se-focus-ring h-8 rounded-md border border-graphite-600 bg-graphite-900 px-2 text-xs text-ink-50"
        aria-label="Active slate"
      >
        {slates.map((s) => (
          <option key={s.id} value={s.id}>
            {s.slateName} · {new Date(s.contestDate).toLocaleDateString()}
            {s.isDemo ? ' (Demo)' : ''}
          </option>
        ))}
      </select>
    </form>
  );
}
