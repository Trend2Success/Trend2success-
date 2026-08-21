-- Lead Rescue AI: core schema
-- Tenants, user profiles/roles, leads, and an append-only AI/human action log.

create extension if not exists "pgcrypto";

-- ---------------------------------------------------------------------------
-- tenants
-- ---------------------------------------------------------------------------
create table public.tenants (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  -- Secret used to validate the X-Lead-Signature header on inbound lead
  -- webhooks for this tenant. Server-only; never returned to the browser
  -- outside the owning tenant's own settings view.
  webhook_signing_secret text not null default encode(gen_random_bytes(32), 'hex'),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

comment on table public.tenants is 'A single home-service business account. All tenant data is isolated by tenant_id.';

-- ---------------------------------------------------------------------------
-- profiles (one row per auth.users row; carries role + tenant membership)
-- ---------------------------------------------------------------------------
create table public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  -- Null only for platform_admin, who is not scoped to a single tenant.
  tenant_id uuid references public.tenants (id) on delete cascade,
  role text not null check (role in ('platform_admin', 'business_owner', 'staff')),
  full_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint profiles_tenant_required_unless_admin check (
    role = 'platform_admin' or tenant_id is not null
  )
);

comment on table public.profiles is 'App-level identity for an auth.users row: role and tenant membership.';

-- ---------------------------------------------------------------------------
-- leads
-- ---------------------------------------------------------------------------
create table public.leads (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  status text not null default 'new' check (
    status in ('new', 'contacted', 'replied', 'qualified', 'booked', 'human_review', 'lost', 'opted_out')
  ),
  source text not null check (source in ('missed_call', 'web_form', 'sms', 'manual')),
  -- De-dupes webhook retries from the same source system, per tenant.
  external_ref text,
  name text,
  phone text,
  email text,
  sms_consent boolean not null default false,
  sms_consent_at timestamptz,
  opted_out boolean not null default false,
  opted_out_at timestamptz,
  assigned_to uuid references public.profiles (id) on delete set null,
  first_response_due_at timestamptz,
  first_response_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint leads_external_ref_unique_per_tenant unique (tenant_id, external_ref)
);

comment on table public.leads is 'A missed call or web lead moving through the response pipeline.';
comment on column public.leads.first_response_due_at is 'created_at + 60s: the MVP success-metric deadline for a first response.';

create index leads_tenant_id_idx on public.leads (tenant_id);
create index leads_tenant_status_idx on public.leads (tenant_id, status);

-- ---------------------------------------------------------------------------
-- lead_events: append-only audit log for every AI and human action.
-- ---------------------------------------------------------------------------
create table public.lead_events (
  id uuid primary key default gen_random_uuid(),
  lead_id uuid not null references public.leads (id) on delete cascade,
  -- Denormalized from leads.tenant_id so RLS can scope this table directly
  -- without a join, and so the row remains attributable if a lead is ever
  -- removed from a tenant's active view.
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  actor_type text not null check (actor_type in ('system', 'ai', 'human')),
  -- Set only when actor_type = 'human'.
  actor_id uuid references public.profiles (id) on delete set null,
  event_type text not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

comment on table public.lead_events is 'Immutable log of every automated and human action taken on a lead. Required for review of all AI actions.';

create index lead_events_lead_id_idx on public.lead_events (lead_id, created_at);
create index lead_events_tenant_id_idx on public.lead_events (tenant_id);

-- Append-only: block updates and deletes outright, including for the table
-- owner, so the audit trail cannot be altered after the fact.
create function public.forbid_lead_events_mutation()
returns trigger
language plpgsql
as $$
begin
  raise exception 'lead_events is append-only: % is not allowed', tg_op;
end;
$$;

create trigger lead_events_no_update
  before update on public.lead_events
  for each row execute function public.forbid_lead_events_mutation();

create trigger lead_events_no_delete
  before delete on public.lead_events
  for each row execute function public.forbid_lead_events_mutation();

-- ---------------------------------------------------------------------------
-- updated_at maintenance
-- ---------------------------------------------------------------------------
create function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger tenants_set_updated_at
  before update on public.tenants
  for each row execute function public.set_updated_at();

create trigger profiles_set_updated_at
  before update on public.profiles
  for each row execute function public.set_updated_at();

create trigger leads_set_updated_at
  before update on public.leads
  for each row execute function public.set_updated_at();
