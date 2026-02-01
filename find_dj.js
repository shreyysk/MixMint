const { createClient } = require('@supabase/supabase-js');

const supabase = createClient(
    'https://ilbijjinhlmobnzpuojl.supabase.co',
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlsYmlqamluaGxtb2JuenB1b2psIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk3Nzc2NjksImV4cCI6MjA4NTM1MzY2OX0.nLGc0JRDauvNDu-Y_xKAChOyQOs0l4EaslJeDoh-8xU'
);

async function findDJ() {
    const { data, error } = await supabase
        .from('profiles')
        .select('id')
        .eq('role', 'dj')
        .limit(1)
        .single();

    if (error) {
        console.error('Error finding DJ:', error);
        process.exit(1);
    }

    console.log('Found DJ:', data);
}

findDJ();
