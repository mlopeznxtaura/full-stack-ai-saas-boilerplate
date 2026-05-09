"""
Stripe billing integration for SaaS subscriptions.
Handles webhooks: subscription created/updated/canceled, payment failed.
SDKs: Stripe, FastAPI, Redis
"""
import os
import stripe
from fastapi import FastAPI, Request, HTTPException
from typing import Dict, Any

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

PRICE_TO_PLAN = {
    os.environ.get("STRIPE_FREE_PRICE_ID", "price_free"): "free",
    os.environ.get("STRIPE_PRO_PRICE_ID", "price_pro"): "pro",
    os.environ.get("STRIPE_ENTERPRISE_PRICE_ID", "price_enterprise"): "enterprise",
}


class StripeBilling:
    """Stripe subscription management for AI SaaS."""

    def create_checkout_session(
        self, user_id: str, price_id: str, success_url: str, cancel_url: str
    ) -> str:
        """Create a Stripe Checkout session. Returns checkout URL."""
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"user_id": user_id},
        )
        return session.url

    def create_portal_session(self, customer_id: str, return_url: str) -> str:
        """Create a Stripe Customer Portal session for plan management."""
        session = stripe.billing_portal.Session.create(
            customer=customer_id, return_url=return_url
        )
        return session.url

    def get_subscription(self, subscription_id: str) -> Dict[str, Any]:
        sub = stripe.Subscription.retrieve(subscription_id)
        price_id = sub["items"]["data"][0]["price"]["id"]
        return {
            "subscription_id": sub.id,
            "status": sub.status,
            "plan": PRICE_TO_PLAN.get(price_id, "free"),
            "current_period_end": sub.current_period_end,
            "cancel_at_period_end": sub.cancel_at_period_end,
        }

    def handle_webhook(self, payload: bytes, sig_header: str) -> Dict[str, Any]:
        """Verify and process Stripe webhook events."""
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid webhook signature")

        event_type = event["type"]
        data = event["data"]["object"]

        handlers = {
            "checkout.session.completed": self._on_checkout_completed,
            "customer.subscription.updated": self._on_subscription_updated,
            "customer.subscription.deleted": self._on_subscription_deleted,
            "invoice.payment_failed": self._on_payment_failed,
        }

        handler = handlers.get(event_type)
        if handler:
            return handler(data)
        return {"handled": False, "event_type": event_type}

    def _on_checkout_completed(self, session: Dict) -> Dict:
        user_id = session.get("metadata", {}).get("user_id")
        subscription_id = session.get("subscription")
        print(f"[Stripe] Checkout complete: user={user_id}, sub={subscription_id}")
        # Update user plan in Supabase here
        return {"handled": True, "action": "subscription_activated", "user_id": user_id}

    def _on_subscription_updated(self, sub: Dict) -> Dict:
        price_id = sub["items"]["data"][0]["price"]["id"]
        plan = PRICE_TO_PLAN.get(price_id, "free")
        print(f"[Stripe] Subscription updated: {sub['id']} -> {plan}")
        return {"handled": True, "action": "plan_changed", "plan": plan}

    def _on_subscription_deleted(self, sub: Dict) -> Dict:
        print(f"[Stripe] Subscription canceled: {sub['id']}")
        return {"handled": True, "action": "subscription_canceled"}

    def _on_payment_failed(self, invoice: Dict) -> Dict:
        customer_id = invoice.get("customer")
        print(f"[Stripe] Payment failed for customer: {customer_id}")
        # Send dunning email via Resend here
        return {"handled": True, "action": "payment_failed_notified"}
