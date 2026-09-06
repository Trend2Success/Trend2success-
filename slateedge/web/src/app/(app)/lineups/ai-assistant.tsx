'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/input';
import { Callout } from '@/components/ui/callout';
import { Card as UiCard, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { parsePlainEnglishRules, ProposedRulePatch } from '@/lib/ai-assistant/parseRules';

export function AiAssistant({ onApply }: { onApply: (patch: ProposedRulePatch) => void }) {
  const [text, setText] = useState('');
  const [result, setResult] = useState<ReturnType<typeof parsePlainEnglishRules> | null>(null);
  const [applied, setApplied] = useState(false);

  function parse() {
    setResult(parsePlainEnglishRules(text));
    setApplied(false);
  }

  return (
    <UiCard>
      <CardHeader>
        <CardTitle>AI Strategy Assistant</CardTitle>
        <CardDescription>
          Describe what you want in plain English. This runs locally — it only proposes optimizer settings; nothing is
          applied until you review and click Apply. It never claims a lineup will win.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <Textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={3}
          placeholder='e.g. "Build 20 tournament lineups with QB stacks, no more than 40% exposure to any player, at least $49,000 salary used, and reduce exposure to highly owned RBs."'
        />
        <div>
          <Button type="button" variant="secondary" onClick={parse} disabled={!text.trim()}>
            Propose rules
          </Button>
        </div>

        {result ? (
          <div className="flex flex-col gap-2">
            <div className="rounded-md border border-graphite-600 bg-graphite-900 p-3 text-xs">
              <p className="mb-1 font-medium text-ink-50">Recognized:</p>
              {result.matchedPhrases.length === 0 ? (
                <p className="text-ink-400">Nothing recognized.</p>
              ) : (
                <ul className="list-inside list-disc text-ink-200">
                  {result.matchedPhrases.map((m) => (
                    <li key={m}>{m}</li>
                  ))}
                </ul>
              )}
              <pre className="mt-2 overflow-x-auto rounded bg-graphite-950 p-2 text-[11px] text-teal-300">
                {JSON.stringify(result.patch, null, 2)}
              </pre>
            </div>

            {result.assumptions.map((a, i) => (
              <Callout key={i} variant="info" title="Assumption">
                {a}
              </Callout>
            ))}
            {result.clarificationsNeeded.map((c, i) => (
              <Callout key={i} variant="warning" title="Needs clarification">
                {c}
              </Callout>
            ))}

            <div>
              <Button
                type="button"
                onClick={() => {
                  onApply(result.patch);
                  setApplied(true);
                }}
                disabled={Object.keys(result.patch).length === 0}
              >
                {applied ? 'Applied to form below' : 'Apply to Lineup Builder settings'}
              </Button>
            </div>
          </div>
        ) : null}
      </CardContent>
    </UiCard>
  );
}
