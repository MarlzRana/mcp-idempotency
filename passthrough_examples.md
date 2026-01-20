# Passthrough Options for Idempotency Key in MCP

## 1. Pass through the idempotency key in the `_meta` object (Reserve `idempotencyKey` property)

### CallToolRequest Example (JSON-RPC)

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "make_payment",
    "arguments": {
      "IBAN": "...",
      "BIC": "...",
      "minorUnits": 2500,
      "currency": "EUR"
    },
    "_meta": {
      "idempotencyKey": "73c2eaf4-8cc4-4ba4-908f-7017f0aa2f4f"
    }
  }
}
```

## 2. Introduce a new attribute to CallToolRequest called `idempotencyKey`

### CallToolRequest Example (JSON-RPC)

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "make_payment",
    "arguments": {
      "IBAN": "...",
      "BIC": "...",
      "minorUnits": 2500,
      "currency": "EUR"
    },
    "idempotencyKey": "73c2eaf4-8cc4-4ba4-908f-7017f0aa2f4f"
  }
}
```

## 3. Add a special mark like `x-idempotency-key` to existing parameters

### Tool Definition Input Schema Example (with x-idempotency-key annotation)

```json
{
  "inputSchema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "IBAN": { "type": "string" },
      "BIC": { "type": "string" },
      "minorUnits": { "type": "integer" },
      "currency": { "type": "string" },
      "transferUid": {
        "type": "string",
        "x-idempotency-key": true
      }
    },
    "required": ["IBAN", "BIC", "minorUnits", "currency", "transferUid"]
  }
}
```
