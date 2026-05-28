# Teacher Session API Key and DeepSeek Provider / 教师会话级 API Key 与 DeepSeek Provider 决策

## Status / 状态

Accepted / 已采纳。

## Context / 背景

V0.2 需要从 Mock AI 过渡到可用于案例展示和部门内试用的真实 AI 生成。平台不能提供公共 Token，也不能做 Token 转售。教师应使用自己的 DeepSeek API Key，学生不需要填写 API Key。

## Decision / 决策

第 8 轮采用教师会话级临时 API Key 方案：

- 浏览器 cookie 只保存 `session_id`；
- cookie 不保存 API Key；
- `session_id` cookie 设置 `HttpOnly` 和 `SameSite=Lax`；
- 本地开发默认不强制 `Secure`，公网 HTTPS 部署建议设置 `AI_SESSION_COOKIE_SECURE=true`；
- 服务端内存保存 `session_id -> api_key`；
- API Key 不写入数据库；
- API Key 不写入日志；
- API Key 不提交到 Git；
- API Key 不存 hash，因为 hash 无法还原，不能用于真实 DeepSeek API 调用；
- 教师可在 `/ai/settings` 设置或清除当前会话 Key；
- 服务重启、清除 Key、空闲过期或会话失效后 Key 失效；
- 清除 Key 时删除临时 session cookie；
- session_id 必须校验格式，非法 cookie 不可作为内存 Key 索引；
- 会话 Key 有自动过期和容量上限；
- 关键 POST 路由增加 same-origin 防护。

同时新增 AI Provider 抽象：

- `AI_PROVIDER=deepseek` 为正式默认路径；
- `AI_PROVIDER=mock` 仅用于单元测试或显式本地开发；
- 无 API Key 的演示流程可使用本地结构化草稿，但页面必须明确标注，不得包装成真实 AI 成果；
- DeepSeek 模型选项由 `DEEPSEEK_ALLOWED_MODELS` 配置；
- DeepSeek 默认模型由 `DEEPSEEK_DEFAULT_MODEL` 配置；
- 教师可在 `/ai/settings` 页面选择当前会话使用的知识主干生成模型；
- 模型选择只保存在服务端内存会话中，不写数据库、不写 cookie、不写日志；
- 清除 API Key 时同时清除模型选择；
- 不使用 `deepseek-chat` 或 `deepseek-reasoner`。

没有 API Key 时不能把本地结构化草稿包装成真实 AI 成果。当前为了本地演示稳定，允许无 Key 时生成“本地结构化草稿”；如果教师需要真实 AI 生成质量，应设置自己的 DeepSeek API Key。

## Consequences / 影响

优点：

- 不承担公共 Token 和 Token 转售风险；
- 避免 API Key 明文持久化；
- 适合 V0.2 演示和部门内试用；
- 实现复杂度低，便于教师理解和主动清除。

限制：

- 服务重启后教师需要重新输入 API Key；
- 当前没有长期加密保存 Key；
- 当前没有复杂权限系统；
- 当前真实 AI 只接入知识主干生成，不接入导学案、小测题、SQL 批阅或 Python 批阅。
- 当前内存方案适合单进程演示；多 worker / 多实例部署时，不同进程之间不会共享 API Key。

## Additional Hardening / 第 8.1 轮加固

第 8.1 轮增加以下安全和稳定性措施：

- 增加自动过期，默认 `AI_SESSION_KEY_IDLE_TIMEOUT_SECONDS=14400`；
- 增加容量上限，默认 `AI_SESSION_KEY_MAX_ENTRIES=200`；
- 超限时先清理过期 Key，再清理最久未使用 Key；
- 清除 Key 时删除临时 session cookie，避免旧 session_id 继续复用；
- 校验 session_id 格式，降低 session fixation 风险；
- DeepSeek HTTP 异常不保留可能携带 Authorization header 的 httpx request 异常链；
- DeepSeek 模型列表从环境变量读取，但 V0.2 只允许 `deepseek-v4-flash` / `deepseek-v4-pro`，拒绝 `deepseek-chat`、`deepseek-reasoner` 和未知模型；
- 知识主干生成路由用 threadpool 执行同步 Provider，避免阻塞 async route；
- 生成 prompt 前进行共享脱敏和轻量材料选择。

第 9.0 轮进一步固化知识主干 Prompt 模板：

- 输出是教师审阅用草稿，不是自动定稿内容；
- 模板包含课程思政与职业素养融入点；
- 模板包含可测知识点与题型蓝图，但不生成正式测评；
- 模板包含补充内容建议和 AI 草稿声明；
- 课程思政内容必须有依据，严禁编造政策文件、政策原文、标准编号、真实企业案例或真实数据来源；
- 补充内容建议仅为参考方向，必须由教师人工筛选、修改和确认。

V0.2 暂不做生产级凭据管理。若后续需要生产化多实例部署，应使用 Redis 等服务端临时存储，并配合加密、过期、轮换和审计机制。

## Security Notes / 安全说明

DeepSeek Provider 不保存 Authorization header、完整 request headers、完整 response headers 或包含 API Key 的调试对象。页面只显示“未设置”“已设置”或掩码，例如 `sk-****abcd`。

常见 DeepSeek 错误会转换为教师可理解提示：认证失败、余额不足、限流、超时和服务繁忙。错误提示不得包含 API Key。
