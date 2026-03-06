import React, { useRef, useState, useCallback, useEffect } from 'react';
import { Card, Button, Switch, HTMLSelect, FormGroup, Tag, Intent, Spinner, Icon } from '@blueprintjs/core';
import { TransformWrapper, TransformComponent, useTransformContext } from 'react-zoom-pan-pinch';
import Draggable from 'react-draggable';
import { useMapContext } from '../context/MapContext';
import { reprojectSVG } from '../api/apiService';
import { blobToDataURL } from '../utils/svgUtils';

interface Point {
  x: number;
  y: number;
  lat: number;
  lng: number;
}

type InteractionMode = 'nav' | 'measure';
type ProjectionView = 'plate-carree' | 'equal-earth';

const MeasurementOverlay: React.FC<{ 
  points: Point[]; 
  showCurvature: boolean; 
  offsetWidth: number;
  offsetHeight: number;
}> = ({ points, showCurvature, offsetWidth, offsetHeight }) => {
  const transform = useTransformContext();
  const scale = transform?.state?.scale ?? 1;
  
  const interpolateGreatCircle = (start: Point, end: Point, numPoints = 50): { x: number; y: number }[] => {
    const result: { x: number; y: number }[] = [];
    
    const lat1 = (start.lat * Math.PI) / 180;
    const lon1 = (start.lng * Math.PI) / 180;
    const lat2 = (end.lat * Math.PI) / 180;
    const lon2 = (end.lng * Math.PI) / 180;
    
    const d = Math.acos(
      Math.sin(lat1) * Math.sin(lat2) + 
      Math.cos(lat1) * Math.cos(lat2) * Math.cos(lon2 - lon1)
    );
    
    if (d === 0 || isNaN(d)) return [{ x: start.x, y: start.y }, { x: end.x, y: end.y }];
    
    for (let i = 0; i <= numPoints; i++) {
      const f = i / numPoints;
      const a = Math.sin((1 - f) * d) / Math.sin(d);
      const b = Math.sin(f * d) / Math.sin(d);
      
      const x = a * Math.cos(lat1) * Math.cos(lon1) + b * Math.cos(lat2) * Math.cos(lon2);
      const y = a * Math.cos(lat1) * Math.sin(lon1) + b * Math.cos(lat2) * Math.sin(lon2);
      const z = a * Math.sin(lat1) + b * Math.sin(lat2);
      
      const latN = (Math.atan2(z, Math.sqrt(x * x + y * y)) * 180) / Math.PI;
      const lonN = (Math.atan2(y, x) * 180) / Math.PI;
      
      const px = ((lonN + 180) / 360) * offsetWidth;
      const py = ((90 - latN) / 180) * offsetHeight;
      
      result.push({ x: px, y: py });
    }
    
    return result;
  };

  const generateLinePath = () => {
    if (points.length < 2) return '';
    
    let pathD = '';
    
    for (let i = 0; i < points.length - 1; i++) {
      if (showCurvature) {
        const curvePoints = interpolateGreatCircle(points[i], points[i + 1]);
        if (curvePoints.length > 0) {
          let currentPath = `M ${curvePoints[0].x} ${curvePoints[0].y}`;
          for (let j = 1; j < curvePoints.length; j++) {
            const dxF = Math.abs(curvePoints[j].x - curvePoints[j - 1].x);
            if (dxF > 100) {
              pathD += currentPath + ' ';
              currentPath = `M ${curvePoints[j].x} ${curvePoints[j].y}`;
            } else {
              currentPath += ` L ${curvePoints[j].x} ${curvePoints[j].y}`;
            }
          }
          pathD += currentPath + ' ';
        }
      } else {
        pathD += `M ${points[i].x} ${points[i].y} L ${points[i + 1].x} ${points[i + 1].y} `;
      }
    }
    
    return pathD;
  };

  const baseRadius = 6;
  const adjustedRadius = baseRadius / scale;

  return (
    <svg className="map-overlay" style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none' }}>
      <path
        d={generateLinePath()}
        stroke="#ee9b00"
        strokeWidth={3 / scale}
        fill="none"
      />
      
      {points.map((point, i) => (
        <circle
          key={i}
          cx={point.x}
          cy={point.y}
          r={adjustedRadius}
          fill="#e9d8a6"
          stroke="#005f73"
          strokeWidth={2 / scale}
        />
      ))}
    </svg>
  );
};

