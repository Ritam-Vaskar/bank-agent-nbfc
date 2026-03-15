import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from database import mongodb

APP_ID = "bbe62022-29b0-43e6-9375-4c0c3989964f"


async def main():
    await mongodb.connect()
    try:
        doc = await mongodb.loan_applications.find_one({"application_id": APP_ID})
        msgs = [
            m.get("content", "")
            for m in (doc or {}).get("conversation_messages", [])
            if m.get("role") == "assistant"
        ]
        kyc_msgs = [m for m in msgs if "KYC verification completed" in m]
        credit_msgs = [m for m in msgs if "Credit assessment completed" in m]
        print("KYC_MSG_FOUND", bool(kyc_msgs))
        print("CREDIT_MSG_FOUND", bool(credit_msgs))
        if kyc_msgs:
            print("KYC_MSG")
            print(kyc_msgs[-1])
    finally:
        await mongodb.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
