// Token storage and login/refresh flow. Tokens live only in SecureStore, never in JS state/logs.
import * as SecureStore from "expo-secure-store";

const ACCESS_TOKEN_KEY = "twirra_access_token";
const REFRESH_TOKEN_KEY = "twirra_refresh_token";

export async function saveTokens(accessToken, refreshToken) {
  await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, accessToken);
  await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, refreshToken);
}

export async function getAccessToken() {
  return SecureStore.getItemAsync(ACCESS_TOKEN_KEY);
}

export async function getRefreshToken() {
  return SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
}

export async function clearTokens() {
  await SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY);
  await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
}

export async function hasSession() {
  const refreshToken = await getRefreshToken();
  return !!refreshToken;
}

export async function login(apiBaseUrl, username, password) {
  const res = await fetch(`${apiBaseUrl}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    throw new Error("Login failed. Check your credentials.");
  }
  const data = await res.json();
  await saveTokens(data.access_token, data.refresh_token);
}

export async function refreshAccessToken(apiBaseUrl) {
  const refreshToken = await getRefreshToken();
  if (!refreshToken) throw new Error("No refresh token available");

  const res = await fetch(`${apiBaseUrl}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!res.ok) {
    await clearTokens();
    throw new Error("Session expired. Please log in again.");
  }
  const data = await res.json();
  await saveTokens(data.access_token, data.refresh_token);
  return data.access_token;
}
