# Lead Rescue AI

Converts missed calls and new web leads into booked appointments for local
home-service businesses. First response to a lead must go out in under 60
seconds and end in one of: booked, handed to staff, marked lost, or opted out.

## Status: vertical slice 1 — tenant foundation + lead intake

This slice implements the foundation everything else depends on:

- Multi-tenant schema (`tenants`, `profiles` with roles, `leads`, an
  append-only `lead_events` audit log) with Postgres RLS enforcing tenant
  isolation on every table.
- A signed webhook endpoint (`POST /api/webhooks/leads/[tenantId]`) that
  turns a missed call or web form submission into a `new` lead, with
  mandatory, explicit SMS consent capture and idempotent retries.
- A role-gated `/leads` dashboard that lists a tenant's leads (or, for
  `platform_admin`, all tenants').

Not in this slice: the AI reply engine, human takeover UI, SMS sending,
staff invites UI, and reporting. Those are separate vertical slices.

## Setup

```bash
npm install
cp .env.example .env.local   # fill in your Supabase project's values
```

Apply the migrations in `supabase/migrations/` to your Supabase project, in
order, via the Supabase SQL editor or the Supabase CLI:

```bash
supabase db push
```

Then run the app:

```bash
npm run dev
```

## Provisioning a tenant and its first users

There's no self-serve signup in this slice — accounts are provisioned by an
admin, since role and tenant assignment must be deliberate. From the
Supabase SQL editor (service role), after creating an `auth.users` row for
the owner via Supabase Auth:

```sql
insert into tenants (name) values ('Acme HVAC') returning id;
-- use the returned id below
insert into profiles (id, tenant_id, role, full_name)
  values ('<auth-user-uuid>', '<tenant-id>', 'business_owner', 'Jane Doe');
```

Grab that tenant's `webhook_signing_secret` from the `tenants` table to
configure the lead source's webhook.

## Sending a test lead

```bash
BODY='{"source":"web_form","name":"Jane Homeowner","phone":"+15551234567","sms_consent":true}'
SIG=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "<tenant-webhook-secret>" | sed 's/^.* //')
curl -X POST "http://localhost:3000/api/webhooks/leads/<tenant-id>" \
  -H "Content-Type: application/json" \
  -H "X-Lead-Signature: $SIG" \
  -d "$BODY"
```

## Tests

```bash
npm run typecheck
npm run lint
npm test
```

`npm test` covers the pure logic: webhook signature verification (valid,
forged, tampered, missing, malformed) and the lead state machine (every
transition the MVP's core states allow and forbid).

### RLS verification

This sandbox has no running Docker daemon, so the RLS policies in
`supabase/migrations/0002_rls_policies.sql` were written against Supabase's
documented patterns but not exercised against a live Postgres instance.
Before trusting them in production, verify against a real (or `supabase
start` local) project:

1. Create two tenants, each with a `business_owner` and a `staff` profile.
2. Sign in as tenant A's owner; confirm `select * from leads` returns only
   tenant A's rows, and that inserting a lead with tenant B's `tenant_id`
   is rejected.
3. Confirm a `staff` row cannot promote itself to `business_owner` or move
   itself to another tenant (the `profiles_update` policy's `with check`
   should reject it).
4. Confirm `platform_admin` can read across tenants.
5. Confirm an `update` or `delete` against `lead_events` fails outright
   (the append-only triggers apply even to the table owner).

## Non-negotiables this slice upholds

- **Tenant isolation**: enforced by RLS on every tenant-scoped table, not
  just in application code.
- **SMS consent**: `sms_consent` is a required, explicit boolean on every
  inbound lead — never defaulted to true.
- **Audit log**: every lead gets a `lead_events` row on creation; the table
  is append-only at the database level.
- **Webhook signatures**: every inbound webhook must carry a valid
  HMAC-SHA256 signature, verified with a constant-time comparison, checked
  against that specific tenant's own secret.
- **No API keys in the browser**: `SUPABASE_SERVICE_ROLE_KEY` and
  `LEAD_WEBHOOK_SIGNING_SECRET` are read only in server-side code
  (`src/lib/supabase/server.ts`, the webhook route handler); the browser
  client only ever uses the public anon key, which is safe precisely
  because RLS — not secrecy — is what protects the data.
