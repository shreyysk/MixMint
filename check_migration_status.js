const { createClient } = require('@supabase/supabase-js');

const supabase = createClient(
    'https://ilbijjinhlmobnzpuojl.supabase.co',
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlsYmlqamluaGxtb2JuenB1b2psIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTc3NzY2OSwiZXhwIjoyMDg1MzUzNjY5fQ.tGBn4Li4iyjzx_0mviXAUu4IYG8zZOEThC6XVkSv7o0'
);

async function checkMigration() {
    console.log('🔍 Checking Migration Status...\n');

    try {
        // Check if dj_profile_id column exists and is populated
        const { data: albums, error } = await supabase
            .from('album_packs')
            .select('id, title, dj_id, dj_profile_id')
            .limit(10);

        if (error) {
            if (error.message.includes('column "dj_profile_id" does not exist')) {
                console.log('❌ Migration NOT executed yet.');
                console.log('   Column dj_profile_id does not exist.\n');
                console.log('📋 ACTION REQUIRED:');
                console.log('   1. Open Supabase SQL Editor');
                console.log('   2. Execute migration SQL');
                console.log('   3. Run this script again');
                return false;
            }
            throw error;
        }

        // Check if all records have dj_profile_id populated
        const nullCount = albums?.filter(a => !a.dj_profile_id).length || 0;
        
        if (nullCount > 0) {
            console.log(`⚠️  Migration partially complete: ${nullCount} records missing dj_profile_id`);
            return false;
        }

        console.log('✅ Migration SUCCESSFUL!\n');
        console.log(`📊 Verified ${albums?.length || 0} album records:`);
        
        albums?.forEach(album => {
            console.log(`   - ${album.title}`);
            console.log(`     Old FK (dj_id): ${album.dj_id}`);
            console.log(`     New FK (dj_profile_id): ${album.dj_profile_id}`);
        });

        console.log('\n✅ Schema migration complete. Proceeding to next step...');
        return true;

    } catch (err) {
        console.error('❌ Verification failed:', err.message);
        return false;
    }
}

checkMigration().then(success => {
    process.exit(success ? 0 : 1);
});
