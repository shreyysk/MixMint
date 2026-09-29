"""
Sign-up, login, logout, password reset and Google sign-in — end-to-end with the test client.
Google is simulated by mocking the token exchange and the profile call.
"""

import re
from unittest import mock

import pytest
from django.core import mail
from django.test import Client

PW = "Str0ng!Passw0rd#2026"
NEW_PW = "N3w/Passw0rd~xyz"  # symbols outside the old allow-list must work


def _signup(c, email, name="Test User", pw=PW, **extra):
    data = {"full_name": name, "email": email, "password": pw, "confirm_password": pw}
    data.update(extra)
    return c.post("/signup/", data)


def _user(email):
    from apps.accounts.models import User

    return User.objects.filter(email__iexact=email).first()


@pytest.fixture
def google(settings):
    settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = "client-id"
    settings.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = "client-secret"
    settings.GOOGLE_LOGIN_ENABLED = True

    def run(client, profile, next_url=None):
        r = client.post("/social-auth/login/google-oauth2/", {"next": next_url} if next_url else {})
        assert r.status_code == 302 and r["Location"].startswith("https://accounts.google.com/")
        state = re.search(r"state=([^&]+)", r["Location"]).group(1)
        if profile is None:  # user pressed "Cancel" on Google's screen
            return client.get(f"/social-auth/complete/google-oauth2/?state={state}&error=access_denied")
        with mock.patch(
            "social_core.backends.google.GoogleOAuth2.request_access_token",
            return_value={"access_token": "t", "token_type": "Bearer"},
        ), mock.patch("social_core.backends.google.GoogleOAuth2.user_data", return_value=profile):
            return client.get(f"/social-auth/complete/google-oauth2/?state={state}&code=abc")

    return run


def _messages(response_or_client_get):
    return [str(m) for m in response_or_client_get.context["messages"]] if response_or_client_get.context else []


# ------------------------------------------------------------------------ sign-up
@pytest.mark.django_db
class TestSignup:
    def test_signup_logs_in_lowercases_and_sends_welcome(self):
        c = Client()
        r = _signup(c, "New.Person@Example.COM")
        assert r.status_code == 302 and r["Location"] == "/dashboard/"
        u = _user("new.person@example.com")
        assert u.email == "new.person@example.com"
        assert u.profile.full_name == "Test User"
        assert any("Welcome" in m.subject for m in mail.outbox)
        assert c.get("/dashboard/").status_code == 200

    def test_signup_returns_to_next(self):
        r = _signup(Client(), "a@example.com", next="/explore/")
        assert r["Location"] == "/explore/"

    def test_signup_refuses_offsite_next(self):
        r = _signup(Client(), "b@example.com", next="https://evil.example/")
        assert r["Location"] == "/dashboard/"

    def test_duplicate_email_any_case_is_refused_and_form_kept(self):
        _signup(Client(), "dup@example.com")
        r = _signup(Client(), "DUP@Example.com", name="Other")
        assert r.status_code == 200
        assert b"already exists" in r.content or any("already exists" in m for m in _messages(r))
        assert r.context["form_name"] == "Other"

    def test_duplicate_of_google_account_points_to_google(self, google):
        google(Client(), {"sub": "1", "email": "g@gmail.com", "email_verified": True, "name": "G"})
        r = _signup(Client(), "g@gmail.com")
        assert any("Google" in m for m in _messages(r))

    def test_any_symbol_satisfies_password_rule(self):
        r = _signup(Client(), "sym@example.com", pw="Abcdefg1/")
        assert r.status_code == 302


