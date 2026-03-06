import { useState, useCallback } from 'react';

export interface UseFileUploadReturn {
  file: File | null;
  setFile: (file: File | null) => void;
  preview: string | null;
  clearFile: () => void;
  isLoading: boolean;
}

export function useFileUpload(): UseFileUploadReturn {
  const [file, setFileState] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const setFile = useCallback((newFile: File | null) => {
    setFileState(newFile);
    
    if (newFile) {
      setIsLoading(true);
      const reader = new FileReader();
      reader.onload = () => {
        setPreview(reader.result as string);
        setIsLoading(false);
      };
      reader.onerror = () => {
        setPreview(null);
        setIsLoading(false);
      };
      reader.readAsDataURL(newFile);
    } else {
      setPreview(null);
      setIsLoading(false);
    }
  }, []);

  const clearFile = useCallback(() => {
    setFileState(null);
    setPreview(null);
    setIsLoading(false);
  }, []);

  return {
    file,
    setFile,
    preview,
    clearFile,
    isLoading,
  };
}

