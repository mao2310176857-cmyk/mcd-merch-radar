# MCP 集成说明 (MCP_INTEGRATION.md)

本文件说明「麦麦周边雷达」实际使用的麦当劳 MCP Server、调用的 Tool、调用流程与业务价值，供赛事核验。

---

## 1. 使用的 MCP Server

| 项目 | 内容 |
| --- | --- |
| 服务方 | 麦当劳中国官方 (GitHub: `M-China` / `M-China-Official`) |
| Server 名称 | `mcd-mcp` |
| 传输协议 | Streamable HTTP (`streamablehttp`) |
| 接入地址 | `https://mcp.mcd.cn` |
| 鉴权方式 | `Authorization: Bearer <MCP_TOKEN>`（Token 通过环境变量 `MCD_MCP_TOKEN` 传入，不落盘） |
| 协议版本 | `2025-06-18` |
| 会话机制 | 首次 `initialize` 后服务端返回 `Mcp-Session-Id`，后续请求需在请求头回传 |

> 本 Skill 使用官方公布的同一接入方式，与 WorkBuddy 连接器里的手动配置完全一致。

---

## 2. 实际调用的 Tool（全部为只读查询类）

麦当劳 MCP 共约 35 个工具，本 Skill **仅使用以下 6 个只读工具**，刻意避开所有下单 / 交易类工具：

| Tool 名称 | 用途 | 在 Skill 中的作用 |
| --- | --- | --- |
| `campaign-calendar` | 活动日历 | 核心数据源。解析出未来 / 在跑的周边、联名、限定活动，提取开售时间与加价门槛 |
| `available-coupons` | 可领取优惠券列表 | 找出用户**尚未领取**的券，作为"摊薄门槛"的弹药 |
| `query-my-coupons` | 我的优惠券 | 与可领列表比对，排除已领，得到"未领券"清单 |
| `query-my-account` | 我的积分账户 | 输出可用 / 累计 / 本月 & 下月将过期积分，支撑"积分体检" |
| `mall-points-products` | 积分商城商品 | 校验"商城内是否在售周边"，印证"周边主要走活动加价"的判断 |
| `query-lottery-info` | 积分抽奖信息 | 结合可用积分，算出"当前能抽几次奖" |

### 明确不调用的工具（安全红线）

以下工具涉及真实交易 / 下单，**本 Skill 一律不调用**：

- `mall-create-order`（积分商城下单）
- `party-order-create`（主题活动下单）
- `create-order`（通用下单）
- 任何写操作类工具（领券、抽奖、兑换等）

所有购买与兑换决策均由用户自行在麦当劳官方渠道完成。

---

## 3. 调用流程

```
initialize ──► notifications/initialized ──► (建立 Mcp-Session-Id)
   │
   ├─ campaign-calendar      ─┐
   ├─ available-coupons      ─┤
   ├─ query-my-coupons       ─┤  并行/顺序调用 6 个只读工具
   ├─ query-my-account       ─┤
   ├─ mall-points-products   ─┤
   └─ query-lottery-info     ─┘
        │
        ▼
   解析原始响应（MCP 包装层在每个文本块前附字段说明，
   真实 JSON 紧接 "## Original Response" 之后；
   用 json.JSONDecoder.raw_decode 精确剥离）
        │
        ▼
   业务加工：活动去重（同活动在多个日期下重复）+
            过滤「往期回顾」+ 周边关键词命中 +
            未领券与即将开售周边自动配对
        │
        ▼
   输出《本周情报》（Markdown / JSON）
```

### 关键解析难点（实测踩坑，已修复）

1. **MCP 包装层干扰**：每个工具返回的文本块前都带一大段字段说明，真正的 JSON 在
   `## Original Response` 之后。用 `raw_decode` 从首个 `{` 精确解析，避免正则贪婪误吞。
2. **优惠券标题末尾的 Markdown 硬回车 `\`**：不是真换行，需用 `rstrip("\\")` 剥离，否则 6 张券会被识别成 0 张。
3. **活动日历重复与往期**：同一活动在多个日期标题下重复出现，且含"往期回顾"区块，
   按 `(活动标题, 开售时间)` 去重并过滤过期区块。

---

## 4. 业务价值

- **把被动变主动**：MCP 本身是"你问我答"，本 Skill 通过"定时跑脚本 + 比对活动日历"模拟"第一时间通知"，
  解决用户"周边上新了却不知道"的核心痛点。
- **把痛点变省钱**：揭示"周边 = 任意餐品消费 + 加价"的真实模式，并把用户**没领的券**与**即将开售的周边**
  自动配对，直接给出"先领哪几张再下单"的行动清单，把"没领券错过优惠"的遗憾变成可执行动作。
- **安全可复现**：纯标准库、零依赖、只读、Token 不落盘，任何人均可在本地复现真实结果。

---

## 5. 复现方式

```bash
export MCD_MCP_TOKEN="你的麦当劳MCP_TOKEN"
python scripts/briefing.py            # 终端打印 Markdown 情报
python scripts/briefing.py --json     # 结构化 JSON
```

核心实现见 `scripts/mcd_client.py`（客户端）与 `scripts/briefing.py`（情报生成）。
