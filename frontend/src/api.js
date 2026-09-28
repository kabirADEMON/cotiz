const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export function getToken() {
  return localStorage.getItem("token");
}

export function setToken(token) {
  if (token) localStorage.setItem("token", token);
  else localStorage.removeItem("token");
}

function messageErreur(data, status) {
  if (typeof data?.detail === "string") return data.detail;
  if (Array.isArray(data?.detail))
    return data.detail.map((e) => `${e.loc.at(-1)} : ${e.msg.replace(/^Value error, /, "")}`).join(" · ");
  return `Erreur ${status}`;
}

async function request(method, path, body, { form = false } = {}) {
  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let payload;
  if (form) {
    payload = new URLSearchParams(body);
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  const res = await fetch(`${API_URL}${path}`, { method, headers, body: payload });
  if (res.status === 401 && token) {
    setToken(null);
    window.location.href = "/connexion";
  }
  const data = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) throw new Error(messageErreur(data, res.status));
  return data;
}

export const api = {
  get: (path) => request("GET", path),
  post: (path, body) => request("POST", path, body),
  put: (path, body) => request("PUT", path, body),
  patch: (path, body) => request("PATCH", path, body),
  delete: (path) => request("DELETE", path),
  login: (telephone, password) =>
    request("POST", "/auth/login", { username: telephone, password }, { form: true }),
};
