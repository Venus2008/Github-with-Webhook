from urllib import request
from django.shortcuts import render
import hmac
import hashlib
import json
from django.conf import settings
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from myapp.models import WebhookEvent


def verify_github_signature(request):
    github_signature = request.headers.get("X-Hub-Signature-256")
    if not github_signature:
        return False

    secret = settings.GITHUB_WEBHOOK_SECRET.encode()
    body = request.body
    expected_signature = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()

    return hmac.compare_digest(github_signature, expected_signature)



# Webhook receiver
@csrf_exempt  # GitHub won’t send CSRF token, so we disable it here
def github_webhook_receiver(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    # Verify signature
    if not verify_github_signature(request):
        return HttpResponseForbidden("Invalid signature")

    # Get event type from headers
    event_type = request.headers.get("X-GitHub-Event", "unknown")

    # Parse payload
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # Extract repo name (if available)
    repo_name = payload.get("repository", {}).get("name", "unknown")

    # Save to DB
    WebhookEvent.objects.create(
        event_type=event_type,
        repo_name=repo_name,
        payload=payload,
    )
    print("GitHub Signature:", request.headers.get("X-Hub-Signature-256"))
    print("Calculated:", "sha256=" + hmac.new(settings.GITHUB_WEBHOOK_SECRET.encode(), request.body, hashlib.sha256).hexdigest())
    return JsonResponse({"status": "success", "event": event_type})



# Event dashboard
def event_list(request):
    events = WebhookEvent.objects.order_by("-received_at")[:50]  # latest 50
    return render(request, "webhooks/event_list.html", {"events": events})
