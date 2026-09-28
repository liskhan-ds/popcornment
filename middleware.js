import { COOKIE_NAME, computeAuthToken } from "./lib/auth.js";

// 로그인 페이지와 로그인 API를 제외한 모든 경로(feed.json 포함)는 비밀번호 쿠키가 있어야 접근 가능
export default async function middleware(request) {
  const url = new URL(request.url);

  if (url.pathname === "/login.html" || url.pathname === "/api/login") {
    return;
  }

  const password = process.env.SITE_PASSWORD;
  const expectedToken = password ? await computeAuthToken(password) : null;
  const cookieHeader = request.headers.get("cookie") || "";
  const authed =
    expectedToken != null &&
    cookieHeader
      .split(";")
      .map((c) => c.trim())
      .includes(`${COOKIE_NAME}=${expectedToken}`);

  if (authed) return;

  return Response.redirect(new URL("/login.html", request.url), 302);
}

export const config = {
  runtime: "edge",
};
