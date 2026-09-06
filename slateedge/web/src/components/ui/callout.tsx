import * as React from 'react';
import { AlertTriangle, Info, ShieldAlert } from 'lucide-react';
import { cn } from '@/lib/utils';

type CalloutVariant = 'info' | 'warning' | 'danger';

const styles: Record<CalloutVariant, string> = {
  info: 'border-teal-500/30 bg-teal-500/10 text-teal-200',
  warning: 'border-amber-500/30 bg-amber-500/10 text-amber-200',
  danger: 'border-rose-500/30 bg-rose-500/10 text-rose-200',
};

const icons: Record<CalloutVariant, React.ElementType> = {
  info: Info,
  warning: AlertTriangle,
  danger: ShieldAlert,
};

export function Callout({
  variant = 'info',
  title,
  children,
  className,
}: {
  variant?: CalloutVariant;
  title?: string;
  children: React.ReactNode;
  className?: string;
}) {
  const Icon = icons[variant];
  return (
    <div className={cn('flex gap-3 rounded-md border p-3 text-sm', styles[variant], className)} role="status">
      <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
      <div>
        {title ? <p className="mb-0.5 font-semibold">{title}</p> : null}
        <div className="text-xs leading-relaxed opacity-90">{children}</div>
      </div>
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-graphite-600 p-10 text-center">
      <p className="text-sm font-medium text-ink-50">{title}</p>
      {description ? <p className="max-w-md text-xs text-ink-400">{description}</p> : null}
      {action}
    </div>
  );
}
