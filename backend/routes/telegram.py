"""
Telegram Bot integration routes
- Account linking between Telegram chat and platform user
- Telegram webhook for conversational loan workflow
"""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
import os
import re
import secrets
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, status

from auth.otp_service import otp_service
from auth.dependencies import get_current_user
from config import settings
from database import mongodb, redis_client
from models.loan_application import ChatMessage
from models.user import User, UserResponse
from routes.loans import (
    _build_initial_state,
    _build_pipeline_progress,
    _normalize_loan_type,
    chat_with_workflow,
    run_workflow_stepwise,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["Telegram"])

_LOAN_TYPE_ALIASES = {
    "personal": "personal_loan",
    "personal_loan": "personal_loan",
    "home": "home_loan",
    "home_loan": "home_loan",
    "business": "business_loan",
    "business_loan": "business_loan",
}


def _main_menu_reply_markup() -> Dict[str, Any]:
    return {
        "keyboard": [
            [{"text": "/auth"}, {"text": "/help"}],
            [{"text": "/new personal"}, {"text": "/new home"}],
            [{"text": "/status"}, {"text": "/history"}],
            [{"text": "/details"}, {"text": "/sanction"}],
            [{"text": "/unlink"}],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
    }


async def _send_telegram_message(
    chat_id: str,
    text: str,
    reply_markup: Optional[Dict[str, Any]] = None,
) -> None:
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN is not configured; skipping Telegram reply")
        return

    api_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(api_url, json=payload)
            response.raise_for_status()
    except Exception as exc:
        logger.error("Failed to send Telegram message: %s", exc, exc_info=True)


async def _send_telegram_document(chat_id: str, file_path: str, caption: str | None = None) -> bool:
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN is not configured; skipping Telegram document send")
        return False

    if not file_path or not os.path.exists(file_path):
        logger.warning("Telegram document not found at path: %s", file_path)
        return False

    api_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendDocument"
    data = {
        "chat_id": chat_id,
    }
    if caption:
        data["caption"] = caption

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            with open(file_path, "rb") as file_handle:
                files = {
                    "document": (os.path.basename(file_path), file_handle, "application/pdf")
                }
                response = await client.post(api_url, data=data, files=files)
                response.raise_for_status()
        return True
    except Exception as exc:
        logger.error("Failed to send Telegram document: %s", exc, exc_info=True)
        return False


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _extract_start_argument(message_text: str) -> str:
    if not message_text:
        return ""
    parts = message_text.strip().split(maxsplit=1)
    if len(parts) < 2:
        return ""
    return parts[1].strip()


def _resolve_loan_type(raw_value: Optional[str]) -> str:
    value = _safe_text(raw_value).lower()
    if not value:
        return "personal_loan"
    mapped = _LOAN_TYPE_ALIASES.get(value)
    if mapped:
        return mapped
    return _normalize_loan_type(value)


def _assistant_reply_from_messages(messages: list[Dict[str, Any]]) -> str:
    if not messages:
        return "I couldn't generate a response. Please try again."

    collected: list[str] = []
    for entry in reversed(messages):
        role = _safe_text(entry.get("role")).lower()
        if role == "user":
            break
        if role == "assistant":
            content = _safe_text(entry.get("content"))
            if content:
                collected.append(content)

    if not collected:
        last = messages[-1]
        fallback = _safe_text(last.get("content"))
        return fallback or "I couldn't generate a response. Please try again."

    collected.reverse()
    return "\n\n".join(collected)


async def _get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    if not user_id:
        return None
    return await mongodb.users.find_one({"user_id": user_id})


def _is_valid_email(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", value or ""))


def _is_valid_otp(value: str) -> bool:
    return bool(re.fullmatch(r"\d{6}", (value or "").strip()))


async def _get_telegram_session(chat_id: str) -> Dict[str, Any]:
    doc = await mongodb.telegram_sessions.find_one({"telegram_chat_id": chat_id})
    return doc or {}


async def _set_telegram_session(chat_id: str, values: Dict[str, Any]) -> None:
    await mongodb.telegram_sessions.update_one(
        {"telegram_chat_id": chat_id},
        {
            "$set": {
                **values,
                "telegram_chat_id": chat_id,
                "updated_at": datetime.utcnow(),
            },
            "$setOnInsert": {
                "created_at": datetime.utcnow(),
            },
        },
        upsert=True,
    )


async def _reset_telegram_session(chat_id: str) -> None:
    await _set_telegram_session(
        chat_id,
        {
            "flow": None,
            "step": None,
            "email": None,
            "details_options": [],
        },
    )


async def _get_or_create_user_by_email(email: str) -> Dict[str, Any]:
    existing_user = await mongodb.users.find_one({"email": email})
    if existing_user:
        await mongodb.users.update_one(
            {"user_id": existing_user["user_id"]},
            {
                "$set": {
                    "is_verified": True,
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        existing_user["is_verified"] = True
        return existing_user

    new_user = User(email=email, is_verified=True, role="user")
    await mongodb.users.insert_one(new_user.model_dump())
    created_user = await mongodb.users.find_one({"user_id": new_user.user_id})
    return created_user or new_user.model_dump()


async def _link_chat_to_user(
    telegram_chat_id: str,
    telegram_user_id: str,
    sender: Dict[str, Any],
    user_doc: Dict[str, Any],
) -> None:
    await mongodb.telegram_links.update_many(
        {"telegram_chat_id": telegram_chat_id, "is_active": True},
        {"$set": {"is_active": False, "updated_at": datetime.now().isoformat()}},
    )

    now = datetime.now().isoformat()
    await mongodb.telegram_links.update_one(
        {"telegram_chat_id": telegram_chat_id},
        {
            "$set": {
                "telegram_chat_id": telegram_chat_id,
                "telegram_user_id": telegram_user_id,
                "telegram_username": sender.get("username"),
                "telegram_first_name": sender.get("first_name"),
                "telegram_last_name": sender.get("last_name"),
                "user_id": user_doc["user_id"],
                "owner_email": user_doc["email"],
                "is_active": True,
                "updated_at": now,
            },
            "$setOnInsert": {"linked_at": now},
        },
        upsert=True,
    )


def _loan_type_label(loan_type: Optional[str]) -> str:
    return (loan_type or "unknown").replace("_loan", "").replace("_", " ").title()


async def _build_history_text(user_id: str) -> str:
    cursor = mongodb.loan_applications.find({"user_id": user_id}).sort("updated_at", -1).limit(12)
    applications = await cursor.to_list(length=12)

    if not applications:
        return "No applications found yet. Start with /new personal|home|business."

    lines = ["Recent applications:"]
    for index, app in enumerate(applications, start=1):
        lines.append(
            f"{index}. {_loan_type_label(app.get('loan_type'))} | {app.get('status')} | "
            f"{_safe_text(app.get('application_id'))[:8]} | {app.get('workflow_stage')}"
        )
    return "\n".join(lines)


async def _build_details_options(user_id: str) -> list[Dict[str, Any]]:
    active_loans = await mongodb.loans.find(
        {"user_id": user_id, "status": "ACTIVE"},
        {"_id": 0, "loan_id": 1, "application_id": 1, "loan_type": 1, "status": 1},
    ).to_list(length=50)

    declined_apps = await mongodb.loan_applications.find(
        {"user_id": user_id, "status": {"$in": ["DECLINED", "REJECTED"]}},
        {"_id": 0, "application_id": 1, "loan_type": 1, "status": 1, "rejection_reason": 1},
    ).sort("updated_at", -1).to_list(length=50)

    options: list[Dict[str, Any]] = []
    for loan in active_loans:
        options.append({
            "kind": "active",
            "loan_id": loan.get("loan_id"),
            "application_id": loan.get("application_id"),
            "loan_type": loan.get("loan_type"),
        })

    for app in declined_apps:
        options.append({
            "kind": "declined",
            "application_id": app.get("application_id"),
            "loan_type": app.get("loan_type"),
            "status": app.get("status"),
        })

    return options


async def _format_details_for_option(user_id: str, option: Dict[str, Any]) -> str:
    if option.get("kind") == "active":
        loan_doc = await mongodb.loans.find_one(
            {"user_id": user_id, "loan_id": option.get("loan_id")},
            {"_id": 0},
        )
        if not loan_doc:
            return "Active loan record not found."

        return (
            f"Active Loan Details\n"
            f"Loan ID: {loan_doc.get('loan_id')}\n"
            f"Loan Type: {_loan_type_label(loan_doc.get('loan_type'))}\n"
            f"Principal: ₹{float(loan_doc.get('principal') or 0):,.2f}\n"
            f"Interest Rate: {float(loan_doc.get('interest_rate') or 0):.2f}% p.a.\n"
            f"EMI: ₹{float(loan_doc.get('monthly_emi') or 0):,.2f}\n"
            f"Tenure: {int(loan_doc.get('tenure_months') or 0)} months\n"
            f"Disbursed: ₹{float(loan_doc.get('disbursement_amount') or 0):,.2f}\n"
            f"Disbursement Date: {loan_doc.get('disbursement_date')}"
        )

    app_doc = await mongodb.loan_applications.find_one(
        {"user_id": user_id, "application_id": option.get("application_id")},
        {"_id": 0},
    )
    if not app_doc:
        return "Declined application record not found."

    requested_amount = ((app_doc.get("application_data") or {}).get("requested_amount") or 0)
    return (
        f"Declined Application Details\n"
        f"Application ID: {app_doc.get('application_id')}\n"
        f"Loan Type: {_loan_type_label(app_doc.get('loan_type'))}\n"
        f"Status: {app_doc.get('status')}\n"
        f"Requested Amount: ₹{float(requested_amount):,.2f}\n"
        f"Reason: {app_doc.get('rejection_reason') or 'Not provided'}\n"
        f"Last Stage: {app_doc.get('workflow_stage')}"
    )


async def _find_latest_sanction_for_user(user_id: str) -> Dict[str, Any]:
    return await mongodb.loan_applications.find_one(
        {
            "user_id": user_id,
            "status": "APPROVED",
            "sanction_letter_path": {"$exists": True, "$ne": None},
        },
        {
            "_id": 0,
            "application_id": 1,
            "loan_id": 1,
            "loan_type": 1,
            "sanction_letter_path": 1,
            "updated_at": 1,
        },
        sort=[("updated_at", -1)],
    ) or {}


async def _find_or_create_application(
    user: UserResponse,
    loan_type: Optional[str],
    force_new: bool,
    telegram_context: Dict[str, Any],
) -> Dict[str, Any]:
    if not force_new:
        existing = await mongodb.loan_applications.find_one(
            {"user_id": user.user_id, "status": "IN_PROGRESS"},
            sort=[("updated_at", -1)],
        )
        if existing:
            return existing

    normalized_loan_type = _resolve_loan_type(loan_type)
    application_id = secrets.token_hex(16)

    initial_state = _build_initial_state(
        application_id=application_id,
        user_id=user.user_id,
        loan_type=normalized_loan_type,
        user_email=user.email,
    )
    result_state = run_workflow_stepwise(initial_state)

    now = datetime.now().isoformat()
    app_doc = {
        "application_id": application_id,
        "user_id": user.user_id,
        "loan_type": normalized_loan_type,
        "status": "IN_PROGRESS",
        "owner_email": user.email,
        "workflow_stage": result_state["stage"],
        "application_data": result_state["application_data"],
        "conversation_messages": result_state["messages"],
        "progress": _build_pipeline_progress(result_state, "IN_PROGRESS"),
        "is_eligible": result_state["is_eligible"],
        "is_accepted": result_state["is_accepted"],
        "created_at": result_state.get("created_at") or now,
        "updated_at": now,
        "source_channel": "telegram",
        "channel_metadata": telegram_context,
    }

    await mongodb.loan_applications.insert_one(app_doc)
    return app_doc


@router.get("/link-status")
async def get_telegram_link_status(current_user: UserResponse = Depends(get_current_user)):
    link_doc = await mongodb.telegram_links.find_one(
        {"user_id": current_user.user_id, "is_active": True},
        sort=[("updated_at", -1)],
    )

    if not link_doc:
        return {"linked": False}

    return {
        "linked": True,
        "chat_id": _safe_text(link_doc.get("telegram_chat_id")),
        "telegram_username": link_doc.get("telegram_username"),
        "linked_at": link_doc.get("linked_at"),
        "updated_at": link_doc.get("updated_at"),
    }


@router.post("/link-token")
async def create_telegram_link_token(current_user: UserResponse = Depends(get_current_user)):
    if not settings.TELEGRAM_BOT_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram bot is not configured on the server",
        )

    code = secrets.token_urlsafe(12).replace("-", "").replace("_", "")[:16]
    code_key = f"telegram:link:{code}"
    now = datetime.utcnow()
    expires_at = now + timedelta(seconds=settings.TELEGRAM_LINK_CODE_TTL_SECONDS)

    await redis_client.client.setex(
        code_key,
        settings.TELEGRAM_LINK_CODE_TTL_SECONDS,
        current_user.user_id,
    )

    await mongodb.telegram_link_codes.update_one(
        {"code": code},
        {
            "$set": {
                "code": code,
                "user_id": current_user.user_id,
                "expires_at": expires_at,
                "is_consumed": False,
                "updated_at": now,
            },
            "$setOnInsert": {
                "created_at": now,
            },
        },
        upsert=True,
    )

    bot_username = _safe_text(settings.TELEGRAM_BOT_USERNAME)
    deep_link = (
        f"https://t.me/{bot_username}?start=link_{code}"
        if bot_username
        else None
    )

    return {
        "code": code,
        "expires_in_seconds": settings.TELEGRAM_LINK_CODE_TTL_SECONDS,
        "bot_username": bot_username or None,
        "command": f"/link {code}",
        "deep_link": deep_link,
    }


@router.post("/unlink")
async def unlink_telegram_account(current_user: UserResponse = Depends(get_current_user)):
    result = await mongodb.telegram_links.update_many(
        {"user_id": current_user.user_id, "is_active": True},
        {
            "$set": {
                "is_active": False,
                "updated_at": datetime.now().isoformat(),
                "unlinked_at": datetime.now().isoformat(),
            }
        },
    )

    return {
        "success": True,
        "unlinked_count": result.modified_count,
    }


@router.post("/webhook")
async def handle_telegram_webhook(
    payload: Dict[str, Any],
    x_telegram_bot_api_secret_token: Optional[str] = Header(default=None),
):
    if not settings.TELEGRAM_BOT_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram bot is not configured",
        )

    if settings.TELEGRAM_WEBHOOK_SECRET:
        if x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook secret")

    message = payload.get("message") or payload.get("edited_message")
    if not message:
        return {"ok": True, "ignored": "no_message"}

    text = _safe_text(message.get("text"))
    if not text:
        return {"ok": True, "ignored": "non_text_message"}

    chat = message.get("chat") or {}
    sender = message.get("from") or {}
    telegram_chat_id = _safe_text(chat.get("id"))
    telegram_user_id = _safe_text(sender.get("id"))

    telegram_context = {
        "telegram_chat_id": telegram_chat_id,
        "telegram_user_id": telegram_user_id,
        "telegram_username": sender.get("username"),
        "telegram_first_name": sender.get("first_name"),
        "telegram_last_name": sender.get("last_name"),
        "last_message_id": message.get("message_id"),
        "last_message_at": message.get("date"),
    }

    link_doc = await mongodb.telegram_links.find_one(
        {"telegram_chat_id": telegram_chat_id, "is_active": True}
    )
    session_doc = await _get_telegram_session(telegram_chat_id)

    if text.startswith("/start"):
        start_arg = _extract_start_argument(text)
        if start_arg.startswith("link_"):
            text = f"/link {start_arg.replace('link_', '', 1)}"
        elif link_doc:
            await _send_telegram_message(
                telegram_chat_id,
                "You are already linked. Send your loan details to continue, or use /new personal|home|business.",
                reply_markup=_main_menu_reply_markup(),
            )
            return {"ok": True, "handled": "start_linked"}
        else:
            await _send_telegram_message(
                telegram_chat_id,
                "Welcome to NBFC Loan Assistant. Generate a link code in dashboard and send /link <code> here.",
                reply_markup=_main_menu_reply_markup(),
            )
            return {"ok": True, "handled": "start_unlinked"}

    if text.startswith("/help"):
        await _send_telegram_message(
            telegram_chat_id,
            (
                "NBFC Loan Assistant Commands\n\n"
                "Authentication & Linking:\n"
                "• /auth - Login via email + OTP in chat\n"
                "• /link <code> - Link Telegram with dashboard-generated code\n"
                "• /unlink - Unlink this Telegram chat\n\n"
                "Loan Journey:\n"
                "• /new personal|home|business - Start a new application\n"
                "• /apply personal|home|business - Same as /new\n"
                "• /status - Show your latest active application status\n"
                "• /history - Show recent application history\n"
                "• /details - List active + declined loans and choose a number for details\n"
                "• /sanction - Re-send your latest sanction letter PDF\n\n"
                "General:\n"
                "• /start - Welcome and quick onboarding\n"
                "• /help - Show this command list"
            ),
            reply_markup=_main_menu_reply_markup(),
        )
        return {"ok": True, "handled": "help"}

    if text.startswith("/link"):
        parts = text.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            await _send_telegram_message(telegram_chat_id, "Usage: /link <code>")
            return {"ok": True, "handled": "link_missing_code"}

        code = parts[1].strip()
        code_key = f"telegram:link:{code}"
        user_id = await redis_client.client.get(code_key)

        code_doc = None
        if not user_id:
            code_doc = await mongodb.telegram_link_codes.find_one(
                {
                    "code": code,
                    "is_consumed": False,
                    "expires_at": {"$gte": datetime.utcnow()},
                }
            )
            if code_doc:
                user_id = _safe_text(code_doc.get("user_id"))

        if not user_id:
            await _send_telegram_message(
                telegram_chat_id,
                "Invalid or expired link code. Generate a fresh code from dashboard.",
            )
            return {"ok": True, "handled": "link_invalid"}

        user_doc = await _get_user_by_id(_safe_text(user_id))
        if not user_doc:
            await _send_telegram_message(
                telegram_chat_id,
                "Linked user account no longer exists. Please login again and generate a new code.",
            )
            return {"ok": True, "handled": "link_user_missing"}

        await _link_chat_to_user(
            telegram_chat_id=telegram_chat_id,
            telegram_user_id=telegram_user_id,
            sender=sender,
            user_doc=user_doc,
        )

        await redis_client.client.delete(code_key)
        await mongodb.telegram_link_codes.update_one(
            {"code": code},
            {
                "$set": {
                    "is_consumed": True,
                    "consumed_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }
            },
            upsert=False,
        )
        await _reset_telegram_session(telegram_chat_id)

        await _send_telegram_message(
            telegram_chat_id,
            (
                f"Linked successfully to {user_doc['email']}. "
                "Use /new personal|home|business to start, or send loan details directly."
            ),
            reply_markup=_main_menu_reply_markup(),
        )
        return {"ok": True, "handled": "link_success"}

    if text.startswith("/auth"):
        await _set_telegram_session(
            telegram_chat_id,
            {
                "flow": "otp_auth",
                "step": "await_email",
                "email": None,
                "details_options": [],
            },
        )
        await _send_telegram_message(
            telegram_chat_id,
            "Please enter your email id for OTP login.",
        )
        return {"ok": True, "handled": "auth_await_email"}

    if session_doc.get("flow") == "otp_auth" and session_doc.get("step") == "await_email":
        if text.startswith("/"):
            await _send_telegram_message(
                telegram_chat_id,
                "Send your email id to continue OTP login, or use /auth to restart.",
            )
            return {"ok": True, "handled": "auth_email_expected"}

        email = text.lower().strip()
        if not _is_valid_email(email):
            await _send_telegram_message(
                telegram_chat_id,
                "Invalid email format. Please enter a valid email id.",
            )
            return {"ok": True, "handled": "auth_email_invalid"}

        otp_result = await otp_service.create_and_store_otp(email)
        note = (
            "OTP sent to your email."
            if otp_result.get("email_sent")
            else (otp_result.get("fallback_reason") or "OTP available in backend logs for development mode.")
        )

        await _set_telegram_session(
            telegram_chat_id,
            {
                "flow": "otp_auth",
                "step": "await_otp",
                "email": email,
            },
        )
        await _send_telegram_message(
            telegram_chat_id,
            f"{note}\nPlease enter the 6-digit OTP.",
        )
        return {"ok": True, "handled": "auth_await_otp"}

    if session_doc.get("flow") == "otp_auth" and session_doc.get("step") == "await_otp":
        otp = text.strip()
        if text.startswith("/"):
            await _send_telegram_message(
                telegram_chat_id,
                "Enter the 6-digit OTP sent to your email, or use /auth to restart.",
            )
            return {"ok": True, "handled": "auth_otp_expected"}

        if not _is_valid_otp(otp):
            await _send_telegram_message(
                telegram_chat_id,
                "Invalid OTP format. OTP must be 6 digits.",
            )
            return {"ok": True, "handled": "auth_otp_invalid_format"}

        email = _safe_text(session_doc.get("email")).lower()
        success, error_message = await otp_service.verify_otp(email, otp)
        if not success:
            await _send_telegram_message(
                telegram_chat_id,
                error_message or "OTP verification failed. Use /auth to try again.",
            )
            return {"ok": True, "handled": "auth_otp_failed"}

        user_doc = await _get_or_create_user_by_email(email)
        await _link_chat_to_user(
            telegram_chat_id=telegram_chat_id,
            telegram_user_id=telegram_user_id,
            sender=sender,
            user_doc=user_doc,
        )
        await _reset_telegram_session(telegram_chat_id)
        await _send_telegram_message(
            telegram_chat_id,
            (
                f"Authenticated and linked successfully to {user_doc['email']}. "
                "Use /new personal|home|business to start your loan journey."
            ),
            reply_markup=_main_menu_reply_markup(),
        )
        return {"ok": True, "handled": "auth_success"}

    if not link_doc:
        await _send_telegram_message(
            telegram_chat_id,
            "This chat is not linked yet. Generate code in dashboard, then send /link <code>.",
        )
        return {"ok": True, "handled": "not_linked"}

    user_doc = await _get_user_by_id(_safe_text(link_doc.get("user_id")))
    if not user_doc:
        await mongodb.telegram_links.update_one(
            {"_id": link_doc["_id"]},
            {"$set": {"is_active": False, "updated_at": datetime.now().isoformat()}},
        )
        await _send_telegram_message(
            telegram_chat_id,
            "Linked account not found anymore. Please relink from dashboard.",
        )
        return {"ok": True, "handled": "stale_link"}

    current_user = UserResponse(
        user_id=user_doc["user_id"],
        email=user_doc["email"],
        role=user_doc["role"],
        is_verified=user_doc.get("is_verified", False),
        created_at=user_doc["created_at"],
    )

    await mongodb.telegram_links.update_one(
        {"_id": link_doc["_id"]},
        {
            "$set": {
                "telegram_user_id": telegram_user_id,
                "telegram_username": sender.get("username"),
                "telegram_first_name": sender.get("first_name"),
                "telegram_last_name": sender.get("last_name"),
                "updated_at": datetime.now().isoformat(),
                "last_seen_at": datetime.now().isoformat(),
            }
        },
    )

    if text.startswith("/history"):
        history_text = await _build_history_text(current_user.user_id)
        await _send_telegram_message(telegram_chat_id, history_text)
        return {"ok": True, "handled": "history"}

    if text.startswith("/details"):
        options = await _build_details_options(current_user.user_id)
        if not options:
            await _send_telegram_message(
                telegram_chat_id,
                "No active or declined loans found.",
            )
            return {"ok": True, "handled": "details_empty"}

        lines = ["Choose a number to view details:"]
        for index, option in enumerate(options, start=1):
            if option.get("kind") == "active":
                lines.append(
                    f"{index}. Active | {_loan_type_label(option.get('loan_type'))} | Loan ID: {option.get('loan_id')}"
                )
            else:
                lines.append(
                    f"{index}. Declined | {_loan_type_label(option.get('loan_type'))} | Application: {_safe_text(option.get('application_id'))[:8]}"
                )

        await _set_telegram_session(
            telegram_chat_id,
            {
                "flow": "details",
                "step": "await_selection",
                "details_options": options,
            },
        )
        await _send_telegram_message(telegram_chat_id, "\n".join(lines))
        return {"ok": True, "handled": "details_list"}

    if text.startswith("/sanction"):
        sanction_doc = await _find_latest_sanction_for_user(current_user.user_id)
        sanction_path = sanction_doc.get("sanction_letter_path")
        sanction_loan_id = sanction_doc.get("loan_id")
        if not sanction_path:
            await _send_telegram_message(
                telegram_chat_id,
                "No approved loan with sanction letter found yet.",
            )
            return {"ok": True, "handled": "sanction_missing"}

        sent = await _send_telegram_document(
            chat_id=telegram_chat_id,
            file_path=sanction_path,
            caption=f"Sanction Letter - Loan ID: {sanction_loan_id or 'N/A'}",
        )
        if sent:
            await _send_telegram_message(telegram_chat_id, "Sanction letter sent.")
            return {"ok": True, "handled": "sanction_sent"}

        await _send_telegram_message(
            telegram_chat_id,
            "Could not send sanction letter PDF right now. Please try again later.",
        )
        return {"ok": True, "handled": "sanction_send_failed"}

    if (
        session_doc.get("flow") == "details"
        and session_doc.get("step") == "await_selection"
        and text.strip().isdigit()
    ):
        options = session_doc.get("details_options") or []
        selected_index = int(text.strip())
        if selected_index < 1 or selected_index > len(options):
            await _send_telegram_message(
                telegram_chat_id,
                f"Invalid selection. Choose a number between 1 and {len(options)}.",
            )
            return {"ok": True, "handled": "details_invalid_selection"}

        selected = options[selected_index - 1]
        detail_text = await _format_details_for_option(current_user.user_id, selected)
        await _send_telegram_message(telegram_chat_id, detail_text)
        await _set_telegram_session(
            telegram_chat_id,
            {
                "flow": None,
                "step": None,
                "details_options": [],
            },
        )
        return {"ok": True, "handled": "details_selected"}

    if text.startswith("/unlink"):
        await mongodb.telegram_links.update_one(
            {"_id": link_doc["_id"]},
            {
                "$set": {
                    "is_active": False,
                    "updated_at": datetime.now().isoformat(),
                    "unlinked_at": datetime.now().isoformat(),
                }
            },
        )
        await _send_telegram_message(telegram_chat_id, "Telegram chat unlinked from your account.")
        return {"ok": True, "handled": "unlink"}

    if text.startswith("/status"):
        app_doc = await mongodb.loan_applications.find_one(
            {"user_id": current_user.user_id, "status": "IN_PROGRESS"},
            sort=[("updated_at", -1)],
        )
        if not app_doc:
            await _send_telegram_message(telegram_chat_id, "No active application. Use /new personal|home|business.")
            return {"ok": True, "handled": "status_no_application"}

        await _send_telegram_message(
            telegram_chat_id,
            (
                f"Application: {app_doc.get('application_id')}\n"
                f"Loan Type: {app_doc.get('loan_type')}\n"
                f"Stage: {app_doc.get('workflow_stage')}\n"
                f"Status: {app_doc.get('status')}"
            ),
        )
        return {"ok": True, "handled": "status"}

    force_new = False
    requested_loan_type: Optional[str] = None

    if text.startswith("/new") or text.startswith("/apply"):
        force_new = True
        parts = text.split(maxsplit=1)
        requested_loan_type = parts[1].strip() if len(parts) > 1 else "personal"
        app_doc = await _find_or_create_application(
            user=current_user,
            loan_type=requested_loan_type,
            force_new=force_new,
            telegram_context=telegram_context,
        )
        await _send_telegram_message(
            telegram_chat_id,
            (
                f"Started {app_doc['loan_type']} application: {app_doc['application_id']}. "
                "Now share details like Aadhaar, PAN, income, amount, tenure, age, employment, city tier."
            ),
        )
        return {"ok": True, "handled": "new_application"}

    app_doc = await _find_or_create_application(
        user=current_user,
        loan_type=None,
        force_new=False,
        telegram_context=telegram_context,
    )

    response = await chat_with_workflow(
        application_id=app_doc["application_id"],
        chat_message=ChatMessage(
            message=text,
            metadata={
                "channel": "telegram",
                **telegram_context,
            },
        ),
        current_user=current_user,
    )

    await mongodb.loan_applications.update_one(
        {"application_id": app_doc["application_id"], "user_id": current_user.user_id},
        {
            "$set": {
                "source_channel": "telegram",
                "channel_metadata": telegram_context,
                "updated_at": datetime.now().isoformat(),
            }
        },
    )

    assistant_text = _assistant_reply_from_messages(response.get("messages") or [])

    latest_app_doc = await mongodb.loan_applications.find_one(
        {"application_id": app_doc["application_id"], "user_id": current_user.user_id},
        {
            "_id": 0,
            "application_id": 1,
            "status": 1,
            "loan_id": 1,
            "sanction_letter_path": 1,
            "telegram_notifications": 1,
        },
    )

    if response.get("loan_id"):
        assistant_text = (
            f"{assistant_text}\n\nLoan ID: {response.get('loan_id')}\n"
            f"Dashboard: {settings.TELEGRAM_DASHBOARD_URL}"
        )

    notifications = (latest_app_doc or {}).get("telegram_notifications") or {}
    sanction_sent_at = notifications.get("sanction_sent_at")
    sanction_path = (latest_app_doc or {}).get("sanction_letter_path")
    sanction_loan_id = (latest_app_doc or {}).get("loan_id") or response.get("loan_id")
    sanction_should_send = (
        bool(sanction_path)
        and bool(sanction_loan_id)
        and (latest_app_doc or {}).get("status") == "APPROVED"
        and not sanction_sent_at
    )

    if sanction_should_send:
        sent = await _send_telegram_document(
            chat_id=telegram_chat_id,
            file_path=sanction_path,
            caption=f"Sanction Letter - Loan ID: {sanction_loan_id}",
        )
        if sent:
            await mongodb.loan_applications.update_one(
                {"application_id": app_doc["application_id"], "user_id": current_user.user_id},
                {
                    "$set": {
                        "telegram_notifications.sanction_sent_at": datetime.utcnow().isoformat(),
                        "telegram_notifications.sanction_sent_chat_id": telegram_chat_id,
                    }
                },
            )
            assistant_text = f"{assistant_text}\n\nSanction letter PDF has been sent in this chat."
        else:
            assistant_text = (
                f"{assistant_text}\n\nLoan approved, but PDF could not be attached right now. "
                "Use dashboard to download it."
            )

    await _send_telegram_message(telegram_chat_id, assistant_text)

    return {
        "ok": True,
        "handled": "chat_processed",
        "application_id": app_doc["application_id"],
        "stage": response.get("stage"),
        "status": response.get("status"),
    }
