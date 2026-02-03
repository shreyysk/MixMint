require('dotenv').config({ path: '.env.local' });
const { createClient } = require('@supabase/supabase-js');

const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
);

async function listRoles() {
    const { data, error } = await supabase
        .from('profiles')
        .select('role')
        .limit(10);

    if (error) {
        console.error('Error listing roles:', error);
        process.exit(1);
    }

    console.log('Roles found:', data);
}

listRoles();
