from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout as auth_logout
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.views import View
from django.db import connection
from .models import User, Profile, LoginHistory
from .validators import validate_email_domain, validate_strong_password


def _get_client_ip(request):
    """Extract real client IP from request (trusted-proxy aware)."""
    from apps.core.net import get_client_ip

    return get_client_ip(request)


def _rate_limited(key, limit, window):
    """Fixed-window limiter backed by the cache. True when over the limit."""
    from django.core.cache import cache

    cache.add(key, 0, timeout=window)
    try:
        return cache.incr(key) > limit
    except ValueError:
        cache.set(key, 1, timeout=window)
        return False


def _bind_session(request):
    from .middleware import _network_of

    request.session["bound_net"] = _network_of(_get_client_ip(request))


def _send_welcome(user):
    """Welcome email for a brand-new account. Never blocks or breaks sign-up."""
    try:
        from .tasks import send_welcome_email

        send_welcome_email.delay(user.id)
    except Exception:
        import logging

        logging.getLogger("mixmint").exception("Welcome email could not be queued for user %s", user.pk)


def home_for(user):
    """Where a signed-in user lands by default: admins -> admin dashboard, approved DJs -> DJ dashboard."""
    profile = getattr(user, "profile", None)
    if user.is_staff or getattr(profile, "role", "") == "admin":
        return "admin_dashboard"
    dj = getattr(profile, "dj_profile", None) if profile is not None and hasattr(profile, "dj_profile") else None
    if getattr(profile, "role", "") == "dj" and dj is not None and dj.status == "approved":
        return "dj_dashboard"
    return "dashboard"


@login_required
def after_login_view(request):
    return redirect(home_for(request.user))


def signup_view(request):
    """User registration with Profile creation [Spec §3.1, §13]."""
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()[:120]
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")

        keep = {"form_email": email, "form_name": full_name}
        if _rate_limited(f"signup_ip_{_get_client_ip(request)}", limit=10, window=3600):
            messages.error(request, "Too many sign-up attempts from your network. Please try again later.")
            return render(request, "auth/signup.html", keep, status=429)

        from django.core.validators import validate_email

        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "Enter a valid email address.")
            return render(request, "auth/signup.html", {"form_email": email, "form_name": full_name})

        # Validate temp email domains [Spec §13]
        try:
            validate_email_domain(email)
        except ValidationError as e:
            messages.error(request, e.message)
            return render(request, "auth/signup.html", {"form_email": email, "form_name": full_name})

        confirm = request.POST.get("confirm_password")
        if confirm is not None and confirm != password:
            messages.error(request, "Passwords don't match.")
            return render(request, "auth/signup.html", {"form_email": email, "form_name": full_name})

        # Validate strong password [Spec §11]
        try:
            validate_strong_password(password)
        except ValidationError as e:
            messages.error(request, e.message)
            return render(request, "auth/signup.html", {"form_email": email, "form_name": full_name})

        if not full_name:
            messages.error(request, "Full name is required.")
            return render(request, "auth/signup.html", keep)

        existing = User.objects.filter(email__iexact=email).first()
        if existing:
            if not existing.has_usable_password():
                messages.error(
                    request,
                    "This email is already registered with Google. Use \"Continue with Google\" to sign in.",
                )
            else:
                messages.error(request, "An account with this email already exists. Log in or reset your password.")
            return render(request, "auth/signup.html", keep)

        from django.db import IntegrityError

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    email=email,
                    password=password,
                    first_name=full_name.split(" ")[0] if " " in full_name else full_name,
                    last_name=full_name.split(" ", 1)[1] if " " in full_name else "",
                )
        except IntegrityError:  # two sign-ups with the same email at the same moment
            messages.error(request, "An account with this email already exists. Log in or reset your password.")
            return render(request, "auth/signup.html", keep)

        with transaction.atomic():

            # Profile is auto-created via accounts.signals; ensure desired defaults.
            profile = user.profile
            profile.full_name = full_name
            profile.role = "user"  # DJ status is granted via application + admin approval [Spec §7]

            # Handle Referral [Imp 15]
            ref_code = request.session.get("ref_code")
            if ref_code:
                from .models import AmbassadorCode

                try:
                    ambassador = AmbassadorCode.objects.get(code=ref_code, is_active=True)
                    from apps.commerce.referrals import has_room

                    if has_room(ambassador.dj):
                        profile.referred_by = ambassador.dj
                        ambassador.referral_count += 1
                        ambassador.save()
                    # Clear session after use
                    del request.session["ref_code"]
                except AmbassadorCode.DoesNotExist:
                    pass

            profile.save(update_fields=["full_name", "role", "referred_by"])

            login(request, user, backend="django.contrib.auth.backends.ModelBackend")

            # Bind session to network [Spec §13]
            _bind_session(request)

            # Record login history [Spec §13]
            device_hash = (request.headers.get("X-Device-Hash") or request.POST.get("device_hash", ""))[:128]

            LoginHistory.objects.create(
                user=user,
                ip_address=_get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:1000],
                location_data={"device_hash": device_hash} if device_hash else {},
            )

        _send_welcome(user)
        messages.success(request, f"Welcome to MixMint, {full_name}!")
        from django.utils.http import url_has_allowed_host_and_scheme

        next_url = request.POST.get("next") or request.GET.get("next")
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            return redirect(next_url)
        return redirect("dashboard")

    return render(request, "auth/signup.html")


