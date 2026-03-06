import React, { createContext, useContext, useState, useCallback } from 'react';
import type { ReactNode } from 'react';

interface MapContextType {
  svgFile: File | null;
  svgDataURL: string | null;
  setSvgFile: (file: File | null) => void;
  useDefaultMap: () => void;
}

const MapContext = createContext<MapContextType | null>(null);

const DEFAULT_MAP_URL = '/pc.svg';

export const MapProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [svgFile, setSvgFileState] = useState<File | null>(null);
  const [svgDataURL, setSvgDataURL] = useState<string | null>(DEFAULT_MAP_URL);

  const setSvgFile = useCallback((file: File | null) => {
    setSvgFileState(file);
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        setSvgDataURL(e.target?.result as string);
      };
      reader.readAsDataURL(file);
    } else {
      setSvgDataURL(DEFAULT_MAP_URL);
    }
  }, []);

  const useDefaultMap = useCallback(() => {
    setSvgFileState(null);
    setSvgDataURL(DEFAULT_MAP_URL);
  }, []);

  return (
    <MapContext.Provider value={{ svgFile, svgDataURL, setSvgFile, useDefaultMap }}>
      {children}
    </MapContext.Provider>
  );
};

export const useMapContext = () => {
  const context = useContext(MapContext);
  if (!context) {
    throw new Error('useMapContext must be used within a MapProvider');
  }
  return context;
};

