require('dotenv').config({ path: '.env.local' });
const { createClient } = require('@supabase/supabase-js');

const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL,
    process.env.SUPABASE_SERVICE_ROLE_KEY
);

async function cleanupMockData() {
    console.log('🧹 Starting Mock Data Cleanup...\n');
    console.log('⚠️  This will DELETE all TEST DATA');
    console.log('⚠️  Press Ctrl+C within 5 seconds to cancel\n');

    // Wait 5 seconds
    await new Promise(resolve => setTimeout(resolve, 5000));

    try {
        // Step 1: Delete tracks with [TEST] in title
        console.log('1️⃣  Deleting test tracks...');
        const { data: tracks, error: tracksError } = await supabase
            .from('tracks')
            .delete()
            .ilike('title', '%[TEST]%')
            .select();

        if (tracksError) {
            console.error('   ❌ Error deleting tracks:', tracksError.message);
        } else {
            console.log(`   ✅ Deleted ${tracks?.length || 0} test tracks`);
        }

        // Step 2: Delete albums with [TEST] in title
        console.log('\n2️⃣  Deleting test albums...');
        const { data: albums, error: albumsError } = await supabase
            .from('album_packs')
            .delete()
            .ilike('title', '%[TEST]%')
            .select();

        if (albumsError) {
            console.error('   ❌ Error deleting albums:', albumsError.message);
        } else {
            console.log(`   ✅ Deleted ${albums?.length || 0} test albums`);
        }

        // Step 3: Delete DJ profiles with [TEST DATA] in bio
        console.log('\n3️⃣  Deleting test DJ profiles...');
        const { data: djs, error: djsError } = await supabase
            .from('dj_profiles')
            .delete()
            .ilike('bio', '%[TEST DATA]%')
            .select();

        if (djsError) {
            console.error('   ❌ Error deleting DJ profiles:', djsError.message);
        } else {
            console.log(`   ✅ Deleted ${djs?.length || 0} test DJ profiles`);
        }

        // Step 4: Delete user profiles
        console.log('\n4️⃣  Deleting test user accounts...');
        const { data: profiles, error: profilesError } = await supabase
            .from('profiles')
            .delete()
            .ilike('full_name', '%Test')
            .select();

        if (profilesError) {
            console.error('   ❌ Error deleting profiles:', profilesError.message);
        } else {
            console.log(`   ✅ Deleted ${profiles?.length || 0} test user profiles`);

            // Delete auth users
            if (profiles && profiles.length > 0) {
                for (const profile of profiles) {
                    const { error: authError } = await supabase.auth.admin.deleteUser(profile.id);
                    if (authError) {
                        console.error(`   ⚠️  Failed to delete auth user ${profile.id}:`, authError.message);
                    }
                }
                console.log(`   ✅ Deleted ${profiles.length} auth users`);
            }
        }

        console.log('\n═══════════════════════════════════════');
        console.log('✅ MOCK DATA CLEANUP COMPLETE');
        console.log('═══════════════════════════════════════\n');

    } catch (err) {
        console.error('❌ Cleanup failed:', err);
        process.exit(1);
    }
}

cleanupMockData();
