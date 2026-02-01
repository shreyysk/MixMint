const { createClient } = require('@supabase/supabase-js');

const supabase = createClient(
    'https://ilbijjinhlmobnzpuojl.supabase.co',
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlsYmlqamluaGxtb2JuenB1b2psIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTc3NzY2OSwiZXhwIjoyMDg1MzUzNjY5fQ.tGBn4Li4iyjzx_0mviXAUu4IYG8zZOEThC6XVkSv7o0'
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
