'use client';

import { cloneElement, useMemo, useState, useTransition } from 'react';
import { useRouter } from 'next/navigation';
import { useFormState, useFormStatus } from 'react-dom';
import { Button } from '@/components/ui/button';
import { Input, Label } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Callout } from '@/components/ui/callout';
import { Badge } from '@/components/ui/badge';
import { runOptimizerAction, LineupFormState } from '@/server/actions/lineups';
import { deleteLineupPresetAction } from '@/server/actions/presets';
import { AiAssistant } from './ai-assistant';
import { GroupBuilder } from './group-builder';
import { RosterEditor } from './roster-editor';
import { ExposureOverrides } from './exposure-overrides';
import { SavePresetDialog } from './save-preset-dialog';
import {
  LINEUP_PRESETS,
  GroupRule,
  PlayerExposureOverride,
  DEFAULT_ROSTER_SLOTS,
  DEFAULT_FLEX_POSITIONS,
} from '@/lib/optimizer/types';
import type { ProposedRulePatch } from '@/lib/ai-assistant/parseRules';

interface FormSettings {
  presetName: string;
  numLineups: string;
  salaryCap: string;
  minSalary: string;
  maxSalary: string;
  minUnique: string;
  maxPerTeam: string;
  minPerGame: string;
  maxPerGame: string;
  globalMaxOwnership: string;
  minTotalProjection: string;
  minTotalCeiling: string;
  globalMaxExposurePct: string;
  globalMinExposurePct: string;
  weightProjection: string;
  weightCeiling: string;
  weightLeverage: string;
  weightOwnershipPenalty: string;
  qbStackMin: string;
  qbStackMax: string;
  bringBackMin: string;
  allowRbWithQb: boolean;
  allowDstVsOffense: boolean;
  reproducible: boolean;
  randomSeed: string;
}

interface FullSnapshot {
  settings: FormSettings;
  rosterSlots: string[];
  flexPositions: string[];
  groups: GroupRule[];
  exposureOverrides: PlayerExposureOverride[];
}

const DEFAULTS: FormSettings = {
  presetName: 'Custom',
  numLineups: '1',
  salaryCap: '50000',
  minSalary: '0',
  maxSalary: '50000',
  minUnique: '0',
  maxPerTeam: '4',
  minPerGame: '',
  maxPerGame: '',
  globalMaxOwnership: '',
  minTotalProjection: '',
  minTotalCeiling: '',
  globalMaxExposurePct: '',
  globalMinExposurePct: '',
  weightProjection: '1',
  weightCeiling: '0',
  weightLeverage: '0',
  weightOwnershipPenalty: '0',
  qbStackMin: '0',
  qbStackMax: '3',
  bringBackMin: '0',
  allowRbWithQb: true,
  allowDstVsOffense: false,
  reproducible: false,
  randomSeed: '42',
};

function SubmitButton() {
  const { pending } = useFormStatus();
  return (
    <Button type="submit" size="lg" disabled={pending}>
      {pending ? 'Generating…' : 'Generate model-ranked lineups'}
    </Button>
  );
}

export interface SavedPreset {
  id: string;
  name: string;
  settingsJson: unknown;
}

