import { useCallback, useEffect, useState } from "react";

import { api, apiError } from "./api";

export function useApi<T>(
  path: string | null,
  params?: Record<string, string | number | boolean | undefined>,
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(Boolean(path));
  const [error, setError] = useState("");
  const paramKey = JSON.stringify(params ?? {});

  const reload = useCallback(async () => {
    if (!path) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const response = await api.get<T>(path, { params: JSON.parse(paramKey) });
      setData(response.data);
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  }, [path, paramKey]);

  useEffect(() => {
    reload();
  }, [reload]);

  return { data, loading, error, reload, setData };
}
