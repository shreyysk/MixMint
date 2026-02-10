-- Create admin_audit_logs table
create table if not exists admin_audit_logs (
    id uuid default uuid_generate_v4() primary key,
    admin_id uuid references auth.users(id) not null,
    action_type text not null, -- e.g., 'update_setting', 'ban_user', 'approve_dj'
    entity_type text not null, -- e.g., 'user', 'track', 'system'
    entity_id text,
    details jsonb, -- Stores changes or extra info
    ip_address text,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- RLS Policies
alter table admin_audit_logs enable row level security;

-- Only admins can view audit logs
drop policy if exists "Admins can view audit logs" on admin_audit_logs;
create policy "Admins can view audit logs"
    on admin_audit_logs
    for select
    using (
        exists (
            select 1 from profiles
            where profiles.id = auth.uid()
            and profiles.role = 'admin'
        )
    );

-- Only system/admins can insert (via API)
drop policy if exists "Admins can insert audit logs" on admin_audit_logs;
create policy "Admins can insert audit logs"
    on admin_audit_logs
    for insert
    with check (
        exists (
            select 1 from profiles
            where profiles.id = auth.uid()
            and profiles.role = 'admin'
        )
    );
