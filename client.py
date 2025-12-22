import asyncio

import httpx
from fastmcp import Client
from fastmcp.client.client import CallToolResult
from mcp.shared.exceptions import McpError

RESET = "\033[0m"
BOLD = "\033[1m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
MAGENTA = "\033[35m"
RED = "\033[31m"


def _pretty_print(message: str, emoji: str = "", color: str = "") -> None:
    """Print a message with optional emoji and color."""
    emoji_str = f"{emoji} " if emoji else ""
    print(f"{color}{emoji_str}{message}{RESET}")


def _pretty_print_result(emoji: str, label: str, result: CallToolResult) -> None:
    """Pretty-print an MCP tool result with color and emojis (jq-style formatting)."""
    import json

    prefix = f"{emoji} {BOLD}{label}{RESET}"
    status_emoji = "❌" if result.is_error else "✅"
    color = RED if result.is_error else GREEN

    try:
        if hasattr(result.data, "__dict__"):
            data_dict = result.data.__dict__
        elif isinstance(result.data, (dict, list)):
            data_dict = result.data
        else:
            data_dict = str(result.data)

        if isinstance(data_dict, (dict, list)):
            formatted_data = json.dumps(data_dict, indent=2, default=str)
            print(f"{prefix}: {status_emoji}")
            print(formatted_data)
        else:
            print(f"{prefix}: {status_emoji} {data_dict}")
    except (TypeError, AttributeError):
        print(f"{prefix}: {status_emoji} {result.data}")


async def run_scenario(server_url: str, use_idempotency_key: bool) -> None:
    """
    Run the demonstration flow against a single MCP server over HTTP:

    1. Call get_balance.
    2. Call make_payment once (wrapped in a short timeout to simulate client timeout).
    3. Retry make_payment with the same arguments (and same idempotency key for the idempotent server).
    4. Call get_balance and get_transactions again to show the effect.
    """

    kind = "idempotent 🔐" if use_idempotency_key else "non-idempotent ⚠️"

    print(f"\n{MAGENTA}{BOLD}{'='*80}{RESET}")
    _pretty_print(f"Demo against {server_url} ({kind})", "🚀", f"{MAGENTA}{BOLD}")
    print(f"{MAGENTA}{BOLD}{'='*80}{RESET}\n")

    account_uid = "b4d8ada9-74a1-4c64-9ba3-a1af8c8307eb"

    async with Client(server_url) as client:
        initial = await client.call_tool("get_balance", {"account_uid": account_uid})
        _pretty_print_result("💰", "Initial balance", initial)

    payment_params = {
        "account_uid": account_uid,
        "IBAN": "DE89370400440532013000",
        "BIC": "COBADEFFXXX",
        "amountInMinorUnits": 25_00,  # 25.00
        "currency": "EUR",
    }

    meta = (
        {"idempotencyKey": "7d17e09d-f4ee-449a-9441-00fcf3d83f76"}
        if use_idempotency_key
        else None
    )

    _pretty_print(
        "Calling make_payment (first attempt, expect timeout)...", "⏱️", YELLOW
    )
    try:
        async with Client(server_url, timeout=2.0) as client:
            result1 = await client.call_tool("make_payment", payment_params, meta=meta)
            _pretty_print("First call returned before timeout.", "⚠️", YELLOW)
            _pretty_print_result("🧾", "First make_payment result", result1)
    except McpError as e:
        is_timeout = isinstance(e, McpError) and "Timed out" in str(e)
        error_type = "timeout" if is_timeout else type(e).__name__
        _pretty_print(
            f"First make_payment had a transport issue: ({error_type}).", "⏳", RED
        )

    _pretty_print("Retrying make_payment with same arguments...", "🔁", CYAN)

    async with Client(server_url, timeout=10.0) as client:
        result2 = await client.call_tool("make_payment", payment_params, meta=meta)
        _pretty_print_result("🧾", "Second make_payment result", result2)

    _pretty_print("Getting final state...", "📊", CYAN)
    async with Client(server_url) as client:
        final_balance = await client.call_tool(
            "get_balance", {"account_uid": account_uid}
        )
        final_txs = await client.call_tool(
            "get_transactions", {"account_uid": account_uid}
        )

        _pretty_print_result("💰", "Final balance", final_balance)
        _pretty_print_result("📜", "Final transactions", final_txs)


async def main() -> None:
    await run_scenario("http://127.0.0.1:8000/mcp", use_idempotency_key=False)
    await run_scenario("http://127.0.0.1:8001/mcp", use_idempotency_key=True)


if __name__ == "__main__":
    asyncio.run(main())
