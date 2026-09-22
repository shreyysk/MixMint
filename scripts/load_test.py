#!/usr/bin/env python
"""
MixMint Load Test Script

Simulates concurrent load on key endpoints:
1. Concurrent explore page browsing
2. Concurrent signup
3. Concurrent checkout attempts (race condition testing)
"""

import asyncio
import httpx
import time
import statistics
import os
import sys
import django
from decimal import Decimal
from asgiref.sync import sync_to_async

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from apps.accounts.models import User, Profile, DJProfile
from apps.tracks.models import Track
from apps.commerce.models import Purchase, DJWallet


async def run_explore_load(base_url: str, num_requests: int = 50, concurrency: int = 10):
    """Simulate concurrent explore page browsing."""
    print(f"\n{'='*60}")
    print(f"LOAD TEST: Explore Page - {num_requests} requests, concurrency {concurrency}")
    print(f"{'='*60}")
    
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        semaphore = asyncio.Semaphore(concurrency)
        
        async def single_request(i: int):
            async with semaphore:
                start = time.perf_counter()
                try:
                    response = await client.get("/explore/", params={"q": "test", "genre": "EDM"})
                    elapsed = time.perf_counter() - start
                    return elapsed, response.status_code, None
                except Exception as e:
                    elapsed = time.perf_counter() - start
                    return elapsed, 0, str(e)
        
        tasks = [single_request(i) for i in range(num_requests)]
        results = await asyncio.gather(*tasks)
    
    latencies = [r[0] for r in results if r[2] is None]
    errors = [r for r in results if r[2] is not None]
    status_codes = [r[1] for r in results]
    
    print(f"  Successful: {len(latencies)}/{num_requests}")
    print(f"  Errors: {len(errors)}")
    if latencies:
        print(f"  Latency (s): avg={statistics.mean(latencies):.3f}, "
              f"p50={statistics.median(latencies):.3f}, "
              f"p95={statistics.quantiles(latencies, n=20)[18]:.3f}, "
              f"p99={max(latencies):.3f}")
    print(f"  Status codes: {dict((k, status_codes.count(k)) for k in set(status_codes))}")
    
    return latencies, errors


async def run_signup_load(base_url: str, num_requests: int = 30, concurrency: int = 10):
    """Simulate concurrent signups."""
    print(f"\n{'='*60}")
    print(f"LOAD TEST: Signup - {num_requests} requests, concurrency {concurrency}")
    print(f"{'='*60}")
    
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0, follow_redirects=True) as client:
        semaphore = asyncio.Semaphore(concurrency)
        
        async def single_signup(i: int):
            async with semaphore:
                start = time.perf_counter()
                try:
                    response = await client.post("/signup/", data={
                        "full_name": f"Load User {i}",
                        "email": f"loaduser{i}@example.com",
                        "password": "StrongPass123!",
                    })
                    elapsed = time.perf_counter() - start
                    return elapsed, response.status_code, None
                except Exception as e:
                    elapsed = time.perf_counter() - start
                    return elapsed, 0, str(e)
        
        tasks = [single_signup(i) for i in range(num_requests)]
        results = await asyncio.gather(*tasks)
    
    latencies = [r[0] for r in results if r[2] is None]
    errors = [r for r in results if r[2] is not None]
    status_codes = [r[1] for r in results]
    
    print(f"  Successful: {len(latencies)}/{num_requests}")
    print(f"  Errors: {len(errors)}")
    if latencies:
        print(f"  Latency (s): avg={statistics.mean(latencies):.3f}, "
              f"p50={statistics.median(latencies):.3f}, "
              f"p95={statistics.quantiles(latencies, n=20)[18]:.3f}, "
              f"p99={max(latencies):.3f}")
    print(f"  Status codes: {dict((k, status_codes.count(k)) for k in set(status_codes))}")
    
    return latencies, errors


