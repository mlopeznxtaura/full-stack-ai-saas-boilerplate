"""
full-stack-ai-saas-boilerplate — Entry Point
"""
import argparse

def parse_args():
    p = argparse.ArgumentParser(description="Full-Stack AI SaaS Boilerplate")
    p.add_argument("--mode", required=True, choices=["serve", "stripe", "demo"])
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--host", default="0.0.0.0")
    return p.parse_args()

def main():
    args = parse_args()
    print("=" * 55)
    print("  Full-Stack AI SaaS Boilerplate")
    print(f"  Mode: {args.mode.upper()}")
    print("=" * 55)

    if args.mode == "serve":
        import uvicorn
        from backend.ai_router import app
        from prometheus_client import start_http_server
        start_http_server(9090)
        print(f"AI backend on {args.host}:{args.port} | Metrics :9090")
        uvicorn.run(app, host=args.host, port=args.port)

    elif args.mode == "stripe":
        from billing.stripe_webhooks import StripeBilling
        billing = StripeBilling()
        print("Stripe billing module loaded.")
        print("Plans:", ["free (50 req/day)", "pro (1000 req/day)", "enterprise (unlimited)"])

    elif args.mode == "demo":
        print("\nSaaS AI Backend Demo")
        print("Plans:", ["free", "pro", "enterprise"])
        print("Models: gpt-3.5-turbo, gpt-4, claude-3-sonnet, ollama/mistral")
        print("\nSet env vars:")
        print("  OPENAI_API_KEY, ANTHROPIC_API_KEY, STRIPE_SECRET_KEY")
        print("  REDIS_URL, SUPABASE_URL, SUPABASE_ANON_KEY")
        print("\nThen run: python main.py --mode serve")

if __name__ == "__main__":
    main()
