import { redirect } from "next/navigation";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import SignOutButton from "./sign-out-button";

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  const { data: profile } = await supabase
    .from("profiles")
    .select("role, full_name")
    .eq("id", user.id)
    .maybeSingle();

  if (!profile) {
    // Authenticated with Supabase but has no app profile yet — an admin
    // hasn't provisioned this account. Nothing to show them.
    redirect("/login");
  }

  return (
    <div className="min-h-screen">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-4">
        <span className="font-semibold text-brand-dark">Lead Rescue AI</span>
        <div className="flex items-center gap-4 text-sm text-slate-600">
          <span>{profile.full_name ?? user.email}</span>
          <span className="rounded bg-slate-100 px-2 py-1 text-xs uppercase tracking-wide">
            {profile.role}
          </span>
          <SignOutButton />
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-8">{children}</main>
    </div>
  );
}
