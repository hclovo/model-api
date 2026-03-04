/**
 * 此文件已废弃。
 *
 * 原方案使用 Cloudflare Worker 做反向代理，现已升级为直接使用
 * Cloudflare AI Gateway（/compat 端点），统一接入多个 LLM 提供商。
 *
 * 配置方式：
 *   1. 登录 Cloudflare Dashboard → AI Gateway → Create Gateway
 *   2. 复制 /compat 端点 URL
 *   3. 将 URL 填入 .env 的 CF_AIG_BASE_URL
 *   4. 在 AI Gateway → API Tokens 创建 Token，填入 CF_AIG_TOKEN
 *
 * 支持的模型前缀（在模型名前加 provider/ 即可路由）：
 *   google-ai-studio/gemini-*
 *   openai/gpt-*
 *   anthropic/claude-*
 */
