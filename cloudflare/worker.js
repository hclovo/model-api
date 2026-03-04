/**
 * Cloudflare Worker — 多 API 反向代理
 *
 * 路由规则：
 *   /google/*  → https://generativelanguage.googleapis.com/*
 *   /openai/*  → https://api.openai.com/*
 *
 * 部署步骤：
 *   1. 登录 Cloudflare Dashboard → Workers & Pages → Create Worker
 *   2. 将本文件内容粘贴进去，保存并部署
 *   3. 将 Worker URL 填入 .env 的 CLOUDFLARE_PROXY_URL
 *
 * 可选：绑定自定义域名以获得更稳定的访问地址。
 */

const UPSTREAM_MAP = {
  "/google": "https://generativelanguage.googleapis.com",
  "/openai": "https://api.openai.com",
};

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const pathname = url.pathname;

    // 找到匹配的前缀
    let upstreamBase = null;
    let stripPrefix = "";
    for (const [prefix, upstream] of Object.entries(UPSTREAM_MAP)) {
      if (pathname.startsWith(prefix)) {
        upstreamBase = upstream;
        stripPrefix = prefix;
        break;
      }
    }

    if (!upstreamBase) {
      return new Response(
        JSON.stringify({ error: "Unknown proxy path: " + pathname }),
        { status: 404, headers: { "Content-Type": "application/json" } }
      );
    }

    // 重写 URL：去掉前缀，拼接到上游地址
    const upstreamPath = pathname.slice(stripPrefix.length) || "/";
    const upstreamUrl = new URL(upstreamPath + url.search, upstreamBase);

    // 克隆请求头，移除 Host 避免上游拒绝
    const headers = new Headers(request.headers);
    headers.delete("host");

    const upstreamRequest = new Request(upstreamUrl.toString(), {
      method: request.method,
      headers,
      body: request.body,
      redirect: "follow",
    });

    try {
      const response = await fetch(upstreamRequest);

      // 将上游响应透传，并加上 CORS 头
      const responseHeaders = new Headers(response.headers);
      responseHeaders.set("Access-Control-Allow-Origin", "*");
      responseHeaders.set("Access-Control-Allow-Methods", "*");
      responseHeaders.set("Access-Control-Allow-Headers", "*");

      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: responseHeaders,
      });
    } catch (err) {
      return new Response(
        JSON.stringify({ error: "Upstream fetch failed", detail: String(err) }),
        { status: 502, headers: { "Content-Type": "application/json" } }
      );
    }
  },
};
