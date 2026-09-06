'use client';

import { createContext, useCallback, useContext, useRef, useState } from 'react';
import { Undo2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface PendingUndo {
  id: string;
  label: string;
}

interface UndoContextValue {
  /** Shows a "<label> Undo" bar for `delayMs`; `run` only fires if the user
   * does not click Undo before the timer elapses. Used for every destructive
   * local action (delete lineup/run/slate/result) so nothing is permanently
   * removed without a window to cancel it. */
  scheduleUndoable: (label: string, run: () => Promise<void> | void, delayMs?: number) => void;
}

const UndoContext = createContext<UndoContextValue | null>(null);

export function useUndoable() {
  const ctx = useContext(UndoContext);
  if (!ctx) throw new Error('useUndoable must be used within UndoProvider');
  return ctx;
}

export function UndoProvider({ children }: { children: React.ReactNode }) {
  const [pending, setPending] = useState<PendingUndo[]>([]);
  const timers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  const scheduleUndoable = useCallback((label: string, run: () => Promise<void> | void, delayMs = 6000) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    setPending((p) => [...p, { id, label }]);
    const timeout = setTimeout(async () => {
      timers.current.delete(id);
      setPending((p) => p.filter((x) => x.id !== id));
      await run();
    }, delayMs);
    timers.current.set(id, timeout);
  }, []);

  function cancel(id: string) {
    const timeout = timers.current.get(id);
    if (timeout) clearTimeout(timeout);
    timers.current.delete(id);
    setPending((p) => p.filter((x) => x.id !== id));
  }

  return (
    <UndoContext.Provider value={{ scheduleUndoable }}>
      {children}
      {pending.length > 0 ? (
        <div className="fixed bottom-16 left-1/2 z-50 flex -translate-x-1/2 flex-col items-center gap-2 md:bottom-4">
          {pending.map((p) => (
            <div
              key={p.id}
              role="status"
              className="flex items-center gap-3 rounded-md border border-graphite-600 bg-graphite-800 px-4 py-2 text-sm text-ink-50 shadow-lg"
            >
              <span>{p.label}</span>
              <Button size="sm" variant="secondary" onClick={() => cancel(p.id)}>
                <Undo2 className="mr-1 h-3.5 w-3.5" /> Undo
              </Button>
            </div>
          ))}
        </div>
      ) : null}
    </UndoContext.Provider>
  );
}
