from __future__ import annotations

import time
from typing import Dict, List
from uuid import UUID

import uvicorn
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
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

num_calls_executed = 0

mcp = FastMCP("Non-Idempotent Payments Demo")


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


@mcp.tool()
def make_payment(
    account_uid: UUID, IBAN: str, BIC: str, amountInMinorUnits: int, currency: str
) -> Dict[str, str]:
    """
    Deliberately *non*-idempotent payment tool.

    - On even-numbered calls (0, 2, 4...), it debits the account and then sleeps long enough
      that a typical HTTP client with a short timeout will give up, even
      though the payment has been applied on the server.
    - On odd-numbered calls (1, 3, 5...), it debits the account again without delay,
      causing the payment to be duplicated.
    """

    global accounts, num_calls_executed

    if account_uid not in accounts:
        raise ToolError(f"Account {account_uid} not found")

    current_balance = accounts[account_uid]["balance_minor_units"]
    if current_balance - amountInMinorUnits < 0:
        raise ValueError(
            f"Insufficient funds: balance {current_balance} cannot cover payment of {amountInMinorUnits}"
        )

    accounts[account_uid]["balance_minor_units"] -= amountInMinorUnits
    accounts[account_uid]["transactions"].append(
        {
            "IBAN": IBAN,
            "BIC": BIC,
            "amountMinorUnits": amountInMinorUnits,
            "currency": currency,
        }
    )

    if num_calls_executed % 2 == 0:
        time.sleep(5)

    num_calls_executed += 1

    return {
        "status": "processed",
        "note": "This server is intentionally non-idempotent and will charge twice on retry.",
    }


if __name__ == "__main__":
    app = mcp.http_app()
    uvicorn.run(app, host="127.0.0.1", port=8000)