# ------------------------------------------------------------------------- login
@pytest.mark.django_db
class TestLogin:
    def test_login_is_case_insensitive_even_for_legacy_mixed_case_rows(self):
        from apps.accounts.models import User

        u = User.objects.create_user(email="x@example.com", password=PW)
        User.objects.filter(pk=u.pk).update(email="Legacy.User@Example.com")  # stored before lowercasing
        r = Client().post("/login/", {"email": "legacy.user@example.com", "password": PW})
        assert r.status_code == 302 and r["Location"] == "/dashboard/"

    def test_wrong_password(self):
        _signup(Client(), "w@example.com")
        r = Client().post("/login/", {"email": "w@example.com", "password": "nope"})
        assert r.status_code == 200 and any("Invalid email or password" in m for m in _messages(r))

    def test_google_only_account_gets_a_helpful_message(self, google):
        google(Client(), {"sub": "2", "email": "go@gmail.com", "email_verified": True, "name": "Go"})
        r = Client().post("/login/", {"email": "go@gmail.com", "password": "whatever"})
        assert any("Continue with Google" in m for m in _messages(r))

    def test_frozen_account_cannot_log_in(self):
        _signup(Client(), "f@example.com")
        u = _user("f@example.com")
        u.profile.is_frozen = True
        u.profile.save()
        c = Client()
        c.post("/login/", {"email": "f@example.com", "password": PW})
        assert c.get("/dashboard/").status_code == 302  # bounced to login

    def test_logout_works_and_is_safe_when_logged_out(self):
        c = Client()
        _signup(c, "l@example.com")
        assert c.get("/logout/").status_code == 302
        assert c.get("/dashboard/").status_code == 302
        assert Client().get("/logout/").status_code == 302  # no error when not logged in

    def test_login_page_shows_google_form_only_when_configured(self, settings):
        settings.GOOGLE_LOGIN_ENABLED = False
        assert b"social-auth/login/google-oauth2" not in Client().get("/login/").content
        settings.GOOGLE_LOGIN_ENABLED = True
        html = Client().get("/login/?next=/library/").content.decode()
        assert 'method="post" action="/social-auth/login/google-oauth2/"' in html
        assert 'name="next" value="/library/"' in html


# ---------------------------------------------------------------- password reset
@pytest.mark.django_db
class TestPasswordReset:
    def _reset(self, email):
        mail.outbox.clear()
        r = Client().post("/password-reset/", {"email": email})
        assert r.status_code == 302 and r["Location"] == "/password-reset/done/"
        return mail.outbox

    def _follow_link(self, message, new_pw):
        link = re.search(r"https?://[^\s\"]+/reset/[^\s\"]+/", message.body).group(0)
        c = Client()
        r = c.get(re.sub(r"https?://[^/]+", "", link), follow=True)
        assert r.context["validlink"]
        set_url = r.redirect_chain[-1][0]
        return c.post(set_url, {"new_password1": new_pw, "new_password2": new_pw})

    def test_full_reset_flow_with_branded_email(self):
        _signup(Client(), "r@example.com")
        outbox = self._reset("R@Example.com")
        assert len(outbox) == 1
        msg = outbox[0]
        assert msg.subject == "Reset your MixMint password"
        assert any(mt == "text/html" for _, mt in msg.alternatives)
        r = self._follow_link(msg, NEW_PW)
        assert r.status_code == 302 and r["Location"] == "/reset/done/"
        r = Client().post("/login/", {"email": "r@example.com", "password": NEW_PW})
        assert r["Location"] == "/dashboard/"

    def test_weak_new_password_is_rejected(self):
        _signup(Client(), "weak@example.com")
        r = self._follow_link(self._reset("weak@example.com")[0], "short")
        assert r.status_code == 200 and r.context["form"].errors

    def test_google_user_can_set_a_password(self, google):
        google(Client(), {"sub": "3", "email": "gp@gmail.com", "email_verified": True, "name": "GP"})
        outbox = self._reset("gp@gmail.com")
        assert len(outbox) == 1
        self._follow_link(outbox[0], NEW_PW)
        assert Client().post("/login/", {"email": "gp@gmail.com", "password": NEW_PW})["Location"] == "/dashboard/"

    def test_unknown_or_banned_email_sends_nothing_but_looks_the_same(self):
        assert self._reset("nobody@example.com") == []
        _signup(Client(), "ban@example.com")
        u = _user("ban@example.com")
        u.profile.is_banned = True
        u.profile.save()
        assert self._reset("ban@example.com") == []


