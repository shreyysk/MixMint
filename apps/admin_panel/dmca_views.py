from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from apps.tracks.models import Track
from apps.albums.models import AlbumPack

@login_required
def generate_dmca_template(request, content_id, content_type='track'):
    """
    Generate a pre-filled DMCA takedown notice [Spec §9].
    DJs can use this to report piracy of their content.
    """
    if not request.user.profile.is_dj:
        return JsonResponse({'error': 'Only DJs can generate DMCA notices.'}, status=403)

    try:
        if content_type == 'track':
            content = Track.objects.get(id=content_id, dj=request.user.dj_profile)
        else:
            content = AlbumPack.objects.get(id=content_id, dj=request.user.dj_profile)
    except (Track.DoesNotExist, AlbumPack.DoesNotExist):
        return JsonResponse({'error': 'Content not found or unauthorized.'}, status=404)

    dj_name = request.user.dj_profile.dj_name
    content_title = content.title
    platform_url = f"https://mixmint.site/{content_type}/{content_id}"

    template = f"""
DMCA TAKEDOWN NOTICE

To: [Infringing Platform Name]
From: {dj_name} (via MixMint)
Date: {timezone.now().strftime('%Y-%m-%d')}

Subject: Formal Notice of Copyright Infringement

I am the copyright owner (or authorized agent) of the sound recording entitled "{content_title}".

The original content is hosted on the secure digital distribution platform MixMint at:
{platform_url}

It has come to my attention that your service is hosting/distributing unauthorized copies of this work without my consent. This activity constitutes copyright infringement.

I have a good faith belief that use of the copyrighted materials described above as allegedly infringing is not authorized by the copyright owner, its agent, or the law.

I swear, under penalty of perjury, that the information in the notification is accurate and that I am the copyright owner or am authorized to act on behalf of the owner of an exclusive right that is allegedly infringed.

Please remove the infringing material immediately.

Regards,
{dj_name}
Authorized via MixMint (mixmint.site)
"""

    return JsonResponse({
        'template': template,
        'dj_name': dj_name,
        'content_title': content_title
    })
