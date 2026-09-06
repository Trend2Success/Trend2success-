'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { NAV_ITEMS, ONBOARDING_ITEM } from '@/lib/nav';
import { cn } from '@/lib/utils';
import { logoutAction } from '@/server/actions/auth';
import { LogOut, Compass } from 'lucide-react';
import type { SlateOption } from '@/components/slate-switcher';
import { SlateSwitcher } from '@/components/slate-switcher';

export function AppShell({
  children,
  displayName,
  slates,
  activeSlateId,
}: {
  children: React.ReactNode;
  displayName: string;
  slates: SlateOption[];
  activeSlateId?: string;
}) {
  const pathname = usePathname();

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <aside className="hidden w-60 shrink-0 flex-col border-r border-graphite-700 bg-graphite-900 md:flex">
        <div className="flex items-center gap-2 px-5 py-5">
          <span className="h-2.5 w-2.5 rounded-full bg-teal-500" />
          <span className="text-lg font-semibold tracking-tight">SlateEdge</span>
        </div>
        <nav className="flex flex-1 flex-col gap-0.5 px-3">
          {NAV_ITEMS.map((item) => {
            const active = pathname.startsWith(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  'se-focus-ring flex items-center gap-3 rounded-md px-3 py-2 text-sm text-ink-400 hover:bg-graphite-800 hover:text-ink-50',
                  active && 'bg-teal-500/10 text-teal-300'
                )}
              >
                <Icon className="h-4 w-4" aria-hidden />
                {item.label}
              </Link>
            );
          })}
          <Link
            href={ONBOARDING_ITEM.href}
            className={cn(
              'se-focus-ring mt-2 flex items-center gap-3 rounded-md border border-dashed border-graphite-600 px-3 py-2 text-sm text-ink-400 hover:bg-graphite-800 hover:text-ink-50',
              pathname.startsWith('/onboarding') && 'border-teal-500/40 text-teal-300'
            )}
          >
            <Compass className="h-4 w-4" aria-hidden />
            Onboarding Wizard
          </Link>
        </nav>
        <div className="border-t border-graphite-700 p-3">
          <p className="truncate px-2 text-xs text-ink-400">{displayName}</p>
          <form action={logoutAction}>
            <button
              type="submit"
              className="se-focus-ring mt-1 flex w-full items-center gap-2 rounded-md px-2 py-2 text-xs text-ink-400 hover:bg-graphite-800 hover:text-ink-50"
            >
              <LogOut className="h-3.5 w-3.5" /> Sign out
            </button>
          </form>
        </div>
      </aside>

      <div className="flex min-h-screen flex-1 flex-col">
        <header className="flex items-center justify-between gap-3 border-b border-graphite-700 bg-graphite-900/60 px-4 py-3 md:px-6">
          <div className="flex items-center gap-2 md:hidden">
            <span className="h-2.5 w-2.5 rounded-full bg-teal-500" />
            <span className="text-base font-semibold">SlateEdge</span>
          </div>
          <div className="flex items-center gap-2 text-xs text-ink-400">
            <span className="hidden sm:inline">Active slate</span>
            <SlateSwitcher slates={slates} activeSlateId={activeSlateId} />
          </div>
        </header>

        <main className="flex-1 px-4 py-5 pb-24 md:px-6 md:pb-6">{children}</main>

        <footer className="border-t border-graphite-700 bg-graphite-900/80 px-4 py-3 text-center text-[11px] leading-relaxed text-ink-400 md:px-6">
          DFS involves financial risk. Use a fixed entertainment budget. Model outputs are estimates and do not
          guarantee results. SlateEdge is an independent analysis tool and is not affiliated with, endorsed by, or
          connected to DraftKings or any contest operator.
        </footer>

        <nav className="fixed inset-x-0 bottom-0 z-40 flex items-center justify-between overflow-x-auto border-t border-graphite-700 bg-graphite-900/95 px-1 py-1 backdrop-blur md:hidden">
          {NAV_ITEMS.map((item) => {
            const active = pathname.startsWith(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  'se-focus-ring flex min-w-[64px] flex-col items-center gap-0.5 rounded-md px-2 py-1.5 text-[10px] text-ink-400',
                  active && 'text-teal-300'
                )}
              >
                <Icon className="h-4 w-4" aria-hidden />
                {item.shortLabel ?? item.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </div>
  );
}
