'use client';

import { useFormState, useFormStatus } from 'react-dom';
import Link from 'next/link';
import { loginAction, AuthFormState } from '@/server/actions/auth';
import { Button } from '@/components/ui/button';
import { Input, Label } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';

const initialState: AuthFormState = {};

function SubmitButton({ label }: { label: string }) {
  const { pending } = useFormStatus();
  return (
    <Button type="submit" disabled={pending} className="w-full">
      {pending ? 'Signing in…' : label}
    </Button>
  );
}

export default function LoginPage() {
  const [state, formAction] = useFormState(loginAction, initialState);

  return (
    <div className="flex min-h-screen items-center justify-center bg-graphite-950 px-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <div className="mb-2 flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-teal-500" />
            <span className="text-lg font-semibold tracking-tight">SlateEdge</span>
          </div>
          <CardTitle>Sign in</CardTitle>
          <CardDescription>Personal DFS decision-support workspace. Local account only.</CardDescription>
        </CardHeader>
        <CardContent>
          <form action={formAction} className="flex flex-col gap-3">
            <div className="flex flex-col gap-1">
              <Label htmlFor="email">Email</Label>
              <Input id="email" name="email" type="email" required autoComplete="email" />
            </div>
            <div className="flex flex-col gap-1">
              <Label htmlFor="password">Password</Label>
              <Input id="password" name="password" type="password" required autoComplete="current-password" />
            </div>
            {state?.error ? <p className="text-xs text-rose-400">{state.error}</p> : null}
            <SubmitButton label="Sign in" />
          </form>
          <p className="mt-4 text-center text-xs text-ink-400">
            No account yet?{' '}
            <Link href="/register" className="text-teal-400 hover:underline">
              Create one
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
