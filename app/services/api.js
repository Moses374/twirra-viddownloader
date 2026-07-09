// Wraps the download call with silent access-token refresh on 401.
import * as FileSystem from "expo-file-system";
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

export async function downloadVideo(tweetUrl, onProgress) {
  let accessToken = await getAccessToken();
  let result = await attemptDownload(tweetUrl, accessToken, onProgress);

  if (result && result.status === 401) {
    accessToken = await refreshAccessToken(API_BASE_URL);
    result = await attemptDownload(tweetUrl, accessToken, onProgress);
  }

  if (!result || result.status >= 400) {
    throw new Error(`Download failed (status ${result ? result.status : "unknown"})`);
  }

  return result.uri;
}
