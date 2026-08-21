-- Lead Rescue AI: row-level security
--
-- Every tenant-scoped table is isolated by tenant_id. Two helper functions
-- read the calling user's own profile; they are SECURITY DEFINER so they can
-- read public.profiles without recursing into that table's own RLS policies
-- (the function owner, not the caller, is subject to RLS during execution).

create function public.current_profile_tenant_id()
returns uuid
language sql
security definer
set search_path = public
stable
as $$
  select tenant_id from public.profiles where id = auth.uid();
$$;

create function public.current_profile_role()
returns text
language sql
security definer
set search_path = public
stable
as $$
  select role from public.profiles where id = auth.uid();
$$;

grant execute on function public.current_profile_tenant_id() to authenticated;
grant execute on function public.current_profile_role() to authenticated;

alter table public.tenants enable row level security;
alter table public.profiles enable row level security;
alter table public.leads enable row level security;
alter table public.lead_events enable row level security;

-- ---------------------------------------------------------------------------
-- tenants
-- ---------------------------------------------------------------------------
create policy tenants_select on public.tenants
  for select to authenticated
  using (
    public.current_profile_role() = 'platform_admin'
    or id = public.current_profile_tenant_id()
  );

create policy tenants_insert on public.tenants
  for insert to authenticated
  with check (public.current_profile_role() = 'platform_admin');

create policy tenants_update on public.tenants
  for update to authenticated
  using (public.current_profile_role() = 'platform_admin')
  with check (public.current_profile_role() = 'platform_admin');

create policy tenants_delete on public.tenants
  for delete to authenticated
  using (public.current_profile_role() = 'platform_admin');

-- ---------------------------------------------------------------------------
-- profiles
-- ---------------------------------------------------------------------------
create policy profiles_select on public.profiles
  for select to authenticated
  using (
    public.current_profile_role() = 'platform_admin'
    or id = auth.uid()
    or tenant_id = public.current_profile_tenant_id()
  );

create policy profiles_insert on public.profiles
  for insert to authenticated
  with check (
    public.current_profile_role() = 'platform_admin'
    or (
      public.current_profile_role() = 'business_owner'
      and tenant_id = public.current_profile_tenant_id()
      and role = 'staff'
    )
  );

create policy profiles_update on public.profiles
  for update to authenticated
  using (
    public.current_profile_role() = 'platform_admin'
    or id = auth.uid()
    or (
      public.current_profile_role() = 'business_owner'
      and tenant_id = public.current_profile_tenant_id()
    )
  )
  with check (
    public.current_profile_role() = 'platform_admin'
    or id = auth.uid()
    or (
      public.current_profile_role() = 'business_owner'
      and tenant_id = public.current_profile_tenant_id()
      and role = 'staff'
    )
  );

create policy profiles_delete on public.profiles
  for delete to authenticated
  using (
    public.current_profile_role() = 'platform_admin'
    or (
      public.current_profile_role() = 'business_owner'
      and tenant_id = public.current_profile_tenant_id()
      and role = 'staff'
    )
  );

-- ---------------------------------------------------------------------------
-- leads
-- ---------------------------------------------------------------------------
create policy leads_select on public.leads
  for select to authenticated
  using (
    public.current_profile_role() = 'platform_admin'
    or tenant_id = public.current_profile_tenant_id()
  );

create policy leads_insert on public.leads
  for insert to authenticated
  with check (
    public.current_profile_role() = 'platform_admin'
    or tenant_id = public.current_profile_tenant_id()
  );

create policy leads_update on public.leads
  for update to authenticated
  using (
    public.current_profile_role() = 'platform_admin'
    or tenant_id = public.current_profile_tenant_id()
  )
  with check (
    public.current_profile_role() = 'platform_admin'
    or tenant_id = public.current_profile_tenant_id()
  );

-- No delete policy: leads are never hard-deleted by the app in the MVP.

-- ---------------------------------------------------------------------------
-- lead_events (append-only; insert + select only, enforced further by the
-- no-update/no-delete triggers in 0001_init_schema.sql)
-- ---------------------------------------------------------------------------
create policy lead_events_select on public.lead_events
  for select to authenticated
  using (
    public.current_profile_role() = 'platform_admin'
    or tenant_id = public.current_profile_tenant_id()
  );

create policy lead_events_insert on public.lead_events
  for insert to authenticated
  with check (
    public.current_profile_role() = 'platform_admin'
    or tenant_id = public.current_profile_tenant_id()
  );
