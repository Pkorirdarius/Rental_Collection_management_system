import axios, {
  AxiosError,
  InternalAxiosRequestConfig,
  create,
  isAxiosError,
} from "axios";
import Constants from "expo-constants";
import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";

import type { Paginated } from "./types";

const ACCESS_KEY = "rentmanager.access";
const REFRESH_KEY = "rentmanager.refresh";

function defaultBaseUrl(): string {
  const configured = process.env.EXPO_PUBLIC_API_URL;
  if (configured) return configured.replace(/\/+$/, "");
  if (Platform.OS === "web") return "http://localhost:8000/api/v1";
  const host = Constants.expoConfig?.hostUri?.split(":")[0];
  if (host) return `http://${host}:8000/api/v1`;
  return Platform.OS === "android" ? "http://10.0.2.2:8000/api/v1" : "http://localhost:8000/api/v1";
}

export const API_BASE_URL = defaultBaseUrl();

export const api = create({
  baseURL: API_BASE_URL,
  timeout: 25000,
  headers: { "Content-Type": "application/json", Accept: "application/json" },
});

async function readItem(key: string): Promise<string | null> {
  if (Platform.OS === "web") {
    return typeof localStorage === "undefined" ? null : localStorage.getItem(key);
  }
  return SecureStore.getItemAsync(key);
}

async function writeItem(key: string, value: string): Promise<void> {
  if (Platform.OS === "web") {
    if (typeof localStorage !== "undefined") localStorage.setItem(key, value);
    return;
  }
  await SecureStore.setItemAsync(key, value);
}

async function removeItem(key: string): Promise<void> {
  if (Platform.OS === "web") {
    if (typeof localStorage !== "undefined") localStorage.removeItem(key);
    return;
  }
  await SecureStore.deleteItemAsync(key);
}

export async function loadTokens(): Promise<{ access: string | null; refresh: string | null }> {
  const [access, refresh] = await Promise.all([readItem(ACCESS_KEY), readItem(REFRESH_KEY)]);
  return { access, refresh };
}

export async function saveTokens(access: string, refresh: string): Promise<void> {
  await Promise.all([writeItem(ACCESS_KEY, access), writeItem(REFRESH_KEY, refresh)]);
}

export async function clearTokens(): Promise<void> {
  await Promise.all([removeItem(ACCESS_KEY), removeItem(REFRESH_KEY)]);
}

export async function getAccessToken(): Promise<string | null> {
  return readItem(ACCESS_KEY);
}

export function setAuthToken(access: string | null): void {
  if (access) {
    api.defaults.headers.common.Authorization = `Bearer ${access}`;
  } else {
    delete api.defaults.headers.common.Authorization;
  }
}

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(refresh: string): Promise<string | null> {
  try {
    const { data } = await axios.post<{ access: string; refresh?: string }>(
      `${API_BASE_URL}/auth/refresh`,
      { refresh },
      { timeout: 20000 },
    );
    if (!data?.access) return null;
    await writeItem(ACCESS_KEY, data.access);
    if (data.refresh) await writeItem(REFRESH_KEY, data.refresh);
    setAuthToken(data.access);
    return data.access;
  } catch {
    return null;
  }
}

type RetryConfig = InternalAxiosRequestConfig & { _retry?: boolean };

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as RetryConfig | undefined;
    const status = error.response?.status;
    const url = original?.url ?? "";
    const skip = url.includes("/auth/login") || url.includes("/auth/refresh") || url.includes("/auth/2fa/verify");
    if (status !== 401 || !original || original._retry || skip) {
      return Promise.reject(error);
    }
    original._retry = true;
    const refresh = await readItem(REFRESH_KEY);
    if (!refresh) return Promise.reject(error);
    if (!refreshPromise) refreshPromise = refreshAccessToken(refresh);
    const access = await refreshPromise;
    refreshPromise = null;
    if (!access) {
      await clearTokens();
      setAuthToken(null);
      return Promise.reject(error);
    }
    original.headers.set("Authorization", `Bearer ${access}`);
    return api(original);
  },
);

export function apiError(error: unknown): string {
  if (isAxiosError(error)) {
    const data = error.response?.data as unknown;
    if (typeof data === "string" && data.trim()) return data;
    if (data && typeof data === "object") {
      const record = data as Record<string, unknown>;
      if (record.detail) return String(record.detail);
      const first = Object.entries(record)[0];
      if (first) {
        const [field, value] = first;
        const message = Array.isArray(value) ? value.join(" ") : String(value);
        return field === "non_field_errors" ? message : `${field}: ${message}`;
      }
    }
    if (error.code === "ECONNABORTED") return "The request timed out. Try again.";
    if (!error.response) return `Cannot reach the server at ${API_BASE_URL}.`;
    return `Request failed (${error.response.status}).`;
  }
  if (error instanceof Error) return error.message;
  return "Something went wrong.";
}

export async function fetchList<T>(
  path: string,
  params?: Record<string, string | number | boolean | undefined>,
): Promise<T[]> {
  const { data } = await api.get<Paginated<T> | T[]>(path, { params });
  return Array.isArray(data) ? data : data.results;
}

export async function fetchPage<T>(
  path: string,
  params?: Record<string, string | number | boolean | undefined>,
): Promise<Paginated<T>> {
  const { data } = await api.get<Paginated<T> | T[]>(path, { params });
  if (Array.isArray(data)) {
    return { count: data.length, next: null, previous: null, results: data };
  }
  return data;
}
