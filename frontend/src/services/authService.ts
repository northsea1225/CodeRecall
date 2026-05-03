import { api, refreshApi } from "./api";

export interface AuthResponse {
  access_token: string;
  token_type: string;
  username: string;
  user_id: number;
}

export const login = async (username: string, password: string): Promise<AuthResponse> => {
  const params = new URLSearchParams();
  params.append("username", username);
  params.append("password", password);
  const response = await api.post<AuthResponse>("/auth/token", params, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return response.data;
};

export const register = async (username: string, password: string): Promise<AuthResponse> => {
  const response = await api.post<AuthResponse>("/auth/register", { username, password });
  return response.data;
};

export const getMe = async () => {
  const response = await api.get("/auth/me");
  return response.data;
};

export async function refreshToken(currentToken: string): Promise<AuthResponse> {
  const { data } = await refreshApi.post<AuthResponse>("/auth/refresh", null, {
    headers: { Authorization: `Bearer ${currentToken}` },
  });
  return data;
}

export async function logout(token: string): Promise<void> {
  await refreshApi
    .post("/auth/logout", null, {
      headers: { Authorization: `Bearer ${token}` },
    })
    .catch(() => {
      // Backend logout failures must not block local logout.
    });
}