export function LineupBuilderForm({
  slateId,
  salaryCapDefault,
  playerOptions,
  savedPresets,
}: {
  slateId: string;
  salaryCapDefault: number;
  playerOptions: { id: string; label: string }[];
  savedPresets: SavedPreset[];
}) {
  const router = useRouter();
  const [deleting, startDeleteTransition] = useTransition();
  const [settings, setSettings] = useState<FormSettings>({
    ...DEFAULTS,
    salaryCap: String(salaryCapDefault),
    maxSalary: String(salaryCapDefault),
  });
  const [rosterSlots, setRosterSlots] = useState<string[]>(DEFAULT_ROSTER_SLOTS);
  const [flexPositions, setFlexPositions] = useState<string[]>(DEFAULT_FLEX_POSITIONS);
  const [groups, setGroups] = useState<GroupRule[]>([]);
  const [exposureOverrides, setExposureOverrides] = useState<PlayerExposureOverride[]>([]);
  const [state, formAction] = useFormState(runOptimizerAction, {} as LineupFormState);

  function set<K extends keyof FormSettings>(key: K, value: FormSettings[K]) {
    setSettings((s) => ({ ...s, [key]: value }));
  }

  function applyPreset(name: string) {
    const preset = LINEUP_PRESETS.find((p) => p.name === name);
    if (!preset) {
      setSettings((s) => ({ ...s, presetName: 'Custom' }));
      return;
    }
    setSettings((s) => ({
      ...s,
      presetName: preset.name,
      numLineups: String(preset.num_lineups),
      minUnique: String(preset.min_unique_players),
      globalMaxExposurePct: String(preset.max_exposure_default * 100),
      globalMaxOwnership: preset.global_max_ownership !== null ? String(preset.global_max_ownership) : '',
      weightProjection: String(preset.objective_weights.projection),
      weightCeiling: String(preset.objective_weights.ceiling),
      weightLeverage: String(preset.objective_weights.leverage),
      weightOwnershipPenalty: String(preset.objective_weights.ownership_penalty),
      qbStackMin: String(preset.stack_rules.qb_stack_min),
      qbStackMax: String(preset.stack_rules.qb_stack_max),
      bringBackMin: String(preset.stack_rules.bring_back_min),
      allowRbWithQb: preset.stack_rules.allow_rb_with_qb,
      allowDstVsOffense: preset.stack_rules.allow_dst_vs_offense,
    }));
  }

  function applySnapshot(snapshot: Partial<FullSnapshot>, name: string) {
    if (snapshot.settings) setSettings({ ...DEFAULTS, ...snapshot.settings, presetName: name });
    if (snapshot.rosterSlots) setRosterSlots(snapshot.rosterSlots);
    if (snapshot.flexPositions) setFlexPositions(snapshot.flexPositions);
    if (snapshot.groups) setGroups(snapshot.groups);
    if (snapshot.exposureOverrides) setExposureOverrides(snapshot.exposureOverrides);
  }

  function applyAiPatch(patch: ProposedRulePatch) {
    setSettings((s) => ({
      ...s,
      presetName: 'Custom',
      numLineups: patch.num_lineups !== undefined ? String(patch.num_lineups) : s.numLineups,
      minSalary: patch.min_salary !== undefined ? String(patch.min_salary) : s.minSalary,
      maxSalary: patch.max_salary !== undefined ? String(patch.max_salary) : s.maxSalary,
      minUnique: patch.min_unique_players !== undefined ? String(patch.min_unique_players) : s.minUnique,
      globalMaxExposurePct: patch.global_max_exposure_pct !== undefined ? String(patch.global_max_exposure_pct) : s.globalMaxExposurePct,
      globalMaxOwnership: patch.global_max_ownership !== undefined ? String(patch.global_max_ownership) : s.globalMaxOwnership,
      qbStackMin: patch.stack_rules?.qb_stack_min !== undefined ? String(patch.stack_rules.qb_stack_min) : s.qbStackMin,
      qbStackMax: patch.stack_rules?.qb_stack_max !== undefined ? String(patch.stack_rules.qb_stack_max) : s.qbStackMax,
      bringBackMin: patch.stack_rules?.bring_back_min !== undefined ? String(patch.stack_rules.bring_back_min) : s.bringBackMin,
      allowRbWithQb: patch.stack_rules?.allow_rb_with_qb ?? s.allowRbWithQb,
      allowDstVsOffense: patch.stack_rules?.allow_dst_vs_offense ?? s.allowDstVsOffense,
      weightOwnershipPenalty:
        patch.objective_weights?.ownership_penalty !== undefined
          ? String(patch.objective_weights.ownership_penalty)
          : s.weightOwnershipPenalty,
      weightCeiling: patch.objective_weights?.ceiling !== undefined ? String(patch.objective_weights.ceiling) : s.weightCeiling,
      weightLeverage: patch.objective_weights?.leverage !== undefined ? String(patch.objective_weights.leverage) : s.weightLeverage,
    }));
  }

  const groupsJson = useMemo(() => JSON.stringify(groups), [groups]);
  const rosterSlotsJson = useMemo(() => JSON.stringify(rosterSlots), [rosterSlots]);
  const flexPositionsJson = useMemo(() => JSON.stringify(flexPositions), [flexPositions]);
  const perPlayerExposureJson = useMemo(() => JSON.stringify(exposureOverrides), [exposureOverrides]);

  function snapshotJson(): string {
    const snapshot: FullSnapshot = { settings, rosterSlots, flexPositions, groups, exposureOverrides };
    return JSON.stringify(snapshot);
  }

  return (
    <div className="flex flex-col gap-6">
      <AiAssistant onApply={applyAiPatch} />

      <Card>
        <CardHeader>
          <CardTitle>Presets</CardTitle>
          <CardDescription>Starting points only — not proven strategies. Fully editable below.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="flex flex-wrap gap-2">
            {['Custom', ...LINEUP_PRESETS.map((p) => p.name)].map((name) => (
              <Button
                key={name}
                type="button"
                size="sm"
                variant={settings.presetName === name ? 'default' : 'outline'}
                onClick={() => applyPreset(name)}
              >
                {name}
              </Button>
            ))}
          </div>

          {savedPresets.length > 0 ? (
            <div>
              <p className="mb-1 text-xs font-medium text-ink-400">Your saved presets</p>
              <div className="flex flex-wrap gap-2">
                {savedPresets.map((p) => (
                  <div key={p.id} className="flex items-center gap-1 rounded-md border border-graphite-600 bg-graphite-900 pl-1">
                    <Button
                      type="button"
                      size="sm"
                      variant={settings.presetName === p.name ? 'default' : 'ghost'}
                      onClick={() => applySnapshot(p.settingsJson as Partial<FullSnapshot>, p.name)}
                    >
                      {p.name}
                    </Button>
                    <button
                      type="button"
                      className="se-focus-ring px-2 text-xs text-ink-600 hover:text-rose-400"
                      disabled={deleting}
                      aria-label={`Delete preset ${p.name}`}
                      onClick={() => {
                        const fd = new FormData();
                        fd.set('presetId', p.id);
                        startDeleteTransition(async () => {
                          await deleteLineupPresetAction(fd);
                          router.refresh();
                        });
                      }}
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          <div>
            <SavePresetDialog getSnapshotJson={snapshotJson} />
          </div>
        </CardContent>
      </Card>

      <form action={formAction} className="flex flex-col gap-6">
        <input type="hidden" name="slateId" value={slateId} />
        <input type="hidden" name="presetName" value={settings.presetName} />
        <input type="hidden" name="groupsJson" value={groupsJson} />
        <input type="hidden" name="rosterSlotsJson" value={rosterSlotsJson} />
        <input type="hidden" name="flexPositionsJson" value={flexPositionsJson} />
        <input type="hidden" name="perPlayerExposureJson" value={perPlayerExposureJson} />
        <input type="hidden" name="allowRbWithQb" value={String(settings.allowRbWithQb)} />
        <input type="hidden" name="allowDstVsOffense" value={String(settings.allowDstVsOffense)} />
        <input type="hidden" name="reproducible" value={String(settings.reproducible)} />

        <Card>
          <CardHeader>
            <CardTitle>Roster construction</CardTitle>
            <CardDescription>
              Default NFL Classic: QB, RB, RB, WR, WR, WR, TE, FLEX (RB/WR/TE), DST — fully editable since roster
              rules can change.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <RosterEditor
              rosterSlots={rosterSlots}
              setRosterSlots={setRosterSlots}
              flexPositions={flexPositions}
              setFlexPositions={setFlexPositions}
            />
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Field label="Number of lineups (1-150)">
                <Input
                  name="numLineups"
                  type="number"
                  min="1"
                  max="150"
                  value={settings.numLineups}
                  onChange={(e) => set('numLineups', e.target.value)}
                />
              </Field>
              <Field label="Salary cap">
                <Input name="salaryCap" type="number" value={settings.salaryCap} onChange={(e) => set('salaryCap', e.target.value)} />
              </Field>
              <Field label="Min salary spent">
                <Input name="minSalary" type="number" value={settings.minSalary} onChange={(e) => set('minSalary', e.target.value)} />
              </Field>
              <Field label="Max salary spent">
                <Input name="maxSalary" type="number" value={settings.maxSalary} onChange={(e) => set('maxSalary', e.target.value)} />
              </Field>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Diversification & exposure</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Field label="Min unique players between lineups">
                <Input name="minUnique" type="number" min="0" value={settings.minUnique} onChange={(e) => set('minUnique', e.target.value)} />
              </Field>
              <Field label="Global max exposure per player (%)">
                <Input
                  name="globalMaxExposurePct"
                  type="number"
                  min="0"
                  max="100"
                  value={settings.globalMaxExposurePct}
                  onChange={(e) => set('globalMaxExposurePct', e.target.value)}
                />
              </Field>
              <Field label="Global min exposure per player (%)">
                <Input
                  name="globalMinExposurePct"
                  type="number"
                  min="0"
                  max="100"
                  value={settings.globalMinExposurePct}
                  onChange={(e) => set('globalMinExposurePct', e.target.value)}
                />
              </Field>
              <Field label="Max players from one team">
                <Input name="maxPerTeam" type="number" min="1" value={settings.maxPerTeam} onChange={(e) => set('maxPerTeam', e.target.value)} />
              </Field>
              <Field label="Global max total lineup ownership (%)">
                <Input
                  name="globalMaxOwnership"
                  type="number"
                  value={settings.globalMaxOwnership}
                  onChange={(e) => set('globalMaxOwnership', e.target.value)}
                />
              </Field>
              <Field label="Min players per game">
                <Input name="minPerGame" type="number" value={settings.minPerGame} onChange={(e) => set('minPerGame', e.target.value)} />
              </Field>
              <Field label="Max players per game">
                <Input name="maxPerGame" type="number" value={settings.maxPerGame} onChange={(e) => set('maxPerGame', e.target.value)} />
              </Field>
              <Field label="Min total lineup projection">
                <Input
                  name="minTotalProjection"
                  type="number"
                  value={settings.minTotalProjection}
                  onChange={(e) => set('minTotalProjection', e.target.value)}
                />
              </Field>
              <Field label="Min total lineup ceiling">
                <Input
                  name="minTotalCeiling"
                  type="number"
                  value={settings.minTotalCeiling}
                  onChange={(e) => set('minTotalCeiling', e.target.value)}
                />
              </Field>
            </div>

            <div>
              <p className="mb-2 text-xs font-medium text-ink-200">Per-player exposure rules</p>
              <ExposureOverrides playerOptions={playerOptions} overrides={exposureOverrides} setOverrides={setExposureOverrides} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Objective weights</CardTitle>
            <CardDescription>How the model score combines projection, ceiling, leverage, and an ownership penalty.</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Field label="Projection weight">
              <Input name="weightProjection" type="number" step="0.05" value={settings.weightProjection} onChange={(e) => set('weightProjection', e.target.value)} />
            </Field>
            <Field label="Ceiling weight">
              <Input name="weightCeiling" type="number" step="0.05" value={settings.weightCeiling} onChange={(e) => set('weightCeiling', e.target.value)} />
            </Field>
            <Field label="Leverage weight">
              <Input name="weightLeverage" type="number" step="0.05" value={settings.weightLeverage} onChange={(e) => set('weightLeverage', e.target.value)} />
            </Field>
            <Field label="Ownership penalty weight">
              <Input
                name="weightOwnershipPenalty"
                type="number"
                step="0.05"
                value={settings.weightOwnershipPenalty}
                onChange={(e) => set('weightOwnershipPenalty', e.target.value)}
              />
            </Field>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>NFL correlation rules</CardTitle>
            <CardDescription>Optional, editable stacking logic. Defaults are a starting point, not proven strategy.</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Field label="QB stack: min pass catchers">
              <Input name="qbStackMin" type="number" min="0" max="3" value={settings.qbStackMin} onChange={(e) => set('qbStackMin', e.target.value)} />
            </Field>
            <Field label="QB stack: max pass catchers">
              <Input name="qbStackMax" type="number" min="0" max="3" value={settings.qbStackMax} onChange={(e) => set('qbStackMax', e.target.value)} />
            </Field>
            <Field label="Min opponent bring-back">
              <Input name="bringBackMin" type="number" min="0" value={settings.bringBackMin} onChange={(e) => set('bringBackMin', e.target.value)} />
            </Field>
            <div className="flex flex-col justify-end gap-2 pb-1">
              <label className="flex items-center gap-2 text-xs text-ink-200">
                <Checkbox checked={settings.allowRbWithQb} onCheckedChange={(v) => set('allowRbWithQb', v === true)} />
                Allow RB from same team as QB
              </label>
              <label className="flex items-center gap-2 text-xs text-ink-200">
                <Checkbox checked={settings.allowDstVsOffense} onCheckedChange={(v) => set('allowDstVsOffense', v === true)} />
                Allow DST against rostered offense
              </label>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Player groups</CardTitle>
            <CardDescription>At-least / at-most / exactly / if-then / exclude-together rules across specific players.</CardDescription>
          </CardHeader>
          <CardContent>
            <GroupBuilder playerOptions={playerOptions} groups={groups} setGroups={setGroups} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Reproducibility</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-xs text-ink-200">
              <Checkbox checked={settings.reproducible} onCheckedChange={(v) => set('reproducible', v === true)} />
              Reproducible run (fixed random seed)
            </label>
            {settings.reproducible ? (
              <Input
                name="randomSeed"
                type="number"
                className="w-28"
                value={settings.randomSeed}
                onChange={(e) => set('randomSeed', e.target.value)}
              />
            ) : null}
          </CardContent>
        </Card>

        {state?.error ? <Callout variant="danger">{state.error}</Callout> : null}
        {state?.success ? <Callout variant="info">{state.success}</Callout> : null}
        {state?.warnings && state.warnings.length > 0 ? (
          <Callout variant="warning" title="Optimizer warnings">
            <ul className="list-inside list-disc">
              {state.warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          </Callout>
        ) : null}

        <div className="flex items-center gap-2">
          <SubmitButton />
          {settings.presetName !== 'Custom' ? <Badge variant="outline">Using preset: {settings.presetName}</Badge> : null}
        </div>
      </form>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactElement }) {
  const id = useMemo(() => `field-${label.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`, [label]);
  return (
    <div className="flex flex-col gap-1">
      <Label htmlFor={id}>{label}</Label>
      {cloneElement(children, { id })}
    </div>
  );
}