def login_view(request):
    """User login with login history recording [Spec §13]."""
    if request.user.is_authenticated:
        return redirect(home_for(request.user))

    if request.method == "POST":
        email = (request.POST.get("email") or request.POST.get("username", "")).strip().lower()
        password = request.POST.get("password", "")
        ip = _get_client_ip(request)

        # Brute-force protection: per IP and per account.
        if _rate_limited(f"login_ip_{ip}", limit=20, window=900) or _rate_limited(
            f"login_email_{email}", limit=8, window=900
        ):
            messages.error(request, "Too many login attempts. Please wait 15 minutes and try again.")
            return render(request, "auth/login.html", {"form_email": email}, status=429)

        user = authenticate(request, username=email, password=password)

        if user is not None:
            # Check if account is frozen [Spec §11]
            try:
                if user.profile.is_frozen:
                    messages.error(request, "Your account has been frozen. Contact support.")
                    return render(request, "auth/login.html")
                if user.profile.is_banned:
                    messages.error(request, "Your account has been banned.")
                    return render(request, "auth/login.html")
            except Profile.DoesNotExist:
                # Create profile if missing (legacy accounts)
                Profile.objects.create(
                    user=user,
                    full_name=f"{user.first_name} {user.last_name}".strip() or user.email,
                )

            login(request, user)

            # Successful login clears the per-account counter; bind session to network [Spec §13]
            from django.core.cache import cache

            cache.delete(f"login_email_{email}")
            _bind_session(request)

            # Record login history [Spec §13]
            device_hash = (request.headers.get("X-Device-Hash") or request.POST.get("device_hash", ""))[:128]

            LoginHistory.objects.create(
                user=user,
                ip_address=_get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:1000],
                location_data={"device_hash": device_hash} if device_hash else {},
            )

            # Also ensure device is registered [Spec §13]
            if device_hash:
                from .models import UserDevice

                UserDevice.objects.update_or_create(
                    user=user, fingerprint=device_hash, defaults={"last_ip": _get_client_ip(request)}
                )

            # Return to where the user was headed (?next=), but only to safe
            # same-host URLs — never follow off-site redirects (open-redirect guard).
            from django.utils.http import url_has_allowed_host_and_scheme

            next_url = request.POST.get("next") or request.GET.get("next")
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect(home_for(user))
        else:
            matches = list(User.objects.filter(email__iexact=email, is_active=True)[:3]) if email else []
            if matches and not any(u.has_usable_password() for u in matches):
                messages.error(
                    request,
                    "This account signs in with Google. Use \"Continue with Google\", "
                    "or set a password with \"Forgot password\".",
                )
            else:
                messages.error(request, "Invalid email or password.")
            return render(request, "auth/login.html", {"form_email": email})

    return render(request, "auth/login.html")


