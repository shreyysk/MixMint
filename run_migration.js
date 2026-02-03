require('dotenv').config({ path: '.env.local' });
const { createClient } = require('@supabase/supabase-js');
const fs = require('fs');

const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL,
    process.env.SUPABASE_SERVICE_ROLE_KEY
);

async function runMigration() {
    console.log('🚀 Starting Album Packs Schema Migration...\n');

    try {
        // Step 1: Check current state
        console.log('📊 Checking current album_packs records...');
        const { data: albums, error: countError } = await supabase
            .from('album_packs')
            .select('id, title, dj_id')
            .limit(5);

        if (countError) throw countError;
        
        console.log(`Found ${albums?.length || 0} album packs`);
        if (albums && albums.length > 0) {
            console.log('Sample:', albums[0]);
        }

        // Step 2: Execute migration SQL
        console.log('\n⚠️  MIGRATION SQL:');
        console.log('──────────────────────────────────────');
        
        const sql = fs.readFileSync('./migrations/001_album_packs_consistency.sql', 'utf8');
        
        // Extract only the executable statements (skip comments)
        const statements = sql
            .split(';')
            .map(s => s.trim())
            .filter(s => s && !s.startsWith('--') && s.length > 10);

        console.log(`Found ${statements.length} SQL statements to execute\n`);

        // Execute each statement
        for (let i = 0; i < statements.length; i++) {
            const statement = statements[i];
            if (statement.includes('ALTER TABLE') || statement.includes('UPDATE') || statement.includes('CREATE INDEX')) {
                console.log(`Executing statement ${i + 1}/${statements.length}...`);
                console.log(statement.substring(0, 80) + '...\n');
                
                // Note: Supabase JS client doesn't support raw SQL execution
                // This needs to be run via Supabase SQL Editor or psql
                console.log('⚠️  This statement must be executed via Supabase SQL Editor');
            }
        }

        console.log('\n✅ Migration script prepared.');
        console.log('\n📋 NEXT STEPS:');
        console.log('1. Open Supabase Dashboard → SQL Editor');
        console.log('2. Copy contents of /app/migrations/001_album_packs_consistency.sql');
        console.log('3. Execute the migration');
        console.log('4. Run verification queries at the bottom of the file');
        console.log('5. Confirm all album_packs have dj_profile_id populated');

    } catch (err) {
        console.error('❌ Migration check failed:', err.message);
        process.exit(1);
    }
}

runMigration();
