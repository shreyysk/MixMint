# MixMint Release Strategy

## Environment Flow
1. **Development**: Local development using `.env.local`. Branching from `main` into feature branches.
2. **Staging**: Pushes to `main` trigger a deployment to the Staging environment on Vercel. This environment uses semi-production keys (e.g. Razorpay Test Mode).
3. **Production**: Tagged releases or manual promotion from `main` to the Production environment. Uses Live keys.

## Deployment Process
- All PRs to `main` undergo automated CI (Lint, Type Check, Build).
- Production deployments are protected and require successful CI status.

## Rollback Procedure
1. **Instant Rollback (Vercel)**: Use the Vercel dashboard to "Promote" a previous successful deployment to Production. This typically takes < 30 seconds.
2. **Database Rollback**: If a deployment involved a migration that must be reversed, use Supabase backups to restore to a point-in-time (PITR) if available, or manually run revert scripts.

## Versioning
- Follow semantic versioning (`vMAJOR.MINOR.PATCH`).
- Major: Breaking infrastructure changes.
- Minor: New features or dashboard updates.
- Patch: Security hardening or bug fixes.
