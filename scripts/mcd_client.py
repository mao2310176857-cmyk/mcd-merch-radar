"""麦麦周边雷达 — McDonald's China MCP client (Streamable HTTP)."""
import json
import re
import urllib.request

ENDPOINT = "https://mcp.mcd.cn"


class McdClient:
    """Minimal MCP client for the McDonald's China remote MCP server."""

    def __init__(self, token, endpoint=ENDPOINT, timeout=90):
        self.token = token
        self.endpoint = endpoint
        self.timeout = timeout
        self._sid = None
        self._seq = 0

    def _rpc(self, method, params=None, notify=False):
        self._seq += 1
        payload = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        if not notify:
            payload["id"] = self._seq

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._sid:
            headers["Mcp-Session-Id"] = self._sid

        req = urllib.request.Request(
            self.endpoint, data=json.dumps(payload).encode(),
            headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            got = resp.headers.get("Mcp-Session-Id")
            if got:
                self._sid = got
            raw = resp.read().decode("utf-8", "replace")

        for line in raw.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                line = line[5:].strip()
            if line.startswith("{"):
                try:
                    return json.loads(line)
                except ValueError:
                    continue
        return None

    def connect(self):
        self._rpc("initialize", {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "mcd-merch-radar", "version": "1.0.0"},
        })
        self._rpc("notifications/initialized", {}, notify=True)
        return self

    def list_tools(self):
        res = self._rpc("tools/list") or {}
        return (res.get("result") or {}).get("tools", [])

    def call(self, name, args=None):
        """Call a tool and return the decoded upstream payload.

        The MCP wrapper prefixes every text block with a field guide; the raw
        JSON payload follows the '## Original Response' marker. Fall back to
        the first balanced object when the marker is absent.
        """
        res = self._rpc("tools/call",
                        {"name": name, "arguments": args or {}}) or {}
        if res.get("error"):
            return {"__rpc_error__": res["error"]}
        block = res.get("result") or {}
        if block.get("isError"):
            return {"__tool_error__": _text(block)}
        text = _text(block)
        return _decode_payload(text)

    def safe(self, name, args=None, default=None):
        """Call a tool and never raise -- briefing output must survive one bad endpoint."""
        try:
            out = self.call(name, args)
        except Exception as exc:  # noqa: BLE001
            return {"__error__": f"{type(exc).__name__}: {exc}"} if default is None else default
        if isinstance(out, dict) and ("__error__" in out or "__tool_error__" in out):
            return default if default is not None else out
        return out


def _text(block):
    return "".join(c.get("text", "") for c in block.get("content", [])
                   if c.get("type") == "text")


def _decode_payload(text):
    tail = text.split("## Original Response", 1)[-1]
    decoder = json.JSONDecoder()
    for candidate in (tail, text):
        idx = candidate.find("{")
        if idx < 0:
            continue
        try:
            obj, _ = decoder.raw_decode(candidate[idx:])
            return obj
        except ValueError:
            continue
    return {"__raw__": text}


def parse_coupon_cards(text):
    """Extract coupon titles + claim state from the markdown coupon payload.

    Titles end with a Markdown hard-break backslash (e.g. "中薯条买一送一 \\"),
    which is not a real newline, so strip it explicitly.
    """
    cards = []
    seen = set()
    for block in text.split("- 优惠券标题：")[1:]:
        title = block.split("\n", 1)[0].strip().rstrip("\\").strip()
        if not title or title.startswith("#"):
            continue
        title = re.sub(r"\s+", " ", title)
        if not title or title in seen:
            continue
        seen.add(title)
        cards.append({"title": title,
                      "state": "可领取" if "可领取" in block[:400] else "状态未知"})
    return cards


CAMPAIGN_HEAD = re.compile(r"####\s*(\d{4}年\d{1,2}月\d{1,2}日.*?)\n")
CAMPAIGN_ITEM = re.compile(r"\*\*活动标题\*\*：(.+?)\n(.*?)(?=\n\s*\*\*活动图片|\Z)", re.S)
SALE_TIME = re.compile(r"(\d{1,2})月(\d{1,2})日\s*(\d{1,2}[:：]\d{2})\s*(?:开售|开抢|正式开售|起正式开售|开售)")
PRIORITY = re.compile(r"(\d{1,2}[:：]\d{2})\s*(?:开售|开抢|正式开售|起正式开售|开售)")
PLUS_PRICE = re.compile(r"加\s*(\d+(?:\.\d+)?)\s*元")
MERCH_HINTS = ("周边", "联名", "盲盒", "徽章", "棒球帽", "玩具", "礼盒",
               "T恤", "帆布袋", "钥匙扣", "扭蛋", "手办", "鞋", "袜")
