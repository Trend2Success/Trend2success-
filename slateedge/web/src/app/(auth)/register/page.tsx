'use client';

import { useFormState, useFormStatus } from 'react-dom';
import Link from 'next/link';
import { registerAction, AuthFormState } from '@/server/actions/auth';
import { Button } from '@/components/ui/button';
import { Input, Label } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Callout } from '@/components/ui/callout';

const initialState: AuthFormState = {};

function SubmitButton() {
  const { pending } = useFormStatus();
  return (
    <Button type="submit" disabled={pending} className="w-full">
      {pending ? 'Creating account…' : 'Create account'}
    </Button>
  );
}

export default function RegisterPage() {
  const [state, formAction] = useFormState(registerAction, initialState);

  return (
    <div className="flex min-h-screen items-center justify-center bg-graphite-950 px-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <div className="mb-2 flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-teal-500" />
            <span className="text-lg font-semibold tracking-tight">SlateEdge</span>
          </div>
          <CardTitle>Create your account</CardTitle>
          <CardDescription>For personal use. No DraftKings login is ever requested or stored.</CardDescription>
        </CardHeader>
        <CardContent>
          <form action={formAction} className="flex flex-col gap-3">
            <div className="flex flex-col gap-1">
              <Label htmlFor="displayName">Display name (optional)</Label>
              <Input id="displayName" name="displayName" type="text" autoComplete="nickname" />
            </div>
            <div className="flex flex-col gap-1">
              <Label htmlFor="email">Email</Label>
              <Input id="email" name="email" type="email" required autoComplete="email" />
            </div>
            <div className="flex flex-col gap-1">
              <Label htmlFor="password">Password</Label>
              <Input id="password" name="password" type="password" required minLength={8} autoComplete="new-password" />
            </div>
            {state?.error ? <p className="text-xs text-rose-400">{state.error}</p> : null}
            <SubmitButton />
          </form>
          <Callout variant="info" className="mt-4">
            DFS involves financial risk. Use a fixed entertainment budget. Model outputs are estimates and do not
            guarantee results.
          </Callout>
          <p className="mt-4 text-center text-xs text-ink-400">
            Already have an account?{' '}
            <Link href="/login" className="text-teal-400 hover:underline">
              Sign in
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
