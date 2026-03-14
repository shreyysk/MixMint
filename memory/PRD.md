# MixMint 2.0 - Project Requirements & Progress Document

## Project Overview
MixMint is a DJ-first digital music distribution platform operating in India.

**Tech Stack**: Django 5.1 + DRF, Supabase PostgreSQL, Cloudflare R2, PhonePe

---

## All Phases Complete ✅

### Phase 1-3: Bug Fixes & Security
### Phase 4: DJ Conversion System  
### Phase 5: Platform Improvements
### Phase 6: Email & Mobile APIs

### Phase 7: Push Notifications & A/B Testing ✅ (Jan 14, 2026)

#### Push Notification System
**Models** (in `/app/apps/accounts/models.py`):
- `PushSubscription` - Web push subscriptions
- `NotificationPreference` - User preferences (email/push per type)
- `InAppNotification` - Stored notifications

**Service**: `/app/apps/core/push_notifications.py`
- `PushNotificationService.notify_sale()`
- `PushNotificationService.notify_milestone()`
- `PushNotificationService.notify_payout()`
- `PushNotificationService.notify_referral_success()`

**API Endpoints**:
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/platform/push/subscribe/` | POST | Register push subscription |
| `/api/v1/platform/push/unsubscribe/` | DELETE | Unregister |
| `/api/v1/platform/notifications/` | GET | Get in-app notifications |
| `/api/v1/platform/notifications/read/` | POST | Mark as read |
| `/api/v1/platform/notifications/preferences/` | GET/PATCH | Preferences |

#### A/B Testing Framework
**Models**:
- `Experiment` - Test definition (name, status, targeting, traffic %)
- `Variant` - Variants with weights and config
- `UserExperiment` - User assignments
- `ExperimentEvent` - Event tracking

**Service**: `/app/apps/core/ab_testing.py`
- `ABTestingService.get_variant(user, experiment_name)`
- `ABTestingService.track_event(user, experiment, event_type)`
- `ABTestingService.get_experiment_stats(experiment_name)`

**API Endpoints**:
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/platform/experiment/<name>/` | GET | Get user's variant |
| `/api/v1/platform/experiment/<name>/track/` | POST | Track event |
| `/api/v1/platform/experiments/` | GET | List user's experiments |
| `/api/v1/platform/admin/experiments/` | GET | Admin: list all |
| `/api/v1/platform/admin/experiments/create/` | POST | Admin: create |
| `/api/v1/platform/admin/experiments/<id>/status/` | POST | Admin: update status |

---

## Complete File List

### Core App (`/app/apps/core/`)
- `improvements.py` - DJ/Buyer/Admin improvements
- `mobile_api.py` - Mobile-optimized endpoints
- `push_notifications.py` - Push notification service
- `ab_testing.py` - A/B testing service
- `notification_views.py` - API endpoints
- `email_service.py` - Email sending service
- `urls.py` - All routes

### Templates (`/app/templates/emails/`)
- `base.html`, `dj_welcome.html`, `sale_notification.html`
- `payout_initiated.html`, `referral_success.html`
- `purchase_confirmation.html`, `milestone_achieved.html`

---

## To Push to GitHub
Use the "Save to Github" button in the chat interface.
