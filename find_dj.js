require('dotenv').config({ path: '.env.local' });
const { createClient } = require('@supabase/supabase-js');

const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
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
