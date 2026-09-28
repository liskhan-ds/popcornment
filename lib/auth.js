export const COOKIE_NAME = "popcornment_auth";

// 비밀번호로부터 세션 쿠키 값을 만든다. 비밀번호 원문을 쿠키에 그대로 넣지 않기 위해 해시로 변환.
export async function computeAuthToken(password) {
  const enc = new TextEncoder().encode(`popcornment-session:${password}`);
  const digest = await crypto.subtle.digest("SHA-256", enc);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}
