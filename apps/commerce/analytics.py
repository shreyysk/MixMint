from decimal import Decimal
from django.core.cache import cache
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
import calendar
from django.db.models.functions import TruncMonth

from apps.commerce.models import Purchase, AdRevenueLog, DJWallet, Payout

def get_platform_monthly_revenue():
    """Cache platform revenue for 1 hour."""
    now = timezone.now()
    cache_key = f"platform_revenue_{now.strftime('%Y_%m')}"
    cached = cache.get(cache_key)

    if cached is not None:
        return cached

    # Calculate platform commission + checkout fees
    revenue = Purchase.objects.filter(
        created_at__month=now.month,
        created_at__year=now.year,
        is_completed=True
    ).aggregate(
        commission=Sum('commission'),
        fees=Sum('checkout_fee')
    )
    
    total = (revenue['commission'] or Decimal('0.00')) + (revenue['fees'] or Decimal('0.00'))
    cache.set(cache_key, total, 3600)
    return total

def get_platform_lifetime_revenue():
    """Daily cache for lifetime revenue (refresh at midnight)."""
    cache_key = "platform_lifetime_revenue"
    cached = cache.get(cache_key)

    if cached is not None:
        return cached

    totals = Purchase.objects.filter(is_completed=True).aggregate(
        sales=Sum('price_paid'),
        comm=Sum('commission'),
        fees=Sum('checkout_fee'),
        dj_earn=Sum('dj_earnings'),
        count=Count('id')
    )
    
    data = {
        'total_sales': str(totals['sales'] or 0),
        'total_commission': str(totals['comm'] or 0),
        'total_checkout_fees': str(totals['fees'] or 0),
        'total_dj_earnings': str(totals['dj_earn'] or 0),
        'purchase_count': totals['count'] or 0,
    }
    
    # Cache until end of day
    now = timezone.now()
    tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    ttl = (tomorrow - now).seconds
    
    cache.set(cache_key, data, ttl)
    return data

def get_dj_monthly_earnings(dj_id):
    """Cache DJ monthly earnings for 5 minutes."""
    now = timezone.now()
    cache_key = f"dj_earnings_{dj_id}_{now.strftime('%Y_%m')}"
    cached = cache.get(cache_key)

    if cached is not None:
        return cached

    earnings = Purchase.objects.filter(
        seller_id=dj_id, 
        is_completed=True, 
        download_completed=True,
        created_at__month=now.month,
        created_at__year=now.year
    ).aggregate(total=Sum('dj_earnings'))['total'] or Decimal('0.00')

    cache.set(cache_key, earnings, 300)
    return earnings

def get_dj_lifetime_earnings(dj_id):
    """Daily cache for DJ lifetime earnings."""
    cache_key = f"dj_lifetime_{dj_id}"
    cached = cache.get(cache_key)

    if cached is not None:
        return cached

    lifetime = Purchase.objects.filter(
        seller_id=dj_id, 
        is_completed=True, 
        download_completed=True
    ).aggregate(total=Sum('dj_earnings'))['total'] or Decimal('0.00')

    # Cache until end of day
    now = timezone.now()
    tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    ttl = (tomorrow - now).seconds
    
    cache.set(cache_key, lifetime, ttl)
    return lifetime

def invalidate_dj_analytics(dj_id):
    """Call this when a purchase completes or earnings change."""
    now = timezone.now()
    cache.delete(f"dj_earnings_{dj_id}_{now.strftime('%Y_%m')}")
    cache.delete(f"dj_lifetime_{dj_id}")
    # Also invalidate platform revenue since it changed
    cache.delete(f"platform_revenue_{now.strftime('%Y_%m')}")
    cache.delete("platform_lifetime_revenue")

def get_active_dj_count():
    """Cache hourly count of active DJs."""
    cache_key = "active_dj_count"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    from apps.accounts.models import DJProfile
    count = DJProfile.objects.filter(status='approved').count()
    cache.set(cache_key, count, 3600)
    return count

def get_last_month_earnings(dj_id):
    """Get earnings for the previous calendar month."""
    now = timezone.now()
    first_of_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_day_of_prev_month = first_of_this_month - timedelta(days=1)
    
    earnings = Purchase.objects.filter(
        seller_id=dj_id,
        is_completed=True,
        download_completed=True,
        created_at__month=last_day_of_prev_month.month,
        created_at__year=last_day_of_prev_month.year
    ).aggregate(total=Sum('dj_earnings'))['total'] or Decimal('0.00')
    
    return earnings

def get_best_month_earnings(dj_id):
    """Find the highest earning month in history."""
    cache_key = f"dj_best_month_{dj_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    monthly_stats = Purchase.objects.filter(
        seller_id=dj_id,
        is_completed=True,
        download_completed=True
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        total=Sum('dj_earnings')
    ).order_by('-total')

    best = monthly_stats[0]['total'] if monthly_stats.exists() else Decimal('0.00')
    
    cache.set(cache_key, best, 86400)
    return best

def calculate_earnings_forecast(dj_id):
    """Imp 11: Calculate projected earnings based on current month's pace."""
    now = timezone.now()
    days_elapsed = now.day
    _, days_in_month = calendar.monthrange(now.year, now.month)
    days_remaining = days_in_month - days_elapsed

    earned_this_month = get_dj_monthly_earnings(dj_id)
    daily_rate = earned_this_month / Decimal(days_elapsed) if days_elapsed > 0 else Decimal('0.00')
    projected_total = earned_this_month + (daily_rate * Decimal(days_remaining))

    best_month = get_best_month_earnings(dj_id)
    pace_vs_best = (projected_total / best_month * 100) if best_month > 0 else None

    last_month_total = get_last_month_earnings(dj_id)
    vs_last_month = ((projected_total - last_month_total) / last_month_total * 100) if last_month_total > 0 else None

    return {
        'earned_this_month': earned_this_month,
        'projected_total': projected_total,
        'daily_rate': daily_rate,
        'days_remaining': days_remaining,
        'best_month': best_month,
        'pace_vs_best': pace_vs_best,
        'vs_last_month': vs_last_month,
        'month_name': now.strftime('%B %Y'),
        'month_progress_percent': (days_elapsed / days_in_month) * 100
    }
