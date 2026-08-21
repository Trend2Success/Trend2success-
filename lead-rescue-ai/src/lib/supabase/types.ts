// Hand-written to match supabase/migrations/*.sql, following the shape
// `supabase gen types typescript` produces. Once the project is linked to a
// real Supabase instance, regenerate this with:
//   supabase gen types typescript --linked > src/lib/supabase/types.ts
// and delete this comment.

export type LeadStatus =
  | "new"
  | "contacted"
  | "replied"
  | "qualified"
  | "booked"
  | "human_review"
  | "lost"
  | "opted_out";

export type LeadSource = "missed_call" | "web_form" | "sms" | "manual";

export type ProfileRole = "platform_admin" | "business_owner" | "staff";

export type LeadEventActorType = "system" | "ai" | "human";

export interface Database {
  __InternalSupabase: {
    PostgrestVersion: "13";
  };
  public: {
    Tables: {
      tenants: {
        Row: {
          id: string;
          name: string;
          webhook_signing_secret: string;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: string;
          name: string;
          webhook_signing_secret?: string;
          created_at?: string;
          updated_at?: string;
        };
        Update: Partial<{
          id: string;
          name: string;
          webhook_signing_secret: string;
          created_at: string;
          updated_at: string;
        }>;
        Relationships: [];
      };
      profiles: {
        Row: {
          id: string;
          tenant_id: string | null;
          role: ProfileRole;
          full_name: string | null;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id: string;
          tenant_id?: string | null;
          role: ProfileRole;
          full_name?: string | null;
          created_at?: string;
          updated_at?: string;
        };
        Update: Partial<{
          id: string;
          tenant_id: string | null;
          role: ProfileRole;
          full_name: string | null;
          created_at: string;
          updated_at: string;
        }>;
        Relationships: [
          {
            foreignKeyName: "profiles_tenant_id_fkey";
            columns: ["tenant_id"];
            isOneToOne: false;
            referencedRelation: "tenants";
            referencedColumns: ["id"];
          },
        ];
      };
      leads: {
        Row: {
          id: string;
          tenant_id: string;
          status: LeadStatus;
          source: LeadSource;
          external_ref: string | null;
          name: string | null;
          phone: string | null;
          email: string | null;
          sms_consent: boolean;
          sms_consent_at: string | null;
          opted_out: boolean;
          opted_out_at: string | null;
          assigned_to: string | null;
          first_response_due_at: string | null;
          first_response_at: string | null;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: string;
          tenant_id: string;
          status?: LeadStatus;
          source: LeadSource;
          external_ref?: string | null;
          name?: string | null;
          phone?: string | null;
          email?: string | null;
          sms_consent?: boolean;
          sms_consent_at?: string | null;
          opted_out?: boolean;
          opted_out_at?: string | null;
          assigned_to?: string | null;
          first_response_due_at?: string | null;
          first_response_at?: string | null;
          created_at?: string;
          updated_at?: string;
        };
        Update: Partial<{
          id: string;
          tenant_id: string;
          status: LeadStatus;
          source: LeadSource;
          external_ref: string | null;
          name: string | null;
          phone: string | null;
          email: string | null;
          sms_consent: boolean;
          sms_consent_at: string | null;
          opted_out: boolean;
          opted_out_at: string | null;
          assigned_to: string | null;
          first_response_due_at: string | null;
          first_response_at: string | null;
          created_at: string;
          updated_at: string;
        }>;
        Relationships: [
          {
            foreignKeyName: "leads_tenant_id_fkey";
            columns: ["tenant_id"];
            isOneToOne: false;
            referencedRelation: "tenants";
            referencedColumns: ["id"];
          },
          {
            foreignKeyName: "leads_assigned_to_fkey";
            columns: ["assigned_to"];
            isOneToOne: false;
            referencedRelation: "profiles";
            referencedColumns: ["id"];
          },
        ];
      };
      lead_events: {
        Row: {
          id: string;
          lead_id: string;
          tenant_id: string;
          actor_type: LeadEventActorType;
          actor_id: string | null;
          event_type: string;
          payload: Record<string, unknown>;
          created_at: string;
        };
        Insert: {
          id?: string;
          lead_id: string;
          tenant_id: string;
          actor_type: LeadEventActorType;
          actor_id?: string | null;
          event_type: string;
          payload?: Record<string, unknown>;
          created_at?: string;
        };
        // Append-only: the schema forbids UPDATE outright (see
        // forbid_lead_events_mutation() in 0001_init_schema.sql).
        Update: Record<string, never>;
        Relationships: [
          {
            foreignKeyName: "lead_events_lead_id_fkey";
            columns: ["lead_id"];
            isOneToOne: false;
            referencedRelation: "leads";
            referencedColumns: ["id"];
          },
          {
            foreignKeyName: "lead_events_tenant_id_fkey";
            columns: ["tenant_id"];
            isOneToOne: false;
            referencedRelation: "tenants";
            referencedColumns: ["id"];
          },
          {
            foreignKeyName: "lead_events_actor_id_fkey";
            columns: ["actor_id"];
            isOneToOne: false;
            referencedRelation: "profiles";
            referencedColumns: ["id"];
          },
        ];
      };
    };
    Views: Record<string, never>;
    Functions: Record<string, never>;
    Enums: Record<string, never>;
    CompositeTypes: Record<string, never>;
  };
}
