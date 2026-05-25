# API Key Session Strategy / API Key 会话级临时使用策略

## Purpose / 文档目的

本文档说明 V0.2 中真实 AI API Key 的推荐处理方式。目标是在支持教师使用自己 API Key 的同时，避免平台承担公共 Token、Token 转售或明文保存 Key 的风险。

## Current State / 当前状态

当前代码已经实现会话级 API Key 管理和 DeepSeek Provider，并已接入真实知识主干生成。

当前真实 AI 只用于“知识主干生成”。导学案、小测题、SQL 批阅、Python 批阅暂未接入真实 AI。

## Principles / 原则

- 教师使用自己的 API Key；
- 平台不提供公共 Token；
- 平台不做 Token 转售；
- 学生不需要填写 API Key；
- API Key 不应明文入库；
- API Key 不应写入日志；
- API Key 不应提交到 Git；
- API Key 不能只存 hash，因为 hash 无法还原，不能用于真实 API 调用；
- 长期保存 Key 需要另行设计加密存储方案，不在当前阶段实现。

## Implemented V0.2 Approach / V0.2 已实现方案

V0.2 当前使用“会话级临时 API Key”：

1. 浏览器访问 `/ai/settings`；
2. 服务端为浏览器生成 `session_id`；
3. 浏览器 cookie 只保存 `session_id`，不保存 API Key；
4. `session_id` cookie 设置 `HttpOnly` 和 `SameSite=Lax`；
5. 本地开发默认不强制 `Secure`；
6. 公网 HTTPS 部署建议设置 `AI_SESSION_COOKIE_SECURE=true`；
7. 教师在页面中临时输入自己的 DeepSeek API Key；
8. 服务端内存保存 `session_id -> api_key`；
9. 真实知识主干生成从当前会话读取 API Key；
10. 教师可以主动清除 API Key；
11. 服务重启后 API Key 失效；
12. 当前会话 API Key 支持自动过期；
13. 当前会话 API Key 支持容量上限；
14. 清除 Key 时会同步删除临时 session cookie。

该方案适合 V0.2 演示 / 部门内试用阶段，降低实现复杂度，也避免明文持久化风险。后续接入完整登录后，可把会话失效与教师退出登录绑定。

## Expiration and Capacity / 自动过期与容量上限

当前 V0.2 的 session key store 是单进程内存临时方案。已实现：

- `AI_SESSION_KEY_IDLE_TIMEOUT_SECONDS=14400`：当前会话 API Key 默认空闲 4 小时后自动失效；
- `AI_SESSION_KEY_MAX_ENTRIES=200`：默认最多保留 200 个会话 Key；
- 超过容量时，系统先清理已过期 Key；
- 如果仍超限，系统清理最久未使用的 Key；
- 服务重启、手动清除、空闲过期都会使 Key 失效；
- cookie 本身不保存 API Key，只保存临时 `session_id`；
- 清除 Key 会删除临时 session cookie。

该方案适合本地开发、部门内试用和单进程演示。如果使用多 worker / 多实例部署，不同进程之间不会共享 API Key。生产化如需多实例部署，应改用 Redis 等服务端临时存储，并配合加密、过期、轮换和审计机制。

## Same-Origin Protection / 同源提交防护

关键 POST 路由已增加 same-origin 防护：

- `POST /ai/settings`；
- `POST /ai/settings/clear`；
- `POST /lessons/{lesson_id}/knowledge-outline/generate`。

系统会校验 `Origin` 或 `Referer` 是否与当前 `Host` 和 scheme 匹配。公网部署必须使用 HTTPS，并建议设置 `AI_SESSION_COOKIE_SECURE=true`。

## Display and Logging / 页面与日志要求

页面只能显示：

- 未设置；
- 已设置；
- `sk-****abcd` 这类掩码。

页面不得回显完整 API Key。日志不得记录 API Key、Authorization header、完整 request headers、完整 cookie 或包含 API Key 的异常调试对象。

## Provider Behavior / Provider 行为

`AI_PROVIDER=deepseek` 是正式默认路径：

- 当前会话没有 API Key 时，阻止真实生成并提示教师先设置 Key；
- 有 API Key 时调用 DeepSeek Provider；
- `generated_by_model` 记录实际模型名，例如 `deepseek-v4-pro` 或 `deepseek-v4-flash`；
- 教师可在 AI 设置页选择当前会话知识主干生成模型；
- 模型选择只保存在服务端内存会话中，不写数据库、不写 cookie、不写日志；
- 清除 API Key 时会同时清除当前会话模型选择；
- `ai_raw_output` 只保存模型返回正文；
- `edited_content` 初始等于模型正文；
- 教师保存后状态变为 `reviewed`。

`AI_PROVIDER=mock` 只用于单元测试或显式本地开发。正式页面不得在缺少 API Key 时静默 fallback 到 Mock。

## DeepSeek Configuration / DeepSeek 配置

推荐配置：

```env
AI_PROVIDER=deepseek
DEEPSEEK_BASE_URL="https://api.deepseek.com"
DEEPSEEK_ALLOWED_MODELS=deepseek-v4-flash,deepseek-v4-pro
DEEPSEEK_DEFAULT_MODEL=deepseek-v4-flash
AI_REQUEST_TIMEOUT_SECONDS=60
AI_SESSION_COOKIE_SECURE=false
AI_SESSION_KEY_IDLE_TIMEOUT_SECONDS=14400
AI_SESSION_KEY_MAX_ENTRIES=200
AI_PROMPT_MATERIAL_MAX_CHARS=12000
```

`DEEPSEEK_ALLOWED_MODELS` 是允许教师在 `/ai/settings` 页面选择的模型列表，逗号分隔。`DEEPSEEK_DEFAULT_MODEL` 是默认模型，必须属于允许列表，否则回退到安全默认模型。

V0.2 当前只允许 `deepseek-v4-flash` 和 `deepseek-v4-pro`。不使用即将废弃的 `deepseek-chat` 或 `deepseek-reasoner`，未知模型不会进入页面选项。如 DeepSeek 官方模型名称变化，应由管理员更新环境变量并重启服务。

`/ai/settings` 页面只显示模型配置说明、建议配置路径和 DeepSeek 官方文档链接，不读取、不打开、不下载、不展示真实 `.env` 文件内容。本地开发通常在项目根目录 `.env` 中配置，示例变量见 `.env.example`；生产部署时建议使用服务器环境变量。

知识主干生成使用固定 Prompt 模板。AI 输出是教师审阅用草稿，不是自动定稿内容。模板包含课程思政与职业素养融入点、可测知识点与题型蓝图、补充内容建议和 AI 草稿声明。课程思政内容必须有依据，严禁编造政策文件、政策原文、标准编号、真实企业案例或真实数据来源。题型蓝图只作为后续小测设计参考，不生成正式测评；补充内容建议仅为参考方向，必须由教师人工筛选、修改和确认。

## Non Goals / 不做内容

V0.2 当前阶段不实现：

- 平台统一公共 API Token；
- API Key 转售；
- API Key 明文数据库存储；
- 仅保存 API Key hash；
- 长期加密保存 Key；
- 多供应商 Key 管理后台；
- 学生侧 API Key 输入。

## Future Option / 后续可选方案

如果后续确需长期保存 API Key，应另行设计：

- 应用层加密；
- 独立密钥管理；
- 密钥轮换；
- 访问审计；
- 管理员不可直接查看明文 Key；
- 日志脱敏；
- 用户主动删除 Key。

该方案不属于当前阶段实现范围。
