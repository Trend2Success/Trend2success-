import Link from 'next/link';
import { CheckCircle2, Circle } from 'lucide-react';
import { requireUser } from '@/lib/auth';
import { prisma } from '@/lib/db';
import { getActiveSlate } from '@/lib/activeSlate';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

export default async function OnboardingPage() {
  const user = await requireUser();
  const slate = await getActiveSlate();

  const [playerCount, projectionCount, lineupCount, resultCount] = slate
    ? await Promise.all([
        prisma.player.count({ where: { slateId: slate.id } }),
        prisma.projectionSnapshot.count({ where: { player: { slateId: slate.id } } }),
        prisma.lineup.count({ where: { run: { slateId: slate.id } } }),
        prisma.contestResult.count({ where: { slate: { userId: user.id } } }),
      ])
    : [0, 0, 0, 0];

  const steps = [
    { title: 'Create your first slate', done: !!slate, href: '/slates', description: 'Give it a name and contest date, or let a salary CSV create it automatically.' },
    { title: 'Download the CSV templates', done: true, href: '/slates', description: 'Salary, projection, and results templates are always available on the Slate Data Import page.' },
    { title: 'Upload salary and projection data', done: playerCount > 0 && projectionCount > 0, href: '/slates', description: 'Import the salary CSV first, then a projection CSV for the same slate.' },
    { title: 'Review the player pool', done: playerCount > 0, href: '/players', description: 'Check positions, salaries, and flag anyone to lock or exclude.' },
    { title: 'Configure optimizer rules', done: false, href: '/lineups', description: 'Set roster construction, exposure limits, stacking, and groups — or describe them in plain English to the AI rules assistant.' },
    { title: 'Generate lineups', done: lineupCount > 0, href: '/lineups', description: 'Model-ranked lineups, never guaranteed winners.' },
    { title: 'Review exposures', done: lineupCount > 0, href: '/portfolio', description: 'Check player, team, and game exposure warnings before you finalize anything.' },
    { title: 'Export manually', done: false, href: '/portfolio', description: 'Download a CSV and upload it yourself wherever you enter contests. SlateEdge never submits entries for you.' },
    { title: 'Track results later', done: resultCount > 0, href: '/results', description: 'Import your own results CSV after contests lock to build a track record.' },
  ];

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4">
      <div>
        <h1 className="text-xl font-semibold">Onboarding Wizard</h1>
        <p className="text-sm text-ink-400">A suggested order to get from zero to your first set of lineups.</p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Setup checklist</CardTitle>
          <CardDescription>Steps are independent — jump to any of them in any order.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col divide-y divide-graphite-700">
          {steps.map((step, idx) => (
            <div key={step.title} className="flex items-start gap-3 py-3">
              {step.done ? (
                <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-teal-400" />
              ) : (
                <Circle className="mt-0.5 h-5 w-5 shrink-0 text-ink-600" />
              )}
              <div className="flex-1">
                <p className={cn('text-sm font-medium', step.done ? 'text-ink-400 line-through' : 'text-ink-50')}>
                  {idx + 1}. {step.title}
                </p>
                <p className="text-xs text-ink-400">{step.description}</p>
              </div>
              <Button asChild size="sm" variant="outline">
                <Link href={step.href}>Go</Link>
              </Button>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
