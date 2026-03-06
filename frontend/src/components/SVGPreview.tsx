import React, { useEffect, useState, useRef, useCallback } from 'react';
import { Card, Button, Spinner, H4 } from '@blueprintjs/core';
import { downloadFile } from '../utils/downloadFile';
import { blobToDataURL } from '../utils/svgUtils';

interface DragSelection {
  start: [number, number];
  end: [number, number];
}

interface MapSelection {
  topLeft: [number, number];
  bottomRight: [number, number];
}

type InteractionMode = 'select' | 'pan';

interface SVGPreviewProps {
  svgBlob?: Blob | null;
  svgDataURL?: string | null;
  filename?: string;
  title: string;
  isLoading?: boolean;
  interactive?: boolean;
  selection?: { topLeft: [number, number]; bottomRight: [number, number] } | null;
  onSelectionChange?: (topLeft: [number, number], bottomRight: [number, number]) => void;
}

const clamp = (value: number, min: number, max: number): number => Math.max(min, Math.min(max, value));

const normalizeSelection = (start: [number, number], end: [number, number]): MapSelection => ({
  topLeft: [Math.min(start[0], end[0]), Math.max(start[1], end[1])],
  bottomRight: [Math.max(start[0], end[0]), Math.min(start[1], end[1])],
});

const shiftSelection = (selection: MapSelection, dLon: number, dLat: number): MapSelection => {
  const widthLon = selection.bottomRight[0] - selection.topLeft[0];
  const heightLat = selection.topLeft[1] - selection.bottomRight[1];

  const newTopLeftLon = clamp(selection.topLeft[0] + dLon, -180, 180 - widthLon);
  const newTopLeftLat = clamp(selection.topLeft[1] + dLat, -90 + heightLat, 90);

  return {
    topLeft: [newTopLeftLon, newTopLeftLat],
    bottomRight: [newTopLeftLon + widthLon, newTopLeftLat - heightLat],
  };
};

