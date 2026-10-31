import { fetch } from "expo/fetch";
import { File, Paths } from "expo-file-system";
import * as Sharing from "expo-sharing";

import { API_BASE_URL, getAccessToken } from "./api";

export async function openAuthenticatedPdf(path: string, filename: string): Promise<void> {
  const token = await getAccessToken();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
  if (!response.ok) {
    throw new Error(`Could not download the PDF (${response.status}).`);
  }
  const file = new File(Paths.cache, filename);
  if (file.exists) file.delete();
  await file.write(await response.bytes());

  if (await file.canPreview()) {
    await file.preview({ title: filename });
    return;
  }
  if (await Sharing.isAvailableAsync()) {
    await Sharing.shareAsync(file.uri, {
      mimeType: "application/pdf",
      dialogTitle: filename,
    });
    return;
  }
  throw new Error("No app is available to open this PDF on this device.");
}