def logout_view(request):
    """User logout [Spec §13]. Works for GET links and POST forms; harmless when already logged out."""
    if not request.user.is_authenticated:
        return redirect("home")
    auth_logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("home")


class HomeView:
    @staticmethod
    def as_view():
        def view(request):
            from apps.tracks.models import Track
            from apps.accounts.models import DJProfile

            # Popular tracks: Highest sales in last 7 days
            popular_tracks = Track.objects.filter(
                is_active=True, is_deleted=False, dj__profile__store_paused=False
            ).select_related("dj", "dj__profile").order_by("-sales_last_7_days", "-created_at")[:12]

            # New Releases: Latest uploaded tracks
            featured_tracks = Track.objects.filter(
                is_active=True, is_deleted=False, dj__profile__store_paused=False
            ).select_related("dj", "dj__profile").order_by("-created_at")[:12]

            # Featured DJs: approved DJs sorted by popularity
            from django.db.models import Count, Q

            featured_djs = (
                DJProfile.objects.filter(status="approved", profile__store_paused=False)
                .select_related("profile")
                .annotate(release_count=Count("tracks", filter=Q(tracks__is_active=True, tracks__is_deleted=False), distinct=True))
                .order_by("-popularity_score")[:12]
            )

            from apps.albums.models import AlbumPack

            new_albums = (
                AlbumPack.objects.filter(is_active=True, is_deleted=False, dj__profile__store_paused=False)
                .select_related("dj", "dj__profile")
                .order_by("-created_at")[:12]
            )
            from apps.commerce.models import Bundle
            from apps.core.catalog import attach_stock

            live = dict(is_active=True, is_deleted=False, dj__status="approved", dj__profile__store_paused=False)
            drop_tracks = list(Track.objects.filter(copies_limit__isnull=False, **live).select_related("dj", "dj__profile").order_by("-created_at")[:12])
            new_bundles = [
                b for b in Bundle.objects.filter(**live).select_related("dj", "dj__profile").prefetch_related("bundle_tracks__track").order_by("-created_at")[:16]
                if b.live_tracks()
            ][:12]
            popular_tracks = list(popular_tracks)
            featured_tracks = list(featured_tracks)
            new_albums = list(new_albums)
            attach_stock(popular_tracks + featured_tracks + drop_tracks, "track")
            attach_stock(new_albums, "album")
            crate = {
                "releases": Track.objects.filter(**live).count() + AlbumPack.objects.filter(**live).count(),
                "djs": DJProfile.objects.filter(status="approved", profile__store_paused=False).count(),
            }
            return render(
                request,
                "home.html",
                {
                    "popular_tracks": popular_tracks,
                    "featured_tracks": featured_tracks,
                    "featured_djs": featured_djs,
                    "new_albums": new_albums,
                    "drop_tracks": drop_tracks,
                    "new_bundles": new_bundles,
                    "crate": crate,
                },
            )

        return view


