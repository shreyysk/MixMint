"""DJ-to-DJ referrals: a DJ shares their code; when the invited DJ is approved and makes a first sale,
the referrer gets ₹100 and the new DJ ₹50. Each DJ can refer at most MAX_REFERRALS DJs."""

import logging

logger = logging.getLogger("mixmint")
MAX_REFERRALS = 50


def referral_count(referrer_dj):
    from .dj_conversion import DJReferralProgram

    return DJReferralProgram.objects.filter(referrer=referrer_dj).count()


def has_room(referrer_dj):
    return referral_count(referrer_dj) < MAX_REFERRALS


def link_on_approval(dj_profile):
    """When a DJ who signed up through someone's link is approved, record the referral (if the referrer has room)."""
    from .dj_conversion import DJReferralProgram

    try:
        referrer = dj_profile.profile.referred_by
        if referrer is None or referrer.pk == dj_profile.pk:
            return None
        if DJReferralProgram.objects.filter(referred=dj_profile).exists() or not has_room(referrer):
            return None
        code = getattr(getattr(referrer, "ambassador_code", None), "code", "") or "LINK"
        return DJReferralProgram.objects.create(referrer=referrer, referred=dj_profile, referral_code=code)
    except Exception:
        logger.exception("Could not link referral for DJ %s", dj_profile.pk)
        return None


def on_sale(seller_dj):
    """Pay the referral bonuses once, on the referred DJ's first sale."""
    from .dj_conversion import DJReferralProgram

    try:
        if seller_dj is not None and DJReferralProgram.objects.filter(referred=seller_dj, first_sale_achieved=False).exists():
            DJReferralProgram.process_first_sale_bonus(seller_dj)
    except Exception:
        logger.exception("Referral bonus failed for DJ %s", getattr(seller_dj, "pk", None))
