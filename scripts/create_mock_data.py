
import os
import django
import random
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.accounts.models import User, Profile, DJProfile, DJAnnouncement, AmbassadorCode
from apps.tracks.models import Track
from apps.albums.models import AlbumPack, AlbumTrack
from apps.commerce.models import Purchase, Bundle, BundleTrack, DJWallet, LedgerEntry, DJApplicationFee

def create_mock_data():
    print("🚀 Starting mock data generation...")

    # 1. Create DJs
    djs_data = [
        {"name": "Alpha Beats", "genre": ["Techno", "House"], "loc": "Berlin", "pro": True},
        {"name": "DJ Synthia", "genre": ["Synthwave", "Retrowave"], "loc": "Miami", "pro": False},
        {"name": "Bass Master", "genre": ["Dubstep", "Bass"], "loc": "London", "pro": True},
        {"name": "Chill Wave", "genre": ["Lo-fi", "Chill"], "loc": "Kyoto", "pro": False},
    ]

    djs = []
    for data in djs_data:
        email = f"{data['name'].lower().replace(' ', '')}@example.com"
        user, created = User.objects.get_or_create(email=email)
        if created:
            user.set_password("Sk@110503")
            user.save()
        
        profile, _ = Profile.objects.get_or_create(
            user=user,
            defaults={
                'role': 'dj',
                'full_name': data['name'],
                'is_pro_dj': data['pro'],
                'storage_quota_mb': 20480 if data['pro'] else 3072
            }
        )
        # Ensure role is always dj
        if profile.role != 'dj':
            profile.role = 'dj'
            profile.save()
        
        dj_profile, _ = DJProfile.objects.get_or_create(
            profile=profile,
            defaults={
                'dj_name': data['name'],
                'bio': f"This is the official profile of {data['name']}. Dropping heat since 2024.",
                'genres': data['genre'],
                'location': data['loc'],
                'status': 'approved',
                'is_onboarding_complete': True
            }
        )
        djs.append(dj_profile)
        
        # Create Wallet
        DJWallet.objects.get_or_create(dj=dj_profile)
        
        # Create Ambassador Code
        AmbassadorCode.objects.get_or_create(dj=dj_profile, defaults={'code': data['name'].upper()[:4] + str(random.randint(10, 99))})

    # 2. Create Listeners
    listeners = []
    for i in range(1, 6):
        email = f"listener{i}@example.com"
        user, created = User.objects.get_or_create(email=email)
        if created:
            user.set_password("Sk@110503")
            user.save()
        
        profile, _ = Profile.objects.get_or_create(
            user=user,
            defaults={'role': 'user', 'full_name': f"Listener {i}"}
        )
        listeners.append(profile)

    # 3. Create Tracks
    genres = ["Techno", "House", "Trance", "Dubstep", "Lo-fi", "Disco"]
    tracks = []
    for dj in djs:
        for i in range(1, 10):
            track_title = f"{dj.dj_name} - {random.choice(['Vibe', 'Flow', 'Beat', 'Pulse', 'Wave', 'Echo', 'Sync', 'Glitch'])} {i}"
            price = random.choice([Decimal("0.00"), Decimal("19.00"), Decimal("29.00"), Decimal("49.00"), Decimal("99.00")])
            
            track, created = Track.objects.get_or_create(
                dj=dj,
                title=track_title,
                defaults={
                    'price': price,
                    'genre': random.choice(genres),
                    'preview_type': 'youtube',
                    'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                    'bpm': random.randint(120, 145),
                    'year': 2024,
                    'file_format': random.choice(['wav', 'mp3', 'aiff']),
                    'file_key': f"tracks/{dj.slug}/{track_title.lower().replace(' ', '_')}.wav"
                }
            )
            tracks.append(track)

    # 3.5 Create Albums
    albums = []
    for dj in djs:
        for i in range(1, 3):
            album_title = f"{dj.dj_name} - {random.choice(['Anthology', 'Chronicles', 'Vision', 'Rebirth'])} Vol. {i}"
            album, created = AlbumPack.objects.get_or_create(
                dj=dj,
                title=album_title,
                defaults={
                    'price': Decimal("149.00") if i == 1 else Decimal("199.00"),
                    'description': f"A premium collection of secret tracks by {dj.dj_name}.",
                    'preview_type': 'youtube',
                    'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                    'processing_status': 'completed',
                    'track_count': 5,
                    'file_key': f"albums/{dj.slug}/{album_title.lower().replace(' ', '_')}.zip"
                }
            )
            albums.append(album)
            
            for j in range(1, 6):
                AlbumTrack.objects.get_or_create(
                    album=album,
                    track_order=j,
                    defaults={'title': f"Album Track {j}", 'format': 'mp3'}
                )

    # 4. Create Sales (History)
    print("💸 Generating sales history for Tracks, Albums, and Bundles...")
    now = timezone.now()
    
    # Track Sales
    for _ in range(80):
        listener = random.choice(listeners)
        track = random.choice(tracks)
        days_ago = random.randint(0, 90)
        sale_date = now - timedelta(days=days_ago)
        
        if track.price > 0:
            commission = track.price * Decimal("0.15")
            dj_revenue = track.price - commission
            
            Purchase.objects.create(
                user=listener, seller=track.dj, content_id=track.id, content_type='track',
                original_price=track.price, price_paid=track.price, commission=commission,
                dj_revenue=dj_revenue, dj_earnings=dj_revenue, status='paid',
                paid_at=sale_date, created_at=sale_date
            )
            
            wallet = DJWallet.objects.get(dj=track.dj)
            wallet.total_earnings = Decimal(str(wallet.total_earnings)) + dj_revenue
            wallet.available_for_payout = Decimal(str(wallet.available_for_payout)) + dj_revenue
            wallet.save()
            
            track.dj.total_revenue = Decimal(str(track.dj.total_revenue)) + dj_revenue
            track.dj.save()
            track.download_count += 1
            track.save()

    # Album Sales
    for _ in range(20):
        listener = random.choice(listeners)
        album = random.choice(albums)
        days_ago = random.randint(0, 90)
        sale_date = now - timedelta(days=days_ago)
        
        commission = album.price * Decimal("0.15")
        dj_revenue = album.price - commission
        
        Purchase.objects.create(
            user=listener, seller=album.dj, content_id=album.id, content_type='album',
            original_price=album.price, price_paid=album.price, commission=commission,
            dj_revenue=dj_revenue, status='paid', paid_at=sale_date, created_at=sale_date
        )
        
        wallet = DJWallet.objects.get(dj=album.dj)
        wallet.total_earnings = Decimal(str(wallet.total_earnings)) + dj_revenue
        wallet.available_for_payout = Decimal(str(wallet.available_for_payout)) + dj_revenue
        wallet.save()
        album.dj.total_revenue = Decimal(str(album.dj.total_revenue)) + dj_revenue
        album.dj.save()

    # 5. Create Announcements
    for dj in djs:
        DJAnnouncement.objects.create(
            dj=dj,
            title="New Track Dropping Soon!",
            content="Stay tuned for my upcoming release next week. It's going to be a banger! 🔥"
        )

    # 6. Create Bundles
    for dj in djs:
        bundle_tracks = Track.objects.filter(dj=dj)[:3]
        if bundle_tracks.count() >= 2:
            bundle = Bundle.objects.create(
                dj=dj,
                title=f"{dj.dj_name}'s Essential Pack",
                price=Decimal("149.00"),
                description="Get my top 3 tracks for a discounted price!"
            )
            for bt in bundle_tracks:
                BundleTrack.objects.create(bundle=bundle, track=bt)

    print("✅ Mock data generation complete!")

if __name__ == "__main__":
    create_mock_data()
