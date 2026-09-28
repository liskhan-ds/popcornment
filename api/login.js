import { COOKIE_NAME, computeAuthToken } from "../lib/auth.js";

export default async function handler(request) {
  if (request.method !== "POST") {
    return new Response("Method Not Allowed", { status: 405 });
  }

  const form = await request.formData();
  const submitted = form.get("password");
  const correct = process.env.SITE_PASSWORD;

  if (!correct || submitted !== correct) {
    return Response.redirect(new URL("/login.html?error=1", request.url), 302);
  }

  const token = await computeAuthToken(correct);
  const secure = new URL(request.url).protocol === "https:" ? "; Secure" : "";
  // 한 번 들어오면 30일 동안 다시 묻지 않는다 (출퇴근길에 매번 입력하지 않도록)
  const authCookie = `${COOKIE_NAME}=${token}; Path=/; Max-Age=2592000; HttpOnly; SameSite=Lax${secure}`;

  return new Response(null, {
    status: 302,
    headers: { "Set-Cookie": authCookie, Location: "/" },
  });
}

export const config = {
  runtime: "edge",
};
