# MixMint 2.0 (Django Migration)

Welcome to the Django-based version of MixMint. This project is a complete conversion from the original Next.js/Supabase stack to a robust **Django 5 + Django REST Framework** architecture.

## Tech Stack
- **Backend**: Django 5.1 (Python 3.12+)
- **API**: Django REST Framework (DRF) with JWT Authentication (Supabase Service Role compatible)
- **Database**: Supabase PostgreSQL (Production) / SQLite (Dev)
- **Storage**: Cloudflare R2 / Supabase Storage (S3 Compatible)
- **Payments**: Razorpay Integrated
- **Auth**: Custom User model (Synched with Supabase Auth)
- **Frontend Layer**: Django Templates + HTMX (Ready for progressive enhancement)

## Project Structure
- `config/`: Project settings and core routing.
- `apps/`: Modularized application logic:
  - `accounts/`: User auth, Profiles, DJ storefronts.
  - `tracks/`: Music track management and previews.
  - `albums/`: Album packs and ZIP processing.
  - `commerce/`: Wallets, purchases, and ledger entries.
  - `payments/`: Razorpay integration.
  - `social/`: Follows, reviews, and wishlists.
  - `rewards/`: Points system and referrals.
  - `downloads/`: Secure download token generation.
  - `admin_panel/`: System settings and audit logs.
  - `analytics/`: A/B testing and event tracking.

## Getting Started

### 1. Prerequisites
- Python 3.12 or higher
- PostgreSQL (optional for dev, uses SQLite by default)
- Redis (for Celery background tasks like ZIP processing)

### 2. Installation
```bash
# Clone the repository and enter the directory
cd mixmint2.0

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration
- Copy `.env.example` to `.env`.
- Fill in your credentials for R2, Razorpay, and PostgreSQL.

### 4. Database Setup
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

### 5. Running the Project
```bash
python manage.py runserver
```
Visit `http://localhost:8000/admin/` to access the admin dashboard or `http://localhost:8000/api/v1/` for the API.

## Features Implemented
- [x] **Universal Auth**: Role-based access (User, DJ, Admin).
- [x] **DJ Storefronts**: Custom profiles with slugs and social links.
- [x] **Track Management**: Full CRUD with metadata (BPM, Genre, Cover Art).
- [x] **Monetization**: Razorpay integrated payments and platform fees.
- [x] **Rewards Engine**: Points balance and referral tracking.
- [x] **Secure Downloads**: Token-based expiring download links.
- [x] **Audit Trails**: Detailed logs for admin actions.

---
Converted by Antigravity (Advanced Agentic Coding)
