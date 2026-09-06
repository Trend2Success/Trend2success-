import { Badge } from '@/components/ui/badge';

const TAG_STYLES: Record<string, { label: string; variant: 'default' | 'teal' | 'amber' | 'rose' | 'outline' }> = {
  CORE: { label: 'Core', variant: 'teal' },
  STRONG_PLAY: { label: 'Strong Play', variant: 'teal' },
  TOURNAMENT_PIVOT: { label: 'Tournament Pivot', variant: 'outline' },
  VALUE: { label: 'Value', variant: 'default' },
  FADE: { label: 'Fade', variant: 'rose' },
  INJURY_WATCH: { label: 'Injury Watch', variant: 'amber' },
  CUSTOM: { label: 'Custom', variant: 'outline' },
};

export function PlayerTagBadge({ tag, label }: { tag: string; label?: string | null }) {
  const style = TAG_STYLES[tag] ?? TAG_STYLES.CUSTOM!;
  return <Badge variant={style.variant}>{tag === 'CUSTOM' && label ? label : style.label}</Badge>;
}

export const ALL_TAGS = Object.keys(TAG_STYLES);
