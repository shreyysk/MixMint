const { createClient } = require('@supabase/supabase-js');

const supabase = createClient(
    'https://ilbijjinhlmobnzpuojl.supabase.co',
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlsYmlqamluaGxtb2JuenB1b2psIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTc3NzY2OSwiZXhwIjoyMDg1MzUzNjY5fQ.tGBn4Li4iyjzx_0mviXAUu4IYG8zZOEThC6XVkSv7o0'
);

async function checkSettings() {
    const { data, error } = await supabase
        .from('system_settings')
        .select('*');
    
    if (error) {
        console.error('Error:', error);
        return;
    }
    
    console.log('✅ System Settings:');
    data?.forEach(setting => {
        console.log(`\n${setting.key}:`);
        console.log(JSON.stringify(setting.value, null, 2));
    });
}

checkSettings();
