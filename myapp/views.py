from django.shortcuts import render,get_object_or_404
import hmac
import hashlib
import json
from django.conf import settings
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from myapp.models import WebhookEvent
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


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
    event = WebhookEvent.objects.create(
        event_type=event_type,
        repo_name=repo_name,
        payload=payload,
    )

    # 🔥 Broadcast to WebSocket group
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "events",  # group name
        {
            "type": "send_event",  # this maps to EventsConsumer.send_event
            "type": event.event_type,
            "repo": event.repo_name,
            "received_at": event.received_at.strftime("%Y-%m-%d %H:%M:%S"),
        },
    )
    print("GitHub Signature:", request.headers.get("X-Hub-Signature-256"))
    print("Calculated:", "sha256=" + hmac.new(settings.GITHUB_WEBHOOK_SECRET.encode(), request.body, hashlib.sha256).hexdigest())
    return JsonResponse({"status": "success", "event": event_type})



# Event dashboard
def event_list(request):
    events = WebhookEvent.objects.order_by("-received_at")[:50]  # latest 50
    return render(request, "webhooks/event_list.html", {"events": events})



def event_detail(request, pk):
    event = get_object_or_404(WebhookEvent, pk=pk)
    payload = event.payload or {}

    summary = {}

    if event.event_type == "push":
        commits = payload.get("commits", [])
        commit_data = [
            {
                "message": c.get("message"),
                "url": c.get("url")
            }
            for c in commits
        ]
        summary = {
            "Pusher": str(payload.get("pusher", {}).get("name", "")),  # ✅ force string
            "Branch": str(payload.get("ref", "")),                     # ✅ force string
            "Commit Count": str(len(commits)),                         # ✅ force string
            "Commits": commit_data,      # 🔑 list of dicts, safe for template
            }

    elif event.event_type == "issues":
        issue = payload.get("issue", {})
        summary = {
            "Action": payload.get("action", ""),
            "Title": issue.get("title", ""),
            "Number": issue.get("number", ""),
            "State": issue.get("state", ""),
            "Author": issue.get("user", {}).get("login", ""),
            "Issue URL": issue.get("html_url", ""),
        }

    elif event.event_type == "star":
        repo = payload.get("repository", {})
        summary = {
            "Action": payload.get("action", ""),
            "Starred Repo": repo.get("full_name", ""),
            "Starrer": payload.get("sender", {}).get("login", ""),
        }

        # ✅ Normalize values: everything is either string or list of dicts/strings
    for key, val in summary.items():
        if val is None:
            summary[key] = ""
        elif isinstance(val, (int, float)):
            summary[key] = str(val)

    return render(request, "webhooks/event_detail.html", {
        "event": event,
        "summary": summary
    })

