## MCP Idempotency Demo (Streamable HTTP, Python)

This repo contains a minimal demo illustrating idempotency in MCP tool calls, using **Python**, the **MCP Python SDK**, and the **Streamable HTTP** transport.

**Note:** The preferred approach is to introduce a new top-level attribute `idempotencyKey` to the CallToolRequest. This makes idempotency explicit and required, not just an optional or ignorable piece of metadata. By making `idempotencyKey` a first-class attribute, it is clear to both clients and servers that idempotency is a core part of the protocol, reducing ambiguity and the risk of accidental omission. However, this demo uses a reserved key in the `_meta` field (`_meta.io.modelcontextprotocol/idempotency-key`) to avoid breaking the current MCP spec. See below for both forms.

### Components

- **`server_non_idempotent.py`**: MCP server with tools:
  - `make_payment(IBAN, BIC, amountMinorUnits, currency)` – _not_ idempotent; on retry it charges again.
  - `get_balance()` – returns `{ "balanceMinorUnits": <int> }`.
  - `get_transactions()` – returns `{ "transactions": [...] }`.
- **`server_idempotent.py`**: Same tools, but `make_payment` uses `_meta.io.modelcontextprotocol/idempotency-key` to be
  idempotent. A retry with the same key does **not** apply the payment
  again.
- **`client.py`**: A single client that:
  1. Calls `get_balance`.
  2. Calls `make_payment` once (the server is slow, so the HTTP client times out).
  3. Retries `make_payment` with the same arguments.
  4. Calls `get_balance` and `get_transactions` again and prints the results.

The client runs this sequence once against the non-idempotent server and once against the
idempotent server so you can directly compare the outcomes.

### Create venv

```bash
uv venv
```

### Install dependencies

```bash
uv install -r requirements.txt
```

### Run the servers (Streamable HTTP)

In one terminal:

```bash
uv run server_non_idempotent.py
```

In another terminal:

```bash
uv run server_idempotent.py
```

Both servers expose an MCP **Streamable HTTP** endpoint that accepts JSON POST requests. This demo uses the reserved key approach for compatibility:

```json
{
  "tool": "make_payment",
  "params": {
    "IBAN": "...",
    "BIC": "...",
    "minorUnits": 2500,
    "currency": "EUR"
  },
  "_meta": {
    "io.modelcontextprotocol/idempotency-key": "73c2eaf4-8cc4-4ba4-908f-7017f0aa2f4f"
  }
}
```

**Preferred (future) approach:**

```json
{
  "tool": "make_payment",
  "params": {
    "IBAN": "...",
    "BIC": "...",
    "minorUnits": 2500,
    "currency": "EUR"
  },
  "idempotencyKey": "73c2eaf4-8cc4-4ba4-908f-7017f0aa2f4f"
}
```

### Run the demo client

With both servers running:

```bash
uv run client.py
```

You should observe:

- **Non-idempotent server**
  - First `make_payment` call: client logs a timeout, but the server has already applied the payment.
  - Second `make_payment` call: server applies the payment _again_ (no idempotency), so
    `get_balance` shows two debits and `get_transactions` contains two matching payments.
- **Idempotent server**
  - First `make_payment` call: client times out, but the server applies the payment once and stores
    the `_meta.io.modelcontextprotocol/idempotency-key`.
  - Second `make_payment` call with the same `_meta.io.modelcontextprotocol/idempotency-key`: the server **does not** apply the payment again, so `get_balance` only shows a single debit and `get_transactions` has a single payment.

This provides a concrete, end-to-end illustration of why idempotency is valuable for safely retrying tools such as payments. While this demo uses a reserved key in `_meta` for compatibility, the recommended approach is to make `idempotencyKey` a first-class attribute in the MCP spec.
