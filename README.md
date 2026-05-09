# Full-Stack AI SaaS Boilerplate

Cluster 24 of the NextAura 500 SDKs / 25 Clusters project.

Production-ready AI SaaS starter with auth, billing, AI integrations, and everything wired up out of the box.

## Stack

- Next.js 14 (App Router) + TypeScript + Tailwind
- Supabase for auth, database, and storage
- Stripe for subscriptions and billing
- OpenAI / Anthropic / Ollama for AI features
- tRPC for end-to-end type-safe APIs
- Upstash Redis for rate limiting and caching
- Resend for transactional email
- Vercel for deployment
- Sentry for error monitoring
- PostHog for product analytics

## SDKs Used

Next.js, Supabase SDK, Stripe SDK, OpenAI SDK, Anthropic SDK, tRPC, Upstash Redis, Resend SDK, Vercel SDK, Sentry SDK, PostHog SDK, Zod, Auth.js, Prisma, Drizzle ORM, Shadcn/UI, Tailwind, FastAPI, Prometheus Client, Pydantic

## Quickstart

```bash
# Frontend
npm install
cp .env.example .env.local
npm run dev

# AI backend
pip install -r requirements.txt
python main.py --mode serve

# Deploy
vercel deploy
```

## Features

- Auth: email/password, OAuth (GitHub, Google), magic links
- Billing: Stripe subscriptions with free/pro/enterprise tiers
- AI chat with streaming, model switching, conversation history
- File upload and processing
- Rate limiting per plan
- Usage tracking and analytics dashboard
- Admin panel
- Email notifications (welcome, billing alerts)
