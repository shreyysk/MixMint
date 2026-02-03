require('dotenv').config({ path: '.env.local' });
const { createClient } = require('@supabase/supabase-js');

const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL,
    process.env.SUPABASE_SERVICE_ROLE_KEY
);

async function setupTestDJ() {
    const email = `test_dj_${Date.now()}@mixmint.site`;
    const password = 'TestPassword123!';

    // 1. Create User
    const { data: userData, error: userError } = await supabase.auth.admin.createUser({
        email,
        password,
        email_confirm: true,
    });

    if (userError) {
        console.error('Error creating user:', userError);
        process.exit(1);
    }

    const userId = userData.user.id;
    console.log('Created user:', userId);

    // 2. Create Profile
    const { error: profileError } = await supabase
        .from('profiles')
        .insert({
            id: userId,
            role: 'dj',
            username: `testdj_${Date.now()}`
        });

    if (profileError) {
        console.error('Error creating profile:', profileError);
        process.exit(1);
    }

    console.log('Created profile for DJ:', userId);
    console.log('TEST_DJ_EMAIL:', email);
    console.log('TEST_DJ_PASSWORD:', password);
    console.log('TEST_DJ_ID:', userId);
}

setupTestDJ();
