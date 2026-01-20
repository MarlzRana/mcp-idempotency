from __future__ import annotations


import time
from typing import Dict, List, Optional
from uuid import UUID

import uvicorn
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_context
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from typing_extensions import TypedDict


class Transaction(TypedDict):
    IBAN: str
    BIC: str
    amountMinorUnits: int
    currency: str


class Account(TypedDict):
    balance_minor_units: int
    transactions: List[Transaction]


accounts: Dict[UUID, Account] = {
    UUID("b4d8ada9-74a1-4c64-9ba3-a1af8c8307eb"): {
        "balance_minor_units": 100_00,
        "transactions": [],
    },
    UUID("1a57e024-09db-4402-801b-4f75b1a05a8d"): {
        "balance_minor_units": 200_00,
        "transactions": [],
    },
}

processed_keys: set[str] = set()

num_calls_executed = 0

mcp = FastMCP("Idempotent Payments Demo")


@mcp.tool()
def get_balance(account_uid: UUID) -> Dict[str, int]:
    """
    Return the current balance in minor units for the specified account.
    """
    if account_uid not in accounts:
        raise ToolError(f"Account {account_uid} not found")

    return {"balanceMinorUnits": accounts[account_uid]["balance_minor_units"]}


@mcp.tool()
def get_transactions(account_uid: UUID) -> Dict[str, List[Transaction]]:
    """
    Return the list of processed transactions for the specified account.
    """
    if account_uid not in accounts:
        raise ToolError(f"Account {account_uid} not found")

    return {"transactions": accounts[account_uid]["transactions"]}


@mcp.tool(annotations=ToolAnnotations(idempotentHint=True))
def make_payment(
    account_uid: UUID,
    iban: str,
    bic: str,
    amountInMinorUnits: int,
    currency: str,
) -> Dict[str, str]:
    """
    Idempotent payment tool using `_meta.io.modelcontextprotocol/idempotency-key`.

    Uses idempotency keys to prevent duplicate payments:
    - The first request with a new idempotency key will debit the account and record the transaction.
    - Subsequent requests with the same idempotency key will not apply the payment again
      and return an "already_processed" response.

    Note: Even-numbered requests (0, 2, 4...) sleep for 5 seconds to simulate network delays
    that might cause client timeouts, demonstrating why idempotency is important.
    """

    global accounts, processed_keys, num_calls_executed

    if account_uid not in accounts:
        raise ToolError(f"Account {account_uid} not found")

    context = get_context()
    meta = (
        context.request_context.meta.model_dump() if context.request_context else None
    )

    print(meta)
    print(type(meta))

    key_in_meta: Optional[str] = None
    if meta:
        key_in_meta = meta.get("io.modelcontextprotocol/idempotency-key")

    if not key_in_meta:
        raise ToolError(
            "Missing required _meta.io.modelcontextprotocol/idempotency-key for idempotent operation."
        )

    if key_in_meta in processed_keys:
        return {
            "status": "already_processed",
            "message": "Request with this idempotency key has already been processed.",
        }

    current_balance = accounts[account_uid]["balance_minor_units"]
    if current_balance - amountInMinorUnits < 0:
        raise ValueError(
            f"Insufficient funds: balance {current_balance} cannot cover payment of {amountInMinorUnits}"
        )

    accounts[account_uid]["balance_minor_units"] -= amountInMinorUnits
    accounts[account_uid]["transactions"].append(
        {
            "IBAN": iban,
            "BIC": bic,
            "amountMinorUnits": amountInMinorUnits,
            "currency": currency,
        }
    )

    base_response: Dict[str, str] = {
        "status": "processed",
        "message": "Payment applied once with idempotency protection.",
    }

    processed_keys.add(key_in_meta)

    if num_calls_executed % 2 == 0:
        time.sleep(5)

    num_calls_executed += 1

    return base_response


if __name__ == "__main__":
    app = mcp.http_app()
    uvicorn.run(app, host="127.0.0.1", port=8001)
