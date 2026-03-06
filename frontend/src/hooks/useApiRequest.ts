import { useState, useCallback } from 'react';
import { getErrorMessage } from '../api/apiService';

export interface UseApiRequestReturn<T> {
  loading: boolean;
  error: string | null;
  data: T | null;
  execute: (...args: any[]) => Promise<T | null>;
  clearError: () => void;
  reset: () => void;
}

export function useApiRequest<T>(
  apiFunction: (...args: any[]) => Promise<T>
): UseApiRequestReturn<T> {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<T | null>(null);

  const execute = useCallback(
    async (...args: any[]): Promise<T | null> => {
      setLoading(true);
      setError(null);
      setData(null);

      try {
        const result = await apiFunction(...args);
        setData(result);
        setLoading(false);
        return result;
      } catch (err) {
        const errorMessage = getErrorMessage(err);
        setError(errorMessage);
        setLoading(false);
        return null;
      }
    },
    [apiFunction]
  );

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const reset = useCallback(() => {
    setLoading(false);
    setError(null);
    setData(null);
  }, []);

  return {
    loading,
    error,
    data,
    execute,
    clearError,
    reset,
  };
}