class ExploreView:
    @staticmethod
    def as_view():
        def view(request):
            from apps.tracks.models import Track
            from apps.albums.models import AlbumPack
            from apps.accounts.models import DJProfile

            q = (request.GET.get("q") or "").strip()
            genre = (request.GET.get("genre") or "").strip()
            year = (request.GET.get("year") or "").strip()
            sort = (request.GET.get("sort") or "latest").strip()

            # New Filters [Gap Analysis Fix]
            asset_type = (request.GET.get("type") or "all").strip()
            price_min = request.GET.get("price_min")
            price_max = request.GET.get("price_max")
            bpm_min = request.GET.get("bpm_min")
            bpm_max = request.GET.get("bpm_max")

            tracks = Track.objects.filter(is_active=True, is_deleted=False, dj__profile__store_paused=False)
            albums = AlbumPack.objects.filter(is_active=True, is_deleted=False, dj__profile__store_paused=False)
            from django.db.models import Count

            base = DJProfile.objects.filter(status="approved", profile__store_paused=False).select_related(
                "profile", "profile__user"
            ).annotate(release_count=Count("tracks", filter=Q(tracks__is_active=True, tracks__is_deleted=False), distinct=True))
            djs = base

            # BPM Filter
            if bpm_min:
                try:
                    tracks = tracks.filter(bpm__gte=int(bpm_min))
                except BaseException:
                    pass
            if bpm_max:
                try:
                    tracks = tracks.filter(bpm__lte=int(bpm_max))
                except BaseException:
                    pass

            # Price Filter
            if price_min:
                try:
                    tracks = tracks.filter(price__gte=float(price_min))
                    albums = albums.filter(price__gte=float(price_min))
                except BaseException:
                    pass
            if price_max:
                try:
                    tracks = tracks.filter(price__lte=float(price_max))
                    albums = albums.filter(price__lte=float(price_max))
                except BaseException:
                    pass

            if genre:
                tracks = tracks.filter(genre__icontains=genre)

            if year:
                try:
                    tracks = tracks.filter(year=int(year))
                except ValueError:
                    pass

            if q:
                if connection.vendor == "postgresql":
                    from django.contrib.postgres.search import TrigramSimilarity
                    from django.db.models import Q

                    tracks = (
                        tracks.annotate(sim=TrigramSimilarity("title", q))
                        .filter(Q(sim__gt=0.2) | Q(title__icontains=q) | Q(dj__dj_name__icontains=q))
                        .order_by("-sim")
                    )

                    albums = (
                        albums.annotate(sim=TrigramSimilarity("title", q))
                        .filter(Q(sim__gt=0.2) | Q(title__icontains=q) | Q(dj__dj_name__icontains=q))
                        .order_by("-sim")
                    )

                    djs = djs.annotate(sim=TrigramSimilarity("dj_name", q)).filter(sim__gt=0.2).order_by("-sim")
                else:
                    from django.db.models import Q

                    tracks = tracks.filter(Q(title__icontains=q) | Q(dj__dj_name__icontains=q))
                    albums = albums.filter(Q(title__icontains=q) | Q(dj__dj_name__icontains=q))
                    djs = djs.filter(Q(dj_name__icontains=q) | Q(slug__icontains=q))

            if sort == "popular":
                tracks = tracks.order_by("-sales_last_7_days", "-created_at")
            elif sort == "price_low":
                tracks = tracks.order_by("price")
            else:
                tracks = tracks.order_by("-created_at")

            # Filter by Type
            if asset_type == "track":
                albums = AlbumPack.objects.none()
            elif asset_type == "album":
                tracks = Track.objects.none()

            ctx = {
                "q": q,
                "genre": genre,
                "year": year,
                "sort": sort,
                "type": asset_type,
                "price_min": price_min,
                "price_max": price_max,
                "bpm_min": bpm_min,
                "bpm_max": bpm_max,
                "sort_options": [("latest", "Latest"), ("popular", "Popular"), ("price_low", "Price: Low to High")],
                "tracks": tracks.select_related("dj", "dj__profile")[:24],
                "albums": albums.select_related("dj", "dj__profile")[:24],
                "djs": djs[:24],
            }
            return render(request, "explore.html", ctx)

        return view


