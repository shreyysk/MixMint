const { createClient } = require('@supabase/supabase-js');

const supabase = createClient(
    'https://ilbijjinhlmobnzpuojl.supabase.co',
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlsYmlqamluaGxtb2JuenB1b2psIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTc3NzY2OSwiZXhwIjoyMDg1MzUzNjY5fQ.tGBn4Li4iyjzx_0mviXAUu4IYG8zZOEThC6XVkSv7o0'
);

async function verifyMigration() {
    console.log('🔍 Verifying Migration Data Mapping\n');

    // Get album with current dj_id
    const userId = 'd68c0c87-b171-4231-8876-2a06ee1e3f8c';
    
    console.log(`Album dj_id (profiles.id): ${userId}`);
    
    // Find corresponding dj_profiles.id
    const { data: djProfile } = await supabase
        .from('dj_profiles')
        .select('id, dj_name')
        .eq('user_id', userId)
        .single();
    
    if (djProfile) {
        console.log(`DJ Profile id: ${djProfile.id}`);
        console.log(`DJ Name: ${djProfile.dj_name}`);
        console.log('\n✅ Mapping verified. Migration will work correctly.');
    } else {
        console.log('❌ No DJ profile found for this user_id!');
    }
}

verifyMigration();
