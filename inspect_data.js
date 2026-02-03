const { createClient } = require('@supabase/supabase-js');

const supabase = createClient(
    'https://ilbijjinhlmobnzpuojl.supabase.co',
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlsYmlqamluaGxtb2JuenB1b2psIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTc3NzY2OSwiZXhwIjoyMDg1MzUzNjY5fQ.tGBn4Li4iyjzx_0mviXAUu4IYG8zZOEThC6XVkSv7o0'
);

async function inspectData() {
    console.log('=== PROFILES ===');
    const { data: profiles } = await supabase
        .from('profiles')
        .select('*')
        .limit(5);
    console.log(JSON.stringify(profiles, null, 2));

    console.log('\n=== DJ PROFILES ===');
    const { data: djs } = await supabase
        .from('dj_profiles')
        .select('*')
        .limit(5);
    console.log(JSON.stringify(djs, null, 2));

    console.log('\n=== TRACKS ===');
    const { data: tracks } = await supabase
        .from('tracks')
        .select('*')
        .limit(5);
    console.log(JSON.stringify(tracks, null, 2));

    console.log('\n=== ALBUMS ===');
    const { data: albums } = await supabase
        .from('album_packs')
        .select('*')
        .limit(5);
    console.log(JSON.stringify(albums, null, 2));
}

inspectData();
