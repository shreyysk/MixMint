const { createClient } = require('@supabase/supabase-js');

const supabase = createClient(
    'https://ilbijjinhlmobnzpuojl.supabase.co',
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlsYmlqamluaGxtb2JuenB1b2psIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTc3NzY2OSwiZXhwIjoyMDg1MzUzNjY5fQ.tGBn4Li4iyjzx_0mviXAUu4IYG8zZOEThC6XVkSv7o0'
);

async function verifyBatch3() {
    console.log('🔍 BATCH 3 - Final Verification\n');
    console.log('═══════════════════════════════════════\n');

    let allPassed = true;

    // 1. Check schema migration
    console.log('1️⃣  Checking Schema Migration...');
    try {
        const { data: albums, error } = await supabase
            .from('album_packs')
            .select('id, dj_id, dj_profile_id')
            .limit(5);

        if (error) throw error;

        const nullCount = albums?.filter(a => !a.dj_profile_id).length || 0;
        
        if (nullCount === 0) {
            console.log('   ✅ album_packs.dj_profile_id populated');
        } else {
            console.log(`   ❌ ${nullCount} records missing dj_profile_id`);
            allPassed = false;
        }
    } catch (err) {
        console.log('   ❌ Schema migration not complete:', err.message);
        allPassed = false;
    }

    // 2. Check system_settings table
    console.log('\n2️⃣  Checking System Settings...');
    try {
        const { data: settings, error } = await supabase
            .from('system_settings')
            .select('key, value');

        if (error) throw error;

        const requiredKeys = ['payment_gateway', 'minimum_pricing', 'feature_flags'];
        const existingKeys = settings?.map(s => s.key) || [];

        requiredKeys.forEach(key => {
            if (existingKeys.includes(key)) {
                console.log(`   ✅ ${key} configured`);
            } else {
                console.log(`   ❌ ${key} missing`);
                allPassed = false;
            }
        });

        // Show payment gateway config
        const paymentGateway = settings?.find(s => s.key === 'payment_gateway');
        if (paymentGateway) {
            console.log(`   📊 Active Gateway: ${paymentGateway.value.provider} (${paymentGateway.value.mode})`);
        }
    } catch (err) {
        console.log('   ❌ system_settings table error:', err.message);
        allPassed = false;
    }

    // 3. Check environment variables
    console.log('\n3️⃣  Checking Environment Variables...');
    const requiredEnv = [
        'NEXT_PUBLIC_RAZORPAY_KEY_ID',
        'RAZORPAY_KEY_SECRET',
        'RESEND_API_KEY',
    ];

    requiredEnv.forEach(key => {
        if (process.env[key]) {
            console.log(`   ✅ ${key} set`);
        } else {
            console.log(`   ❌ ${key} missing`);
            allPassed = false;
        }
    });

    // 4. Check API routes exist
    console.log('\n4️⃣  Checking API Routes...');
    const apiRoutes = [
        '/api/payment/create',
        '/api/payment/verify',
    ];

    console.log('   ℹ️  API routes should be tested manually via HTTP requests');
    apiRoutes.forEach(route => {
        console.log(`   📁 ${route}`);
    });

    // 5. Check file structure
    console.log('\n5️⃣  Checking File Structure...');
    const fs = require('fs');
    const requiredFiles = [
        '/app/src/app/lib/payments/index.ts',
        '/app/src/app/lib/payments/razorpay.ts',
        '/app/src/app/lib/payments/phonepe.ts',
        '/app/src/app/lib/email.ts',
        '/app/src/app/lib/razorpayCheckout.ts',
        '/app/src/app/admin/settings/page.tsx',
    ];

    requiredFiles.forEach(file => {
        if (fs.existsSync(file)) {
            console.log(`   ✅ ${file.replace('/app/', '')}`);
        } else {
            console.log(`   ❌ ${file} missing`);
            allPassed = false;
        }
    });

    // Final Result
    console.log('\n═══════════════════════════════════════');
    if (allPassed) {
        console.log('✅ BATCH 3 VERIFICATION PASSED');
        console.log('\nNext Steps:');
        console.log('1. Start dev server: yarn dev');
        console.log('2. Test payment flow manually');
        console.log('3. Review /app/TESTING_CHECKLIST.md');
    } else {
        console.log('❌ BATCH 3 VERIFICATION FAILED');
        console.log('\nSome components are missing or misconfigured.');
        console.log('Review the errors above and fix before proceeding.');
    }
    console.log('═══════════════════════════════════════\n');

    process.exit(allPassed ? 0 : 1);
}

verifyBatch3();