export const MapPage: React.FC = () => {
  const { svgDataURL, svgFile } = useMapContext();
  const containerRef = useRef<HTMLDivElement>(null);
  const cardRef = useRef<HTMLDivElement>(null);
  const [points, setPoints] = useState<Point[]>([]);
  const [showCurvature, setShowCurvature] = useState(false);
  const [interactionMode, setInteractionMode] = useState<InteractionMode>('nav');
  const [projection, setProjection] = useState<ProjectionView>('plate-carree');
  const [reprojectedDataURL, setReprojectedDataURL] = useState<string | null>(null);
  const [isLoadingReprojection, setIsLoadingReprojection] = useState(false);
  const [containerSize, setContainerSize] = useState({ width: 0, height: 0 });

  useEffect(() => {
    setReprojectedDataURL(null);
    setProjection('plate-carree');
    setPoints([]);
  }, [svgDataURL]);

  useEffect(() => {
    const updateSize = () => {
      if (containerRef.current) {
        setContainerSize({
          width: containerRef.current.offsetWidth,
          height: containerRef.current.offsetHeight,
        });
      }
    };
    updateSize();
    window.addEventListener('resize', updateSize);
    return () => window.removeEventListener('resize', updateSize);
  }, []);

  const handleProjectionChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newProjection = e.target.value as ProjectionView;
    setProjection(newProjection);

    if (newProjection === 'equal-earth') {
      setInteractionMode('nav');
      
      if (!reprojectedDataURL) {
        setIsLoadingReprojection(true);
        try {
          let fileToUpload: File;
          if (svgFile) {
            fileToUpload = svgFile;
          } else {
            const response = await fetch('/pc.svg');
            const blob = await response.blob();
            fileToUpload = new File([blob], 'Weltkarte.svg', { type: 'image/svg+xml' });
          }

          const resultBlob = await reprojectSVG(fileToUpload, { direction: 'plate-to-equal' });
          const url = await blobToDataURL(resultBlob);
          setReprojectedDataURL(url);
        } catch (error) {
          console.error('Reprojection failed:', error);
          setProjection('plate-carree');
        } finally {
          setIsLoadingReprojection(false);
        }
      }
    }
  };

  const calculateDistance = useCallback(() => {
    if (points.length < 2) return 0;
    
    let total = 0;
    const R = 6371;
    
    for (let i = 0; i < points.length - 1; i++) {
      const lat1 = (points[i].lat * Math.PI) / 180;
      const lat2 = (points[i + 1].lat * Math.PI) / 180;
      const dLat = ((points[i + 1].lat - points[i].lat) * Math.PI) / 180;
      const dLon = ((points[i + 1].lng - points[i].lng) * Math.PI) / 180;
      
      const a = Math.sin(dLat / 2) ** 2 + 
                Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) ** 2;
      const c = 2 * Math.asin(Math.sqrt(a));
      total += R * c;
    }
    
    return total;
  }, [points]);

  const handleMapClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (interactionMode !== 'measure' || projection !== 'plate-carree') return;
    if (!containerRef.current) return;
    
    const rect = containerRef.current.getBoundingClientRect();
    
    const scaleX = rect.width / containerSize.width;
    const scaleY = rect.height / containerSize.height;
    
    const xScreen = e.clientX - rect.left;
    const yScreen = e.clientY - rect.top;
    
    const xLayout = xScreen / scaleX;
    const yLayout = yScreen / scaleY;
    
    const lng = ((xScreen / rect.width) * 360) - 180;
    const lat = 90 - ((yScreen / rect.height) * 180);
    
    setPoints(prev => [...prev, { x: xLayout, y: yLayout, lat, lng }]);
  }, [interactionMode, projection, containerSize]);

  const clearMeasurement = useCallback(() => {
    setPoints([]);
  }, []);

  const deleteLastPoint = useCallback(() => {
    setPoints(prev => prev.slice(0, -1));
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Backspace' && !['INPUT', 'TEXTAREA', 'SELECT'].includes((e.target as Element)?.tagName)) {
        e.preventDefault();
        deleteLastPoint();
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [deleteLastPoint]);

  const distance = calculateDistance();
  const currentImageURL = projection === 'equal-earth' ? reprojectedDataURL : svgDataURL;

  return (
    <div className="map-page">
      <div className="map-controls">
        <Draggable handle=".drag-handle" nodeRef={cardRef}>
           <div ref={cardRef}>
            <Card style={{ pointerEvents: 'auto' }}>
              <div className="drag-handle" style={{ 
                cursor: 'grab', 
                paddingBottom: '10px', 
                marginBottom: '10px', 
                borderBottom: '1px solid #394b59',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#a7b6c2'
              }}>
                 <Icon icon="drag-handle-horizontal" />
              </div>

              <FormGroup label="Projektion">
                <HTMLSelect fill value={projection} onChange={handleProjectionChange}>
                  <option value="plate-carree">Plate Carrée (SVG)</option>
                  <option value="equal-earth">Equal Earth</option>
                </HTMLSelect>
              </FormGroup>

              <FormGroup label="Modus">
                <div style={{ display: 'flex', gap: '10px' }}>
                    <Button 
                      active={interactionMode === 'nav'} 
                      onClick={() => setInteractionMode('nav')} 
                      icon="move" 
                      title="Navigieren (Zoom/Pan)"
                    />
                    <Button 
                      active={interactionMode === 'measure'} 
                      onClick={() => setInteractionMode('measure')} 
                      icon="timeline-line-chart" 
                      title="Messen"
                      disabled={projection !== 'plate-carree'}
                    />
                </div>
              </FormGroup>
              
              {projection === 'plate-carree' && (
                <>
                  <Switch
                    checked={showCurvature}
                    label="Krümmung anzeigen"
                    onChange={(e) => setShowCurvature((e.target as HTMLInputElement).checked)}
                  />

                  {points.length > 0 && (
                    <Tag minimal fill style={{ marginTop: 15, justifyContent: 'center' }}>
                      {points[points.length - 1].lng.toFixed(2)}° / {points[points.length - 1].lat.toFixed(2)}°
                    </Tag>
                  )}
                  
                  <Tag large fill intent={Intent.PRIMARY} style={{ marginTop: 10, justifyContent: 'center' }}>
                    {distance.toFixed(2)} km
                  </Tag>
                  
                  <Button
                    text="Messung löschen"
                    icon="trash"
                    onClick={clearMeasurement}
                    fill
                    style={{ marginTop: 10 }}
                  />
                  
                  <p className="bp5-text-muted bp5-text-small" style={{ marginTop: 10, textAlign: 'center' }}>
                    Backspace: letzten Punkt löschen
                  </p>
                </>
              )}

              {projection === 'equal-earth' && (
                <p className="bp5-text-muted bp5-text-small" style={{ marginTop: 10 }}>
                  Messungen sind nur in Plate Carrée verfügbar.
                </p>
              )}
            </Card>
           </div>
        </Draggable>
      </div>
      
      <div className="map-wrapper" style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
         {isLoadingReprojection ? (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
               <Spinner />
               <div style={{ marginLeft: 10 }}>Berechne Projektion...</div>
            </div>
         ) : (
            <TransformWrapper
               disabled={interactionMode === 'measure'}
               minScale={1}
               maxScale={8}
               centerOnInit
            >
               <TransformComponent wrapperStyle={{ width: '100%', height: '100%' }} contentStyle={{ width: '100%', height: '100%' }}>
                  <div 
                    className="map-container"
                    ref={containerRef}
                    onClick={handleMapClick}
                    style={{ 
                       cursor: interactionMode === 'measure' ? 'crosshair' : 'grab',
                       width: '100%',
                       height: '100%',
                       position: 'relative'
                    }}
                  >
                    {currentImageURL && (
                      <img 
                        src={currentImageURL} 
                        alt="Map" 
                        draggable={false}
                        style={{ width: '100%', height: 'auto', display: 'block' }}
                      />
                    )}
                    
                    {projection === 'plate-carree' && containerSize.width > 0 && (
                      <MeasurementOverlay 
                        points={points} 
                        showCurvature={showCurvature}
                        offsetWidth={containerSize.width}
                        offsetHeight={containerSize.height}
                      />
                    )}
                  </div>
               </TransformComponent>
            </TransformWrapper>
         )}
      </div>
    </div>
  );
};