async def run_checkout_race_test(base_url: str, num_attempts: int = 20):
    """
    Test for race conditions in checkout.
    Creates a single track and attempts concurrent purchases against it.
    """
    print(f"\n{'='*60}")
    print(f"LOAD TEST: Checkout Race Condition - {num_attempts} concurrent attempts")
    print(f"{'='*60}")
    
    # Setup: Create a test track with one DJ, multiple buyers
    # Use sync_to_async for Django ORM operations
    from apps.accounts.models import User, Profile, DJProfile
    from apps.tracks.models import Track
    from apps.commerce.models import DJWallet
    
    # Clean up any existing test data
    await sync_to_async(lambda: User.objects.filter(email__startswith='race_buyer').delete())()
    await sync_to_async(lambda: User.objects.filter(email='race_seller@example.com').delete())()
    
    # Create seller (DJ)
    def create_seller():
        seller_user = User.objects.create_user(
            email='race_seller@example.com',
            password='Pass123!'
        )
        seller_user.profile.role = 'dj'
        seller_user.profile.save()
        seller_dj = DJProfile.objects.create(
            profile=seller_user.profile,
            dj_name='Race Seller',
            slug='race-seller',
            status='approved'
        )
        DJWallet.objects.get_or_create(dj=seller_dj)
        return seller_dj
    
    seller_dj = await sync_to_async(create_seller)()
    
    # Create track
    def create_track():
        return Track.objects.create(
            dj=seller_dj,
            title='Race Condition Track',
            price=Decimal('50.00'),
            file_key='race.wav',
            preview_type='youtube',
            youtube_url='https://youtube.com/watch?v=race'
        )
    
    track = await sync_to_async(create_track)()
    
    # Create buyers
    def create_buyers():
        buyers = []
        for i in range(num_attempts):
            email = f'race_buyer{i}@example.com'
            user = User.objects.create_user(email=email, password='Pass123!')
            buyers.append(user)
        return buyers
    
    buyers = await sync_to_async(create_buyers)()
    
    print(f"  Created track #{track.id}, {len(buyers)} buyers")
    
    # Now simulate concurrent purchases
    from django.test import Client
    
    def attempt_purchase(buyer_idx: int):
        client = Client()
        buyer = buyers[buyer_idx]
        client.force_login(buyer)
        
        start = time.perf_counter()
        try:
            import json
            response = client.post(
                "/api/v1/payments/initiate/",
                data=json.dumps({
                    "content_id": track.id,
                    "content_type": "track",
                }),
                content_type="application/json"
            )
            elapsed = time.perf_counter() - start
            return {
                "buyer": buyer.email,
                "elapsed": elapsed,
                "status": response.status_code,
                "data": response.json() if response.status_code == 200 else response.content.decode()
            }
        except Exception as e:
            elapsed = time.perf_counter() - start
            return {
                "buyer": buyer.email,
                "elapsed": elapsed,
                "status": 0,
                "error": str(e)
            }
    
    # Run concurrent purchases
    tasks = [asyncio.to_thread(attempt_purchase, i) for i in range(num_attempts)]
    purchase_results = await asyncio.gather(*tasks)
    
    successes = [r for r in purchase_results if r.get("status") == 200]
    failed = [r for r in purchase_results if r.get("status") != 200]
    errors = [r for r in purchase_results if "error" in r]
    
    print(f"  Successful initiations: {len(successes)}/{num_attempts}")
    print(f"  Failed initiations: {len(failed)}")
    print(f"  Errors: {len(errors)}")
    
    if successes:
        latencies = [r["elapsed"] for r in successes]
        print(f"  Initiation latency (s): avg={statistics.mean(latencies):.3f}, "
              f"p50={statistics.median(latencies):.3f}, "
              f"p95={max(latencies):.3f}")
    
    # Check actual purchase records created
    def get_purchases():
        from apps.commerce.models import Purchase
        return list(Purchase.objects.filter(
            content_id=track.id, content_type='track', status='paid'
        ).select_related('user'))
    
    purchases = await sync_to_async(get_purchases)()
    print(f"  Actual paid purchases in DB: {len(purchases)}")
    for p in purchases:
        print(f"    - {p.user.email} | {p.id} | {p.paid_at}")
    
    # Check wallet balance
    def get_wallet():
        from apps.commerce.models import DJWallet
        return DJWallet.objects.get(dj=seller_dj)
    
    wallet = await sync_to_async(get_wallet)()
    print(f"  Seller wallet: total={wallet.total_earnings}, available={wallet.available_for_payout}")
    
    return purchase_results


async def main():
    base_url = "http://127.0.0.1:8000"
    
    print("="*60)
    print("MIXMINT LOAD TEST SUITE")
    print("="*60)
    print(f"Target: {base_url}")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run tests
    await run_explore_load(base_url, num_requests=50, concurrency=10)
    await run_signup_load(base_url, num_requests=30, concurrency=10)
    await run_checkout_race_test(base_url, num_attempts=20)
    
    print("\n" + "="*60)
    print("LOAD TEST COMPLETE")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())