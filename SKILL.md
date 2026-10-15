---
name: mcd-merch-radar
description: 麦麦周边雷达 —— 当有人想第一时间掌握麦当劳中国周边/联名新品的上新情报、担心错过限时活动或没领的优惠券时，使用本 Skill。触发词：麦当劳周边、联名上新、徽章、限定周边、麦麦周边情报、本周有什么麦当劳活动、别错过周边。它会基于麦当劳 MCP 实时拉取活动日历、可领优惠券与积分账户，每周生成一份带行动清单的《周边情报》，并高亮"先领哪几张券再下单最划算"。
---

# 麦麦周边雷达 (McdMerchRadar)

一个聚焦"麦当劳周边上新情报"的轻量 Skill。它不帮你下单、不替你花钱，只做一件事：
**每周主动把"有什么周边机会 + 你还没领的券 + 怎么买更划算"整理成一份可执行的情报。**

## 适用场景

- 用户说"这周麦当劳有什么周边/联名上新吗？"
- 用户担心"上次那个徽章我又没抢到/没领券亏了"
- 用户想"第一时间知道限定周边什么时候开售"

## 工作原理

1. 连接麦当劳中国官方 MCP Server（`https://mcp.mcd.cn`，Streamable HTTP + Bearer Token）。
2. 只读调用 6 个工具：`campaign-calendar`（活动日历）、`available-coupons`（可领券）、
   `query-my-coupons`（我的券）、`query-my-account`（积分账户）、`mall-points-products`（积分商城）、
   `query-lottery-info`（抽奖）。
3. 解析、去重、过滤往期，挑出未来的周边/联名类活动，并把"未领取的券"与"即将开售的周边"自动配对，
   生成《本周情报》。
4. **红线**：本 Skill 绝不调用任何下单类工具（`mall-create-order` / `party-order-create` / `create-order`），
   所有购买决策由用户自己完成。

## 在 WorkBuddy 里怎么用

两种用法，按当前环境任选其一：

**A. 直接运行内置脚本（推荐，确定性最强）**

```bash
cd <skill目录>
export MCD_MCP_TOKEN="你的麦当劳MCP Token"
python scripts/briefing.py            # 打印 Markdown 简报
python scripts/briefing.py --json     # 输出结构化 JSON，便于二次加工
```

**B. 让 WorkBuddy 直接调已挂载的 MCP 工具**
如果连接器里已信任并启用了 `mcd-mcp`，可直接让 AI 调用 `campaign-calendar`、`available-coupons`、
`query-my-account` 等工具，再按 `MCP_INTEGRATION.md` 里的字段说明产出同样的情报。

## 输出示例（节选）

```
# 麦麦周边雷达 · 本周情报
## 一、周边机会
### 麦当劳「我就喜欢」限定主题丝巾
- 活动日期：2026年10月22日
- 开售时间：10月22日 10:45
- 加价门槛：任意餐品消费 + 39.9 元

## 二、你没领的券（6 张）
- 中薯条买一送一 / 人气麦旋风买一送一 / 免费脆薯饼 ...

## 五、本周行动清单
### 为「限定主题丝巾」做准备
- 开售：10月22日 10:45（任意餐品消费 + 39.9 元）
- 先领这 6 张券，下单时凑满「任意餐品消费」门槛，把券也薅了
```

## 文件结构

```
mcd-merch-radar/
├── SKILL.md                 # 本文件
├── README.md                # 项目介绍与安装
├── MCP_INTEGRATION.md       # MCP 集成说明（参赛必交）
├── CONTEST_DECLARATION.md   # 参赛声明（官方原文，不可改动）
├── workbuddy.md             # WorkBuddy 开发上下文（专项奖励核验）
└── scripts/
    ├── mcd_client.py        # 极简麦当劳 MCP 客户端（纯标准库）
    └── briefing.py          # 情报生成主程序
```