class DJDirectoryView:
    @staticmethod
    def as_view():
        def view(request):
            from .models import DJProfile
            from django.db import connection
            from django.db.models import Q

            q = (request.GET.get("q") or "").strip()
            genre = (request.GET.get("genre") or "").strip()
            verified = request.GET.get("verified") == "true"
            sort = (request.GET.get("sort") or "popular").strip()

            from django.db.models import Count

            base = (
                DJProfile.objects.filter(status="approved", profile__store_paused=False)
                .select_related("profile", "profile__user")
                .annotate(release_count=Count("tracks", filter=Q(tracks__is_active=True, tracks__is_deleted=False), distinct=True))
            )
            djs = base

            if verified:
                djs = djs.filter(is_verified=True)

            if genre:
                # DJ genres are stored in a JSONField list
                djs = djs.filter(genres__icontains=genre)

            if q:
                if connection.vendor == "postgresql":
                    from django.contrib.postgres.search import TrigramSimilarity

                    djs = (
                        djs.annotate(sim=TrigramSimilarity("dj_name", q))
                        .filter(Q(sim__gt=0.2) | Q(dj_name__icontains=q))
                        .order_by("-sim")
                    )
                else:
                    djs = djs.filter(Q(dj_name__icontains=q) | Q(slug__icontains=q))

            if sort == "popular":
                djs = djs.order_by("-popularity_score", "-total_revenue")
            elif sort == "latest":
                djs = djs.order_by("-profile__created_at")
            else:
                djs = djs.order_by("dj_name")

            all_genres = sorted({g.strip() for gl in base.values_list("genres", flat=True) for g in (gl or []) if isinstance(g, str) and g.strip()}, key=str.lower)
            rows = []
            filtered = bool(q or genre or verified or sort != "popular")
            if not filtered:
                everyone = list(base.order_by("-popularity_score", "-total_revenue")[:60])
                if len(everyone) > 4:
                    rows.append({"id": "popular", "title": "Popular DJs", "djs": everyone[:12]})
                    rows.append({"id": "new", "title": "New on MixMint", "djs": sorted(everyone, key=lambda d: d.created_at, reverse=True)[:12]})
                    for g in all_genres[:6]:
                        in_g = [d for d in everyone if g.lower() in [x.lower() for x in (d.genres or []) if isinstance(x, str)]]
                        if len(in_g) >= 3:
                            rows.append({"id": "g-" + g.lower().replace(" ", "-"), "title": g, "djs": in_g[:12], "more": f"?genre={g}"})
            ctx = {
                "q": q,
                "genre": genre,
                "verified": verified,
                "sort": sort,
                "djs": djs[:48],
                "rows": rows,
                "all_genres": all_genres,
                "filtered": filtered,
            }
            return render(request, "dj/directory.html", ctx)

        return view


class WaitlistSignupView(View):
    """Imp 10: Launch Waitlist System."""

    def post(self, request):
        import json
        from django.http import JsonResponse

        from django.core.validators import validate_email

        try:
            data = json.loads(request.body or b"{}")
        except (ValueError, UnicodeDecodeError):
            return JsonResponse({"error": "Invalid request."}, status=400)
        email = str(data.get("email") or "").strip().lower()
        try:
            validate_email(email)
        except ValidationError:
            return JsonResponse({"error": "Enter a valid email address."}, status=400)
        if _rate_limited(f"waitlist_{_get_client_ip(request)}", limit=10, window=3600):
            return JsonResponse({"error": "Too many requests. Try again later."}, status=429)

        from .models import Waitlist

        _, created = Waitlist.objects.get_or_create(
            email=email,
            defaults={"is_dj": bool(data.get("is_dj", False)), "source": str(data.get("source") or "unknown")[:50]},
        )
        if not created:
            return JsonResponse({"message": "You are already on the waitlist! We will notify you soon."})
        return JsonResponse({"message": "Success! You have been added to the waitlist."})


class ThrottledPasswordResetView:
    """Password reset form with per-IP throttling (stops reset-email bombing)."""

    @staticmethod
    def as_view(**kwargs):
        from django.contrib.auth import views as auth_views

        from .forms import MixMintPasswordResetForm

        kwargs.setdefault("form_class", MixMintPasswordResetForm)
        kwargs.setdefault("subject_template_name", "registration/password_reset_subject.txt")
        kwargs.setdefault("email_template_name", "registration/password_reset_email.txt")
        kwargs.setdefault("html_email_template_name", "registration/password_reset_email.html")
        kwargs.setdefault("extra_email_context", {"site_name": "MixMint"})
        inner = auth_views.PasswordResetView.as_view(**kwargs)

        def view(request, *args, **kw):
            if request.method == "POST" and _rate_limited(f"pwreset_{_get_client_ip(request)}", limit=5, window=3600):
                messages.error(request, "Too many reset requests. Please try again in an hour.")
                return redirect("password_reset")
            return inner(request, *args, **kw)

        return view
