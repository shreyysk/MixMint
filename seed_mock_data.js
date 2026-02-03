require('dotenv').config({ path: '.env.local' });
const { createClient } = require('@supabase/supabase-js');

const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL,
    process.env.SUPABASE_SERVICE_ROLE_KEY
);

// Mock DJs data
const MOCK_DJS = [
    {
        dj_name: "DJ Shadow Test",
        slug: "dj-shadow-test",
        bio: "Electronic music producer specializing in downtempo beats. [TEST DATA]",
        genres: ["Electronic", "Downtempo", "Hip-Hop"],
        banner_url: "https://images.unsplash.com/photo-1571266028243-e4733b0f0bb1?q=80&w=1200&h=400&auto=format&fit=crop",
    },
    {
        dj_name: "Luna Beats Test",
        slug: "luna-beats-test",
        bio: "House and techno DJ with a passion for underground sounds. [TEST DATA]",
        genres: ["House", "Techno", "Deep House"],
        banner_url: "https://images.unsplash.com/photo-1598387993441-a364f854c3e1?q=80&w=1200&h=400&auto=format&fit=crop",
    },
    {
        dj_name: "Rhythm Master Test",
        slug: "rhythm-master-test",
        bio: "Drum & Bass specialist bringing high-energy sets. [TEST DATA]",
        genres: ["Drum & Bass", "Jungle", "Breakbeat"],
        banner_url: "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?q=80&w=1200&h=400&auto=format&fit=crop",
    },
    {
        dj_name: "Bass Frequency Test",
        slug: "bass-frequency-test",
        bio: "Dubstep and bass music producer. Heavy drops guaranteed. [TEST DATA]",
        genres: ["Dubstep", "Bass", "Trap"],
        banner_url: "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?q=80&w=1200&h=400&auto=format&fit=crop",
    },
    {
        dj_name: "Vinyl Soul Test",
        slug: "vinyl-soul-test",
        bio: "Classic soul and funk DJ spinning vinyl only. [TEST DATA]",
        genres: ["Soul", "Funk", "Disco"],
        banner_url: "https://images.unsplash.com/photo-1514320291840-2e0a9bf2a9ae?q=80&w=1200&h=400&auto=format&fit=crop",
    },
    {
        dj_name: "Cosmic Trance Test",
        slug: "cosmic-trance-test",
        bio: "Progressive trance and psytrance explorer. [TEST DATA]",
        genres: ["Trance", "Progressive", "Psytrance"],
        banner_url: "https://images.unsplash.com/photo-1506157786151-b8491531f063?q=80&w=1200&h=400&auto=format&fit=crop",
    },
];

