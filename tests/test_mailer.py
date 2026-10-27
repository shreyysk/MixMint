"""Email provider chain: Resend first, Hostinger SMTP as backup, per-provider counters and limits."""

from unittest import mock

import pytest
from django.core import mail
from django.core.cache import cache

from apps.admin_panel import plan_watch
from apps.core import mailer

MSG = {"from": "MixMint <noreply@mixmint.site>", "to": ["buyer@example.com"], "subject": "Your receipt", "html": "<p>Thanks</p>"}


@pytest.fixture
def both(settings):
    cache.clear()
    settings.RESEND_API_KEY = "re_test"
    settings.SMTP_USER = "hello@mixmint.site"
    settings.SMTP_PASSWORD = "pw"
    settings.SMTP_DAILY_LIMIT = 1000
    settings.EMAIL_PROVIDER = "auto"
    return settings


def test_order_and_capacity(both):
    assert mailer.order() == ["resend", "smtp"]
    assert mailer.provider_limits() == {"resend": (100, 3000), "smtp": (1000, 30000)}
    from apps.core.email_budget import limits

    assert limits() == (1100, 33000)
    both.EMAIL_PROVIDER = "smtp"
    assert mailer.order() == ["smtp"]


def test_resend_used_when_it_works(both):
    with mock.patch("apps.core.resend_backend.requests.post") as post:
        post.return_value.raise_for_status.return_value = None
        assert mailer.deliver(dict(MSG)) == "resend"
    assert plan_watch.emails("resend") == (1, 1) and plan_watch.emails() == (1, 1)
    assert len(mail.outbox) == 0


def test_falls_back_to_hostinger_when_resend_fails(both):
    with mock.patch("apps.core.resend_backend.requests.post", side_effect=Exception("429 limit")), \
         mock.patch("apps.core.mailer.smtp_connection", return_value=mail.get_connection("django.core.mail.backends.locmem.EmailBackend")):
        assert mailer.deliver(dict(MSG)) == "smtp"
    sent = mail.outbox[-1]
    assert sent.from_email == "MixMint <hello@mixmint.site>"  # Hostinger relays only as the mailbox
    assert sent.reply_to == ["noreply@mixmint.site"] and sent.alternatives[0][0] == "<p>Thanks</p>"
    assert plan_watch.emails("smtp") == (1, 1)


def test_skips_resend_when_it_is_at_its_daily_limit(both):
    for _ in range(100):
        plan_watch.count_email("resend")
    with mock.patch("apps.core.resend_backend.requests.post") as post, \
         mock.patch("apps.core.mailer.smtp_connection", return_value=mail.get_connection("django.core.mail.backends.locmem.EmailBackend")):
        assert mailer.deliver(dict(MSG)) == "smtp"
    assert not post.called


def test_smtp_only_and_django_backend(both):
    both.RESEND_API_KEY = ""
    both.EMAIL_BACKEND = "apps.core.resend_backend.ResendEmailBackend"
    with mock.patch("apps.core.mailer.smtp_connection", return_value=mail.get_connection("django.core.mail.backends.locmem.EmailBackend")):
        from django.core.mail import send_mail

        assert send_mail("Your sign-in link", "Click", "noreply@mixmint.site", ["a@b.c"]) == 1
    assert mail.outbox[-1].subject == "Your sign-in link"


def test_raises_when_every_provider_fails(both):
    with mock.patch("apps.core.resend_backend.requests.post", side_effect=Exception("down")), \
         mock.patch("apps.core.mailer.smtp_connection", side_effect=OSError("blocked")):
        with pytest.raises(OSError):
            mailer.deliver(dict(MSG))


def test_nothing_configured(settings):
    settings.RESEND_API_KEY = ""
    settings.SMTP_USER = ""
    assert not mailer.ready() and mailer.deliver(dict(MSG)) is None