export const SVGPreview: React.FC<SVGPreviewProps> = ({
  svgBlob,
  svgDataURL,
  filename = 'map.svg',
  title,
  isLoading = false,
  interactive = false,
  selection: externalSelection,
  onSelectionChange,
}) => {
  const [previewURL, setPreviewURL] = useState<string | null>(null);
  const [dragSelection, setDragSelection] = useState<DragSelection | null>(null);
  const [isSelecting, setIsSelecting] = useState(false);
  const [isPanning, setIsPanning] = useState(false);
  const [isDraggingCenter, setIsDraggingCenter] = useState(false);
  const [viewScale, setViewScale] = useState(1);
  const [offsetX, setOffsetX] = useState(0);
  const [offsetY, setOffsetY] = useState(0);
  const [interactionMode, setInteractionMode] = useState<InteractionMode>('select');
  const containerRef = useRef<HTMLDivElement>(null);
  const panRef = useRef<{ x: number; y: number; startOffsetX: number; startOffsetY: number } | null>(null);
  const centerDragRef = useRef<[number, number] | null>(null);
  const touchStartRef = useRef<{ x: number; y: number; scale: number; offsetX: number; offsetY: number } | null>(null);
  const lastTouchDistRef = useRef<number | null>(null);

  useEffect(() => {
    if (svgDataURL) {
      setPreviewURL(svgDataURL);
    } else if (svgBlob) {
      blobToDataURL(svgBlob).then(setPreviewURL).catch(console.error);
    } else {
      setPreviewURL(null);
    }
  }, [svgBlob, svgDataURL]);

  const handleDownload = () => {
    if (svgBlob) {
      downloadFile(svgBlob, filename);
    }
  };

  const resetView = useCallback(() => {
    setViewScale(1);
    setOffsetX(0);
    setOffsetY(0);
  }, []);

  const getContainerSize = useCallback(() => {
    const rect = containerRef.current?.getBoundingClientRect();
    return {
      width: rect?.width ?? 0,
      height: rect?.height ?? 0,
      left: rect?.left ?? 0,
      top: rect?.top ?? 0,
    };
  }, []);

  const toMapCoordinates = useCallback((clientX: number, clientY: number) => {
    const { width, height, left, top } = getContainerSize();
    if (width <= 0 || height <= 0) {
      return null;
    }
    const localX = clientX - left;
    const localY = clientY - top;
    const mapX = (localX - offsetX) / viewScale;
    const mapY = (localY - offsetY) / viewScale;

    return {
      width,
      height,
      mapX: clamp(mapX, 0, width),
      mapY: clamp(mapY, 0, height),
    };
  }, [getContainerSize, offsetX, offsetY, viewScale]);

  const mapToGeo = useCallback((mapX: number, mapY: number, width: number, height: number): [number, number] => {
    const lon = ((mapX / width) * 360) - 180;
    const lat = 90 - ((mapY / height) * 180);
    return [clamp(lon, -180, 180), clamp(lat, -90, 90)];
  }, []);

  const geoToMap = useCallback((lon: number, lat: number, width: number, height: number): [number, number] => {
    const x = ((lon + 180) / 360) * width;
    const y = ((90 - lat) / 180) * height;
    return [x, y];
  }, []);

  const zoomBy = useCallback((factor: number, centerX?: number, centerY?: number) => {
    const { width, height } = getContainerSize();
    if (width <= 0 || height <= 0) return;

    const cx = centerX ?? width / 2;
    const cy = centerY ?? height / 2;
    const newScale = clamp(viewScale * factor, 1, 12);
    const mapCenterX = (cx - offsetX) / viewScale;
    const mapCenterY = (cy - offsetY) / viewScale;

    setViewScale(newScale);
    setOffsetX(cx - mapCenterX * newScale);
    setOffsetY(cy - mapCenterY * newScale);
  }, [getContainerSize, offsetX, offsetY, viewScale]);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (!interactive || !containerRef.current) return;

      if (e.button === 1 || e.button === 2 || interactionMode === 'pan') {
        e.preventDefault();
        setIsPanning(true);
        panRef.current = {
          x: e.clientX,
          y: e.clientY,
          startOffsetX: offsetX,
          startOffsetY: offsetY,
        };
        return;
      }

      if (e.button !== 0) return;

      const coords = toMapCoordinates(e.clientX, e.clientY);
      if (!coords) return;

      const geo = mapToGeo(coords.mapX, coords.mapY, coords.width, coords.height);
      setDragSelection({ start: geo, end: geo });
      setIsSelecting(true);
    },
    [interactive, mapToGeo, offsetX, offsetY, toMapCoordinates, interactionMode]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (!containerRef.current) return;

      if (isPanning && panRef.current) {
        const dx = e.clientX - panRef.current.x;
        const dy = e.clientY - panRef.current.y;
        setOffsetX(panRef.current.startOffsetX + dx);
        setOffsetY(panRef.current.startOffsetY + dy);
        return;
      }

      const coords = toMapCoordinates(e.clientX, e.clientY);
      if (!coords) return;

      if (isDraggingCenter && externalSelection && onSelectionChange) {
        const currentGeo = mapToGeo(coords.mapX, coords.mapY, coords.width, coords.height);
        const prevGeo = centerDragRef.current ?? currentGeo;
        centerDragRef.current = currentGeo;

        const dLon = currentGeo[0] - prevGeo[0];
        const dLat = currentGeo[1] - prevGeo[1];
        const shifted = shiftSelection(externalSelection, dLon, dLat);
        onSelectionChange(shifted.topLeft, shifted.bottomRight);
        return;
      }

      if (!isSelecting || !dragSelection) return;

      const geo = mapToGeo(coords.mapX, coords.mapY, coords.width, coords.height);
      setDragSelection((prev) => (prev ? { ...prev, end: geo } : null));
    },
    [
      dragSelection,
      externalSelection,
      isDraggingCenter,
      isPanning,
      isSelecting,
      mapToGeo,
      onSelectionChange,
      toMapCoordinates,
    ]
  );

  const handleMouseUp = useCallback(() => {
    if (isPanning) {
      setIsPanning(false);
      panRef.current = null;
    }

    if (isDraggingCenter) {
      setIsDraggingCenter(false);
      centerDragRef.current = null;
    }

    if (isSelecting && dragSelection && onSelectionChange) {
      const normalized = normalizeSelection(dragSelection.start, dragSelection.end);
      onSelectionChange(normalized.topLeft, normalized.bottomRight);
    }

    setIsSelecting(false);
    setDragSelection(null);
  }, [dragSelection, isDraggingCenter, isPanning, isSelecting, onSelectionChange]);

  const handleWheel = useCallback((e: React.WheelEvent<HTMLDivElement>) => {
    if (!interactive) return;
    e.preventDefault();

    const { width, height, left, top } = getContainerSize();
    if (width <= 0 || height <= 0) return;

    const mouseX = e.clientX - left;
    const mouseY = e.clientY - top;

    const zoomFactor = e.deltaY < 0 ? 1.12 : 0.89;
    const newScale = clamp(viewScale * zoomFactor, 1, 12);

    const mapX = (mouseX - offsetX) / viewScale;
    const mapY = (mouseY - offsetY) / viewScale;

    setViewScale(newScale);
    setOffsetX(mouseX - mapX * newScale);
    setOffsetY(mouseY - mapY * newScale);
  }, [getContainerSize, interactive, offsetX, offsetY, viewScale]);

  const handleTouchStart = useCallback((e: React.TouchEvent<HTMLDivElement>) => {
    if (!interactive) return;
    
    if (e.touches.length === 1) {
      const touch = e.touches[0];
      touchStartRef.current = {
        x: touch.clientX,
        y: touch.clientY,
        scale: viewScale,
        offsetX: offsetX,
        offsetY: offsetY,
      };
    } else if (e.touches.length === 2) {
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      lastTouchDistRef.current = Math.sqrt(dx * dx + dy * dy);
      
      const midX = (e.touches[0].clientX + e.touches[1].clientX) / 2;
      const midY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
      touchStartRef.current = {
        x: midX,
        y: midY,
        scale: viewScale,
        offsetX: offsetX,
        offsetY: offsetY,
      };
    }
  }, [interactive, viewScale, offsetX, offsetY]);

  const handleTouchMove = useCallback((e: React.TouchEvent<HTMLDivElement>) => {
    if (!interactive || !touchStartRef.current) return;

    if (e.touches.length === 1 && interactionMode === 'pan') {
      const touch = e.touches[0];
      const dx = touch.clientX - touchStartRef.current.x;
      const dy = touch.clientY - touchStartRef.current.y;
      setOffsetX(touchStartRef.current.offsetX + dx);
      setOffsetY(touchStartRef.current.offsetY + dy);
    } else if (e.touches.length === 2) {
      const touchDx = e.touches[0].clientX - e.touches[1].clientX;
      const touchDy = e.touches[0].clientY - e.touches[1].clientY;
      const dist = Math.sqrt(touchDx * touchDx + touchDy * touchDy);
      let newScale = viewScale;

      if (lastTouchDistRef.current !== null && dist > 0) {
        const scaleFactor = dist / lastTouchDistRef.current;
        newScale = clamp(touchStartRef.current.scale * scaleFactor, 1, 12);
        setViewScale(newScale);
      }

      const midX = (e.touches[0].clientX + e.touches[1].clientX) / 2;
      const midY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
      const panDx = midX - touchStartRef.current.x;
      const panDy = midY - touchStartRef.current.y;
      
      setOffsetX(touchStartRef.current.offsetX + panDx);
      setOffsetY(touchStartRef.current.offsetY + panDy);

      lastTouchDistRef.current = dist;
    }
  }, [interactive, interactionMode, getContainerSize]);

  const handleTouchEnd = useCallback(() => {
    touchStartRef.current = null;
    lastTouchDistRef.current = null;
  }, []);

  const handleCenterMouseDown = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!interactive || !externalSelection) return;
    e.preventDefault();
    e.stopPropagation();
    setIsDraggingCenter(true);
    centerDragRef.current = null;
  }, [externalSelection, interactive]);

  const getSelectionStyle = (): React.CSSProperties | null => {
    if (!containerRef.current) return null;
    const rect = containerRef.current.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return null;

    const activeSelection = dragSelection ? normalizeSelection(dragSelection.start, dragSelection.end) : externalSelection;
    if (!activeSelection) return null;

    const [x1, y1] = geoToMap(activeSelection.topLeft[0], activeSelection.topLeft[1], rect.width, rect.height);
    const [x2, y2] = geoToMap(activeSelection.bottomRight[0], activeSelection.bottomRight[1], rect.width, rect.height);

    return {
      position: 'absolute',
      left: Math.min(x1, x2),
      top: Math.min(y1, y2),
      width: Math.abs(x2 - x1),
      height: Math.abs(y2 - y1),
      border: '2px solid #2d72d2',
      backgroundColor: 'rgba(45, 114, 210, 0.2)',
      pointerEvents: 'none',
    };
  };

  const getCenterStyle = (): React.CSSProperties | null => {
    if (!containerRef.current || !externalSelection) return null;
    const rect = containerRef.current.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return null;

    const centerLon = (externalSelection.topLeft[0] + externalSelection.bottomRight[0]) / 2;
    const centerLat = (externalSelection.topLeft[1] + externalSelection.bottomRight[1]) / 2;
    const [x, y] = geoToMap(centerLon, centerLat, rect.width, rect.height);

    return {
      position: 'absolute',
      left: x - 6,
      top: y - 6,
      width: 12,
      height: 12,
      borderRadius: '50%',
      backgroundColor: '#db3737',
      border: '2px solid #ffffff',
      boxShadow: '0 0 0 1px rgba(0,0,0,0.35)',
      cursor: 'move',
      pointerEvents: interactive ? 'auto' : 'none',
    };
  };

  const selectionStyle = getSelectionStyle();
  const centerStyle = getCenterStyle();
  const cursor = isPanning ? 'grabbing' : interactionMode === 'pan' ? 'grab' : interactive ? 'crosshair' : 'default';

  return (
    <Card className="svg-preview-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <H4 style={{ margin: 0 }}>{title}</H4>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {interactive && (
            <>
              <Button 
                small 
                icon="select" 
                active={interactionMode === 'select'} 
                onClick={() => setInteractionMode('select')} 
                title="Auswählen"
              />
              <Button 
                small 
                icon="move" 
                active={interactionMode === 'pan'} 
                onClick={() => setInteractionMode('pan')} 
                title="Verschieben"
              />
              <Button small icon="zoom-in" onClick={() => zoomBy(1.15)} />
              <Button small icon="zoom-out" onClick={() => zoomBy(0.87)} />
              <Button small icon="refresh" onClick={resetView} />
            </>
          )}
          {svgBlob && (
            <Button icon="download" intent="primary" onClick={handleDownload} text="Download" />
          )}
        </div>
      </div>

      {isLoading && (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: 40 }}>
          <Spinner size={40} />
          <p className="bp5-text-muted">Verarbeite...</p>
        </div>
      )}

      {!isLoading && previewURL && (
        <div
          ref={containerRef}
          className="svg-container"
          style={{ position: 'relative', cursor, userSelect: 'none', overflow: 'hidden', touchAction: 'none' }}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onWheel={handleWheel}
          onContextMenu={(e) => e.preventDefault()}
          onTouchStart={handleTouchStart}
          onTouchMove={handleTouchMove}
          onTouchEnd={handleTouchEnd}
        >
          <div
            style={{
              position: 'relative',
              width: '100%',
              transform: `translate(${offsetX}px, ${offsetY}px) scale(${viewScale})`,
              transformOrigin: '0 0',
            }}
          >
            <img src={previewURL} alt={title} style={{ width: '100%', display: 'block', pointerEvents: 'none' }} draggable={false} />
            {selectionStyle && interactionMode === 'select' && <div style={selectionStyle} />}
            {centerStyle && interactionMode === 'select' && <div style={centerStyle} onMouseDown={handleCenterMouseDown} />}
          </div>
        </div>
      )}

      {!isLoading && !previewURL && (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <p className="bp5-text-muted">Keine Vorschau verfügbar</p>
        </div>
      )}
    </Card>
  );
};
