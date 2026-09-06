'use client';

import { useState, useTransition } from 'react';
import { useRouter } from 'next/navigation';
import { Lock, Ban, StickyNote, Tag as TagIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { PlayerTagBadge, ALL_TAGS } from '@/components/player-tag-badge';
import { togglePlayerFlagAction, updatePlayerNotesAction, togglePlayerTagAction } from '@/server/actions/players';
import { cn } from '@/lib/utils';

export function LockExcludeButtons({ playerId, locked, excluded }: { playerId: string; locked: boolean; excluded: boolean }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  function toggle(flag: 'locked' | 'excluded', value: boolean) {
    const fd = new FormData();
    fd.set('playerId', playerId);
    fd.set('flag', flag);
    fd.set('value', String(value));
    startTransition(async () => {
      await togglePlayerFlagAction(fd);
      router.refresh();
    });
  }

  return (
    <div className="flex items-center gap-1">
      <Button
        size="icon"
        variant={locked ? 'default' : 'ghost'}
        disabled={pending}
        title="Lock player into every lineup"
        onClick={() => toggle('locked', !locked)}
        className="h-7 w-7"
      >
        <Lock className="h-3.5 w-3.5" />
      </Button>
      <Button
        size="icon"
        variant={excluded ? 'destructive' : 'ghost'}
        disabled={pending}
        title="Exclude player from all lineups"
        onClick={() => toggle('excluded', !excluded)}
        className="h-7 w-7"
      >
        <Ban className="h-3.5 w-3.5" />
      </Button>
    </div>
  );
}

export function NotesDialog({ playerId, notes }: { playerId: string; notes: string }) {
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState(notes);
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  function save() {
    const fd = new FormData();
    fd.set('playerId', playerId);
    fd.set('notes', value);
    startTransition(async () => {
      await updatePlayerNotesAction(fd);
      setOpen(false);
      router.refresh();
    });
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="icon" variant="ghost" className={cn('h-7 w-7', notes && 'text-teal-400')} title="Notes">
          <StickyNote className="h-3.5 w-3.5" />
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Player notes</DialogTitle>
        </DialogHeader>
        <Textarea value={value} onChange={(e) => setValue(e.target.value)} rows={5} placeholder="Your notes on this player…" />
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={save} disabled={pending}>
            {pending ? 'Saving…' : 'Save notes'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function TagsDialog({ playerId, tags }: { playerId: string; tags: { tag: string; label: string | null }[] }) {
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const activeTags = new Set(tags.map((t) => t.tag));

  function toggle(tag: string) {
    const fd = new FormData();
    fd.set('playerId', playerId);
    fd.set('tag', tag);
    fd.set('add', String(!activeTags.has(tag)));
    startTransition(async () => {
      await togglePlayerTagAction(fd);
      router.refresh();
    });
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <div className="flex cursor-pointer flex-wrap items-center gap-1">
          {tags.length === 0 ? (
            <Button size="icon" variant="ghost" className="h-7 w-7" title="Tags">
              <TagIcon className="h-3.5 w-3.5" />
            </Button>
          ) : (
            tags.map((t) => <PlayerTagBadge key={t.tag} tag={t.tag} label={t.label} />)
          )}
        </div>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Player tags</DialogTitle>
        </DialogHeader>
        <div className="flex flex-col gap-2">
          {ALL_TAGS.filter((t) => t !== 'CUSTOM').map((tag) => (
            <label key={tag} className="flex items-center gap-2 text-sm">
              <Checkbox checked={activeTags.has(tag)} disabled={pending} onCheckedChange={() => toggle(tag)} />
              <PlayerTagBadge tag={tag} />
            </label>
          ))}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Done
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