# --------------------------------------------------------------- Google sign-in
@pytest.mark.django_db
class TestGoogle:
    def test_get_on_begin_is_not_the_entry_point(self, google):
        assert Client().get("/social-auth/login/google-oauth2/").status_code == 405

    def test_begin_sends_to_google_with_account_chooser(self, settings, google):
        r = Client().post("/social-auth/login/google-oauth2/")
        assert "prompt=select_account" in r["Location"]
        assert "redirect_uri=http%3A%2F%2Ftestserver%2Fsocial-auth%2Fcomplete%2Fgoogle-oauth2%2F" in r[
            "Location"
        ] or "redirect_uri=http://testserver/social-auth/complete/google-oauth2/" in r["Location"]

    def test_new_user(self, google):
        c = Client()
        r = google(
            c,
            {"sub": "10", "email": "Fresh@Gmail.com", "email_verified": True, "given_name": "Fresh",
             "family_name": "User", "name": "Fresh User"},
            next_url="/explore/",
        )
        assert r.status_code == 302 and r["Location"] == "/explore/"
        u = _user("fresh@gmail.com")
        assert u.email == "fresh@gmail.com" and not u.has_usable_password()
        assert u.profile.full_name == "Fresh User"
        assert u.login_history.filter(location_data__method="google").exists()
        assert any("Welcome" in m.subject for m in mail.outbox)
        assert c.get("/dashboard/").status_code == 200

    def test_returning_google_user(self, google):
        profile = {"sub": "11", "email": "back@gmail.com", "email_verified": True, "name": "Back"}
        google(Client(), profile)
        c = Client()
        assert google(c, profile)["Location"] == "/start/"
        from apps.accounts.models import User

        assert User.objects.filter(email__iexact="back@gmail.com").count() == 1

    def test_existing_email_account_is_linked_not_crashing(self, google):
        _signup(Client(), "both@gmail.com", name="Both Ways")
        c = Client()
        r = google(c, {"sub": "12", "email": "Both@gmail.com", "email_verified": True, "name": "Both"})
        assert r["Location"] == "/start/"
        u = _user("both@gmail.com")
        assert u.social_auth.filter(provider="google-oauth2").exists()
        assert u.profile.full_name == "Both Ways"  # their chosen name is kept
        assert u.check_password(PW)  # password login still works

    def test_cancel_returns_to_login_with_message(self, google):
        c = Client()
        r = google(c, None)
        assert r.status_code == 302 and r["Location"] == "/login/"
        assert any("cancelled" in m for m in _messages(c.get("/login/")))

    def test_unverified_google_email_is_refused(self, google):
        _signup(Client(), "victim@example.com")
        c = Client()
        r = google(c, {"sub": "13", "email": "victim@example.com", "email_verified": False})
        assert r["Location"] == "/login/"
        assert not _user("victim@example.com").social_auth.exists()
        assert c.get("/dashboard/").status_code == 302

    def test_frozen_user_is_refused(self, google):
        profile = {"sub": "14", "email": "cold@gmail.com", "email_verified": True, "name": "Cold"}
        google(Client(), profile)
        u = _user("cold@gmail.com")
        u.profile.is_frozen = True
        u.profile.save()
        c = Client()
        r = google(c, profile)
        assert r["Location"] == "/login/"
        assert any("frozen" in m for m in _messages(c.get("/login/")))
        assert c.get("/dashboard/").status_code == 302

    def test_expired_state_is_friendly(self, google):
        c = Client()
        r = c.get("/social-auth/complete/google-oauth2/?state=bogus&code=abc")
        assert r.status_code == 302 and r["Location"] == "/login/"


# ------------------------------------------------------------------------ API/JWT
@pytest.mark.django_db
class TestApiAuth:
    def test_register_validates(self):
        c = Client()
        weak = c.post("/api/v1/accounts/register/", {"email": "a@example.com", "password": "weak", "full_name": "A"})
        assert weak.status_code == 400 and "password" in weak.json()
        temp = c.post("/api/v1/accounts/register/", {"email": "a@mailinator.com", "password": PW, "full_name": "A"})
        assert temp.status_code == 400
        ok = c.post("/api/v1/accounts/register/", {"email": "Api@Example.com", "password": PW, "full_name": "A"})
        assert ok.status_code == 201 and ok.json()["access"]
        dup = c.post("/api/v1/accounts/register/", {"email": "api@example.COM", "password": PW, "full_name": "A"})
        assert dup.status_code == 400

    def test_token_login_refresh_logout(self):
        _signup(Client(), "jwt@example.com")
        c = Client()
        r = c.post("/api/v1/accounts/token/", {"email": "JWT@example.com", "password": PW})
        assert r.status_code == 200, r.content
        tokens = r.json()
        assert tokens["role"] == "user"
        me = c.get("/api/v1/accounts/profiles/", HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        assert me.status_code == 200
        r = c.post("/api/v1/accounts/token/refresh/", {"refresh": tokens["refresh"]})
        assert r.status_code == 200
        new_refresh = r.json()["refresh"]
        assert c.post("/api/v1/accounts/logout/", {"refresh": new_refresh}).status_code == 205
        assert c.post("/api/v1/accounts/token/refresh/", {"refresh": new_refresh}).status_code == 401

    def test_token_login_wrong_password_and_frozen(self):
        _signup(Client(), "tf@example.com")
        c = Client()
        assert c.post("/api/v1/accounts/token/", {"email": "tf@example.com", "password": "x"}).status_code == 401
        u = _user("tf@example.com")
        u.profile.is_frozen = True
        u.profile.save()
        assert c.post("/api/v1/accounts/token/", {"email": "tf@example.com", "password": PW}).status_code == 400
