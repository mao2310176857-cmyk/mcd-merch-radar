"""麦麦周边雷达 — 每周周边机会简报。

用麦当劳 MCP 拉取活动日历、积分账户、可领券、商城周边与积分抽奖，
输出一份带行动指令的《本周周边情报》。

用法:
    python briefing.py --token $MCD_MCP_TOKEN            # 打印简报
    python briefing.py --token $MCD_MCP_TOKEN --json     # 输出结构化 JSON
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcd_client import (  # noqa: E402
    McdClient, parse_coupon_cards, SALE_TIME, PRIORITY,
    PLUS_PRICE, MERCH_HINTS, CAMPAIGN_HEAD, CAMPAIGN_ITEM,
)

STATUS = {1: "仓库中", 2: "上架", 3: "售罄", 4: "已下架", 5: "预热"}
LOYALTY_HINTS = ("积分", "麦享会", "会员")


PAST_MARK = re.compile(r"往期回顾|已结束")


def pick_merch(campaigns):
    """Future merch drops first, then live ones; drop expired retrospectives."""
    live = [c for c in campaigns if not c["is_past"]]
    merch = [c for c in live if c["is_merch"]]
    return merch or [c for c in live if c["mentions_points"]]


def parse_campaigns(raw):
    """Split the campaign-calendar markdown into structured entries."""
    text = raw if isinstance(raw, str) else json.dumps(raw, ensure_ascii=False)
    out = []
    marks = list(CAMPAIGN_HEAD.finditer(text))
    for i, m in enumerate(marks):
        seg_end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        seg = text[m.end():seg_end]
        day = m.group(1).strip()
        for item in CAMPAIGN_ITEM.finditer(seg):
            title = item.group(1).strip()
            body = item.group(2)
            times = SALE_TIME.findall(body)
            priority = PRIORITY.findall(body)
            price = PLUS_PRICE.search(body)
            out.append({
                "date": day,
                "title": title,
                "body": " ".join(body.split()),
                "sale_times": ["%s月%s日 %s" % t for t in times],
                "all_times": priority,
                "plus_price": float(price.group(1)) if price else None,
                "is_merch": any(h in title or h in body for h in MERCH_HINTS),
                "mentions_points": any(h in body for h in LOYALTY_HINTS),
                "is_past": bool(PAST_MARK.search(day)),
            })
    return out


def dedupe_campaigns(campaigns):
    """The calendar repeats a campaign under each date heading; keep the first."""
    seen, out = set(), []
    for c in campaigns:
        key = (c["title"], tuple(c["sale_times"]))
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


def build_briefing(client, now=None):
    now = now or datetime.now()
    today = now.strftime("%Y-%m-%d")

    campaigns_raw = client.safe("campaign-calendar", {})
    account = client.safe("query-my-account", {})
    avail_raw = client.safe("available-coupons", {})
    mine_raw = client.safe("query-my-coupons", {})
    mall = client.safe("mall-points-products", {}) or {}
    lottery = client.safe("query-lottery-info", {})

    campaigns = []
    if isinstance(campaigns_raw, dict):
        cal = campaigns_raw.get("data")
        if isinstance(cal, dict):
            campaigns = parse_campaigns(json.dumps(cal, ensure_ascii=False))
        else:
            campaigns = parse_campaigns(
                campaigns_raw.get("__raw__", json.dumps(campaigns_raw, ensure_ascii=False)))
    campaigns = dedupe_campaigns(campaigns)

    acct = account.get("data", {}) if isinstance(account, dict) else {}
    points = float(acct.get("availablePoint") or 0)

    avail_cards = []
    if isinstance(avail_raw, dict):
        if avail_raw.get("__raw__"):
            avail_cards = parse_coupon_cards(avail_raw["__raw__"])
        elif isinstance(avail_raw.get("data"), list):
            avail_cards = avail_coupon_titles(avail_raw["data"])

    mine_cards = []
    if isinstance(mine_raw, dict):
        if mine_raw.get("__raw__"):
            mine_cards = parse_coupon_cards(mine_raw["__raw__"])
        elif isinstance(mine_raw.get("data"), list):
            mine_cards = [c.get("title") for c in mine_raw["data"] if isinstance(c, dict)]

    unclaimed = [c["title"] for c in avail_cards]
    unclaimed = [t for t in unclaimed if t not in mine_cards]

    items = (mall.get("data") or []) if isinstance(mall, dict) else []
    merch_items = [i for i in items
                   if i.get("catName") in ("玩具", "鞋袜", "配件", "服饰", "生活")]

    lot = lottery.get("data", {}) if isinstance(lottery, dict) else {}
    draw_point = lot.get("drawPoint")

    hot = pick_merch(campaigns)
    return {
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "reference_date": today,
        "account": {
            "points": points,
            "accumulative": float(acct.get("accumulativePoint") or 0),
            "expiring_this_month": float(acct.get("currentMouthExpirePoint") or 0),
            "expiring_next_month": float(acct.get("nextMouthExpirePoint") or 0),
            "expired": float(acct.get("expiredPoint") or 0),
        },
        "merch_campaigns": hot,
        "total_campaigns": len(campaigns),
        "unclaimed_coupons": unclaimed,
        "unclaimed_count": len(unclaimed),
        "owned_coupons": mine_cards,
        "mall_merch": [
            {"name": i.get("spuName"), "points": i.get("point"),
             "status": STATUS.get(i.get("status"), "?"),
             "up": str(i.get("upTime", ""))[:16], "down": str(i.get("downTime", ""))[:16]}
            for i in merch_items],
        "mall_merch_total": len(items),
        "lottery": {"draw_point": draw_point, "active": lot.get("activityStatusText")},
    }


def avail_coupon_titles(data):
    out = []
    for item in data:
        if isinstance(item, dict):
            title = item.get("couponName") or item.get("title") or item.get("name")
            if title:
                out.append({"title": title, "state": item.get("status", "可领取")})
    return out


def render(b):
    acc = b["account"]
    lines = []
    add = lines.append
    add("# 麦麦周边雷达 · 本周情报")
    add("")
    add("> 生成时间 %s（北京时间）" % b["generated_at"])
    add("")

    add("## 一、周边机会")
    if not b["merch_campaigns"]:
        add("本周未监测到周边/联名类上新。")
    else:
        for c in b["merch_campaigns"][:6]:
            add("### %s" % c["title"])
            add("- 活动日期：%s" % c["date"])
            if c["sale_times"]:
                add("- **开售时间：%s**" % "、".join(c["sale_times"]))
            if c["plus_price"]:
                add("- **加价门槛：任意餐品消费 + %s 元**" % c["plus_price"])
            add("")
            add("> %s" % c["body"][:300])
            add("")

    add("## 二、你没领的券（%d 张）" % b["unclaimed_count"])
    if b["unclaimed_coupons"]:
        for t in b["unclaimed_coupons"][:12]:
            add("- %s" % t)
        add("")
        add("买周边要「任意餐品消费 + 加价」，先领券再下单能直接摊薄门槛。")
    else:
        add("- 暂无待领券")
    add("")

    add("## 三、积分账户")
    add("| 指标 | 数值 |")
    add("| --- | --- |")
    add("| 可用积分 | %.1f |" % acc["points"])
    add("| 累计积分 | %.1f |" % acc["accumulative"])
    add("| 本月将过期 | %.1f |" % acc["expiring_this_month"])
    add("| 下月将过期 | %.1f |" % acc["expiring_next_month"])
    add("| 历史已过期 | %.1f |" % acc["expired"])
    if b["lottery"]["draw_point"]:
        try:
            times = int(float(acc["points"]) // float(b["lottery"]["draw_point"]))
            add("")
            add("- 抽奖单次需 %s 积分，当前可抽约 **%d** 次" %
                (b["lottery"]["draw_point"], times))
        except Exception:
            pass
    add("")

    add("## 四、商城周边类目（%d 件）" % b["mall_merch_total"])
    if b["mall_merch"]:
        add("| 商品 | 积分 | 状态 | 兑换窗口 |")
        add("| --- | --- | --- | --- |")
        for m in b["mall_merch"]:
            add("| %s | %s | %s | %s ~ %s |" %
                (m["name"], m["points"], m["status"], m["up"], m["down"]))
    else:
        add("商城内暂无在售周边。周边主要以「活动加价」形式发放，盯活动日历。")
    add("")

    add("## 五、本周行动清单")
    future = [c for c in b["merch_campaigns"] if not c.get("is_past")]
    if future and b["unclaimed_coupons"]:
        for c in future[:3]:
            when = "、".join(c["sale_times"]) or c["date"]
            plus = "（任意餐品消费 + %s 元）" % c["plus_price"] if c["plus_price"] else ""
            add("### 为「%s」做准备" % c["title"])
            add("- 开售：%s%s" % (when, plus))
            add("- 先领下面这 %d 张券，下单时凑满「任意餐品消费」门槛，把券也薅了："
                % min(len(b["unclaimed_coupons"]), 6))
            for t in b["unclaimed_coupons"][:6]:
                add("  - %s" % t)
            add("")
    elif future:
        add("- 有即将开售的周边，但当前无可领券；保持关注，开售前再来一查。")
    else:
        add("- 暂无即将开售的周边需要准备；保持关注活动日历即可。")
    add("")
    add("---")
    add("> 本情报由麦麦周边雷达基于麦当劳 MCP 实时生成，仅供参考；价格 / 供应以官方为准。")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--token", default=os.environ.get("MCD_MCP_TOKEN"))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if not args.token:
        ap.error("需要 --token 或环境变量 MCD_MCP_TOKEN")

    client = McdClient(args.token).connect()
    briefing = build_briefing(client)
    if args.json:
        print(json.dumps(briefing, ensure_ascii=False, indent=2))
    else:
        print(render(briefing))


if __name__ == "__main__":
    main()
