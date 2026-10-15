# WorkBuddy 开发上下文 (workbuddy.md)

本文件记录「麦麦周边雷达」使用 **WorkBuddy**（本次活动官方合作伙伴）进行创意构思、开发与调试的对话上下文，
用于核验是否符合 WorkBuddy 联动活动奖励条件。

---

## 1. 创意构思阶段（WorkBuddy 协助做"选题判断"）

- 用户最初想法：做一个"周边上新通知 + 高亮怎么买更划算"的工具，并希望 B（时机）、C（渠道）、D（凑单）都要。
- WorkBuddy 没有直接照做，而是**先连真实 MCP 拉数据验证想法**，发现三个关键事实：
  1. 积分商城里**当前一件周边都没有**（周边类目仅 3 件且档期全过期）；
  2. 用户积分仅 65.9，而周边最少要 800 积分，**差一个数量级**；
  3. 周边的真实上新信号在 `campaign-calendar`，且模式是"任意餐品消费 + 加价"，而用户**有 6 张券没领**。
- 基于真实数据，WorkBuddy 建议把方向收敛为：**每周主动推送"周边机会 + 未领券提醒"的情报**，
  而非大而全的"省钱总管"。用户认可此为项目亮点，并确定**窄口径**。

> 这一步的价值：避免参赛者"凭空虚构痛点"，用真数据支撑选题，使参赛故事真实可信。

## 2. 开发阶段（WorkBuddy 协助写代码 + 调通 MCP）

- WorkBuddy 帮用户把麦当劳 MCP 配置写进 `~/.workbuddy/mcp.json`（`streamablehttp` + `Bearer` 头）。
- 由于新 MCP 需用户手动"信任 + 重启"才挂载，WorkBuddy 改用**脚本直连**方式先验证接口可用性，
  确认 35 个工具（含文档未写全的 3 个）均可调用。
- 编写 `mcd_client.py`（极简 Streamable HTTP 客户端）与 `briefing.py`（情报生成主程序），
  全部用 Python 标准库，零第三方依赖，便于复现。

## 3. 调试阶段（WorkBuddy 定位并修复真实 Bug）

WorkBuddy 在实测中识别并修复了 3 个数据解析问题：

| 问题 | 症状 | 修复 |
| --- | --- | --- |
| MCP 包装层字段说明里的花括号骗过正则 | 周边列表解析出 0 条 | 按 `## Original Response` 切分 + `json.JSONDecoder.raw_decode` |
| 券名末尾带 Markdown 硬回车 `\` | 6 张券只识别出 0 张 | `rstrip("\\")` |
| 同一活动在多个日期下重复 + 往期区块 | 徽章出现 3 次 | 按 `(标题, 开售时间)` 去重 + 过滤"往期回顾" |

## 4. 交付阶段（WorkBuddy 协助打包参赛要求文件）

WorkBuddy 按赛事要求生成仓库文件：`README.md`、`CONTEST_DECLARATION.md`（官方原文不可改动）、
`MCP_INTEGRATION.md`、`SKILL.md`，并把 Token 改为环境变量读取（符合信息安全声明）。

## 5. 安全约定（WorkBuddy 主动设定的红线）

- 仅使用 6 个只读工具；**绝不调用** `mall-create-order` / `party-order-create` / `create-order` 等下单接口；
- Token 仅通过 `MCD_MCP_TOKEN` 环境变量传入，仓库内不含真实凭证。

---

> 以上过程均由 WorkBuddy 在对话中协助完成，体现"用 AI 高效完成创意构思、开发与调试"的联动活动目标。
