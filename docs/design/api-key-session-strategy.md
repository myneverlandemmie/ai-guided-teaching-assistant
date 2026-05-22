# API Key Session Strategy / API Key 会话级临时使用策略

## Purpose / 文档目的

本文档说明 V0.2 中真实 AI API Key 的推荐处理方式。目标是在支持教师使用自己 API Key 的同时，避免平台承担公共 Token、Token 转售或明文保存 Key 的风险。

## Current State / 当前状态

当前代码只实现 Mock AI 知识主干生成，不调用真实 AI API。当前没有 API Key 输入、保存或调用逻辑。

后续接入真实 API 时，应先实现教师登录和会话级临时 API Key，再接真实 AI 生成。

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

## Recommended V0.2 Approach / V0.2 推荐方案

V0.2 推荐使用“教师登录后，会话级临时 API Key”：

1. 教师登录系统；
2. 教师在页面中临时输入自己的 API Key；
3. 服务端将 API Key 临时保存在内存会话中；
4. 真实 AI 生成请求从当前会话读取 API Key；
5. 教师可以主动清除 API Key；
6. 教师退出登录后 API Key 失效；
7. 服务重启后 API Key 失效。

该方案适合 V0.2 演示 / 部门内试用阶段，降低实现复杂度，也避免明文持久化风险。

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
