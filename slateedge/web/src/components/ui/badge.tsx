import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center gap-1 rounded-sm border px-2 py-0.5 text-xs font-medium',
  {
    variants: {
      variant: {
        default: 'border-graphite-600 bg-graphite-800 text-ink-200',
        teal: 'border-teal-500/40 bg-teal-500/10 text-teal-300',
        amber: 'border-amber-500/40 bg-amber-500/10 text-amber-300',
        rose: 'border-rose-500/40 bg-rose-500/10 text-rose-400',
        outline: 'border-graphite-600 text-ink-400',
      },
    },
    defaultVariants: { variant: 'default' },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant, className }))} {...props} />;
}
