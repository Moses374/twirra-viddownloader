// Wraps the download call with silent access-token refresh on 401.
import * as FileSystem from "expo-file-system/legacy";
import { getAccessToken, refreshAccessToken } from "./auth";

export const API_BASE_URL = "https://twirra.immercel.com";

async function attemptDownload(tweetUrl, accessToken, onProgress) {
  const fileUri = FileSystem.cacheDirectory + `twirra_${Date.now()}.mp4`;
  const endpoint = `${API_BASE_URL}/download?url=${encodeURIComponent(tweetUrl)}`;

  const downloadResumable = FileSystem.createDownloadResumable(
    endpoint,
    fileUri,
    { headers: { Authorization: `Bearer ${accessToken}` } },
    onProgress
  );

  return downloadResumable.downloadAsync();
}

async function extractErrorMessage(result) {
  if (!result) return "Could not reach the server. Check your connection.";
  try {
    const body = await FileSystem.readAsStringAsync(result.uri);
    const parsed = JSON.parse(body);
    if (parsed.detail) return parsed.detail;
  } catch {
    // response wasn't JSON (or file unreadable) — fall through to generic message
  }
  return `Download failed (status ${result.status})`;
}

export async function downloadVideo(tweetUrl, onProgress) {
  let accessToken = await getAccessToken();
  let result = await attemptDownload(tweetUrl, accessToken, onProgress);

  if (result && result.status === 401) {
    accessToken = await refreshAccessToken(API_BASE_URL);
    result = await attemptDownload(tweetUrl, accessToken, onProgress);
  }

  if (!result || result.status >= 400) {
    const message = await extractErrorMessage(result);
    if (result) {
      FileSystem.deleteAsync(result.uri, { idempotent: true }).catch(() => {});
    }
    throw new Error(message);
  }

  return result.uri;
}