// Mock Tracks data (will be linked to DJs after creation)
const MOCK_TRACKS = [
    { title: "Midnight Groove [TEST]", price: 49, description: "Deep house track perfect for late night sessions", youtube_url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ" },
    { title: "Sunrise Anthem [FREE TEST]", price: 0, description: "Free uplifting trance track", youtube_url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ" },
    { title: "Urban Jungle [TEST]", price: 79, description: "Fast-paced drum & bass", youtube_url: null },
    { title: "Bass Drop [TEST]", price: 99, description: "Heavy dubstep with massive drops", youtube_url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ" },
    { title: "Soulful Sunday [FREE TEST]", price: 0, description: "Free soul music for relaxing", youtube_url: null },
    { title: "Cosmic Journey [TEST]", price: 149, description: "Epic progressive trance", youtube_url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ" },
    { title: "Minimal Techno 001 [TEST]", price: 59, description: "Stripped down techno beats", youtube_url: null },
    { title: "Funk Revival [FREE TEST]", price: 0, description: "Free funky grooves", youtube_url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ" },
];

// Mock Album Packs data
const MOCK_ALBUMS = [
    { title: "Summer Sessions 2026 [TEST]", description: "Complete summer mix package with 10 tracks", price: 299, file_size: 157286400 },
    { title: "Underground Collection [TEST]", description: "Rare underground tracks compilation", price: 499, file_size: 209715200 },
    { title: "Best of House [TEST]", description: "Top house tracks from the year", price: 399, file_size: 188743680 },
    { title: "Bass Music Pack [FREE TEST]", description: "Free bass music starter pack", price: 0, file_size: 104857600 },
];

async function seedMockData() {
    console.log('🌱 Starting Mock Data Seed...\n');
    console.log('⚠️  This creates TEST DATA for UI/UX validation');
    console.log('⚠️  Run cleanup script after testing\n');

    try {
        // Step 1: Create test user profiles for DJs
        console.log('1️⃣  Creating DJ user profiles...');
        const djProfiles = [];

        for (const mockDJ of MOCK_DJS) {
            // Create a test user account
            const testEmail = `${mockDJ.slug}@test.mixmint.local`;
            const testPassword = 'TestPass123!';

            // Check if user already exists
            const { data: existingProfile } = await supabase
                .from('profiles')
                .select('id')
                .eq('full_name', mockDJ.dj_name)
                .single();

            let userId;

            if (existingProfile) {
                console.log(`   ⏭️  ${mockDJ.dj_name} already exists`);
                userId = existingProfile.id;
            } else {
                // Create auth user
                const { data: authData, error: authError } = await supabase.auth.admin.createUser({
                    email: testEmail,
                    password: testPassword,
                    email_confirm: true,
                });

                if (authError) {
                    console.error(`   ❌ Failed to create auth for ${mockDJ.dj_name}:`, authError.message);
                    continue;
                }

                userId = authData.user.id;

                // Create profile
                const { error: profileError } = await supabase
                    .from('profiles')
                    .insert({
                        id: userId,
                        full_name: mockDJ.dj_name,
                        role: 'dj',
                    });

                if (profileError) {
                    console.error(`   ❌ Failed to create profile for ${mockDJ.dj_name}:`, profileError.message);
                    continue;
                }

                console.log(`   ✅ Created user profile for ${mockDJ.dj_name}`);
            }

            // Check if DJ profile exists
            const { data: existingDJ } = await supabase
                .from('dj_profiles')
                .select('id')
                .eq('slug', mockDJ.slug)
                .single();

            if (existingDJ) {
                console.log(`   ⏭️  DJ profile ${mockDJ.dj_name} already exists`);
                djProfiles.push({ ...mockDJ, id: existingDJ.id, user_id: userId });
            } else {
                // Create DJ profile
                const { data: djData, error: djError } = await supabase
                    .from('dj_profiles')
                    .insert({
                        user_id: userId,
                        dj_name: mockDJ.dj_name,
                        slug: mockDJ.slug,
                        bio: mockDJ.bio,
                        genres: mockDJ.genres,
                        banner_url: mockDJ.banner_url,
                        status: 'approved',
                    })
                    .select()
                    .single();

                if (djError) {
                    console.error(`   ❌ Failed to create DJ profile for ${mockDJ.dj_name}:`, djError.message);
                    continue;
                }

                djProfiles.push({ ...mockDJ, id: djData.id, user_id: userId });
                console.log(`   ✅ Created DJ profile for ${mockDJ.dj_name}`);
            }
        }

        console.log(`\n   📊 Total DJs created/verified: ${djProfiles.length}\n`);

        // Step 2: Create tracks
        console.log('2️⃣  Creating tracks...');
        let tracksCreated = 0;

        for (let i = 0; i < MOCK_TRACKS.length; i++) {
            const track = MOCK_TRACKS[i];
            const dj = djProfiles[i % djProfiles.length]; // Distribute tracks across DJs

            // Check if track exists
            const { data: existingTrack } = await supabase
                .from('tracks')
                .select('id')
                .eq('title', track.title)
                .single();

            if (existingTrack) {
                console.log(`   ⏭️  ${track.title} already exists`);
                continue;
            }

            const { error } = await supabase
                .from('tracks')
                .insert({
                    dj_id: dj.id,
                    title: track.title,
                    description: track.description,
                    price: track.price,
                    youtube_url: track.youtube_url,
                    file_key: `tracks/test_${Date.now()}_${i}.mp3`,
                    status: 'active',
                });

            if (error) {
                console.error(`   ❌ Failed to create ${track.title}:`, error.message);
            } else {
                tracksCreated++;
                const priceLabel = track.price === 0 ? 'FREE' : `₹${track.price}`;
                console.log(`   ✅ Created: ${track.title} (${priceLabel}) by ${dj.dj_name}`);
            }
        }

        console.log(`\n   📊 Total tracks created: ${tracksCreated}\n`);

        // Step 3: Create album packs
        console.log('3️⃣  Creating album packs...');
        let albumsCreated = 0;

        for (let i = 0; i < MOCK_ALBUMS.length; i++) {
            const album = MOCK_ALBUMS[i];
            const dj = djProfiles[i % djProfiles.length];

            // Check if album exists
            const { data: existingAlbum } = await supabase
                .from('album_packs')
                .select('id')
                .eq('title', album.title)
                .single();

            if (existingAlbum) {
                console.log(`   ⏭️  ${album.title} already exists`);
                continue;
            }

            const { error } = await supabase
                .from('album_packs')
                .insert({
                    dj_id: dj.user_id, // Note: album_packs uses profiles.id
                    dj_profile_id: dj.id, // New standardized FK
                    title: album.title,
                    description: album.description,
                    price: album.price,
                    file_key: `albums/test_${Date.now()}_${i}.zip`,
                    file_size: album.file_size,
                });

            if (error) {
                console.error(`   ❌ Failed to create ${album.title}:`, error.message);
            } else {
                albumsCreated++;
                const priceLabel = album.price === 0 ? 'FREE' : `₹${album.price}`;
                console.log(`   ✅ Created: ${album.title} (${priceLabel}) by ${dj.dj_name}`);
            }
        }

        console.log(`\n   📊 Total albums created: ${albumsCreated}\n`);

        // Summary
        console.log('═══════════════════════════════════════');
        console.log('✅ MOCK DATA SEED COMPLETE\n');
        console.log('Summary:');
        console.log(`   - ${djProfiles.length} DJs (approved)`);
        console.log(`   - ${tracksCreated} Tracks (mix of paid & free)`);
        console.log(`   - ${albumsCreated} Album Packs`);
        console.log('\n📋 Test Credentials:');
        djProfiles.forEach(dj => {
            console.log(`   ${dj.dj_name}: ${dj.slug}@test.mixmint.local / TestPass123!`);
        });
        console.log('\n⚠️  To remove this data, run: node cleanup_mock_data.js');
        console.log('═══════════════════════════════════════\n');

    } catch (err) {
        console.error('❌ Seed failed:', err);
        process.exit(1);
    }
}

seedMockData();
