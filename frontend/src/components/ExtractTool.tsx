import React, { useState } from 'react';
import { OverlayToaster, Position, Intent, Button, Card, HTMLSelect, Switch, FormGroup, Callout, Tag, NumericInput, Checkbox } from '@blueprintjs/core';
import type { Toaster } from '@blueprintjs/core';
import { FileUploadZone } from './FileUploadZone';
import { SVGPreview } from './SVGPreview';
import { useMapContext } from '../context/MapContext';
import { useApiRequest } from '../hooks/useApiRequest';
import { extractByCorners } from '../api/apiService';
import type { ProjectionType } from '../api/types';

let toaster: Toaster;
OverlayToaster.createAsync({ position: Position.TOP }).then(t => toaster = t);

export const ExtractTool: React.FC = () => {
  const { svgFile, svgDataURL, setSvgFile, useDefaultMap } = useMapContext();
  const cornersRequest = useApiRequest(extractByCorners);
  const [resultBlob, setResultBlob] = useState<Blob | null>(null);
  const [resultFilename, setResultFilename] = useState<string>('extracted_map.svg');
  
  const [selection, setSelection] = useState<{
    topLeft: [number, number];
    bottomRight: [number, number];
  } | null>(null);
  
  const [reproject, setReproject] = useState(true);
  const [projection, setProjection] = useState<ProjectionType>('aeqd');
  const [graticuleSpacing, setGraticuleSpacing] = useState<number | undefined>(undefined);
  const [scaleBarKm, setScaleBarKm] = useState<number | undefined>(undefined);

  const loading = cornersRequest.loading;

  const handleFileSelect = (newFile: File | null) => {
    setSvgFile(newFile);
    setResultBlob(null);
    setSelection(null);
  };

  const handleSelectionChange = (topLeft: [number, number], bottomRight: [number, number]) => {
    setSelection({ topLeft, bottomRight });
  };

  const handleCalculate = async () => {
    if (!selection) {
      toaster.show({ message: 'Bitte einen Bereich auswählen', intent: Intent.WARNING, icon: 'warning-sign' });
      return;
    }

    let fileToProcess = svgFile;
    
    if (!fileToProcess && svgDataURL) {
      try {
        const response = await fetch(svgDataURL);
        const blob = await response.blob();
        fileToProcess = new File([blob], 'plate-carree.svg', { type: 'image/svg+xml' });
      } catch {
        toaster.show({ message: 'Fehler beim Laden der Karte', intent: Intent.DANGER, icon: 'error' });
        return;
      }
    }

    if (!fileToProcess) {
      toaster.show({ message: 'Keine SVG verfügbar', intent: Intent.WARNING, icon: 'warning-sign' });
      return;
    }

    const outputFilename = `extracted_${fileToProcess.name}`;
    const params = {
      top_left: selection.topLeft,
      bottom_right: selection.bottomRight,
      input_bounds: [-180, -90, 180, 90] as [number, number, number, number],
      output_width: 800,
      reproject,
      projection,
      output_filename: outputFilename,
      graticule_spacing: graticuleSpacing,
      scale_bar_km: scaleBarKm,
    };

    const result = await cornersRequest.execute(fileToProcess, params);

    if (result) {
      setResultBlob(result);
      setResultFilename(outputFilename);
      toaster.show({ message: 'Extraktion erfolgreich!', intent: Intent.SUCCESS, icon: 'tick' });
    } else if (cornersRequest.error) {
      toaster.show({ message: `Fehler: ${cornersRequest.error}`, intent: Intent.DANGER, icon: 'error', timeout: 5000 });
    }
  };

  return (
    <div className="extract-tool">
      <div className="tool-layout">
        <div className="tool-controls">
          <FileUploadZone onFileSelect={handleFileSelect} currentFile={svgFile} disabled={loading} />
          
          {!svgFile && (
            <Callout intent={Intent.PRIMARY} icon="info-sign">Standard Plate Carrée wird verwendet.</Callout>
          )}
          
          {svgFile && (
            <Button text="Standard-Karte" icon="reset" onClick={useDefaultMap} variant="minimal" />
          )}

          <Card>
            <Callout intent={Intent.PRIMARY} icon="select" style={{ marginBottom: 15 }}>
              Bereich auf der Karte auswählen
            </Callout>

            {selection && (
              <Tag large fill intent={Intent.SUCCESS} style={{ marginBottom: 15 }}>
                ({selection.topLeft[0].toFixed(1)}°, {selection.topLeft[1].toFixed(1)}°) → 
                ({selection.bottomRight[0].toFixed(1)}°, {selection.bottomRight[1].toFixed(1)}°)
              </Tag>
            )}

            <FormGroup label="Projektion">
              <HTMLSelect value={projection} onChange={(e) => setProjection(e.target.value as ProjectionType)} disabled={loading} fill>
                <option value="aeqd">Azimuthal Equidistant</option>
                <option value="laea">Lambert Equal-Area</option>
                <option value="ortho">Orthographic</option>
                <option value="stere">Stereographic</option>
                <option value="lcc">Lambert Conformal Conic</option>
                <option value="tmerc">Transverse Mercator</option>
              </HTMLSelect>
            </FormGroup>

            <Switch
              checked={reproject}
              label="Zentrierte Reprojektion"
              onChange={(e) => setReproject((e.target as HTMLInputElement).checked)}
              disabled={loading}
            />

            <FormGroup label="Gitternetz (°)" helperText="z.B. 10 für alle 10°">
              <NumericInput
                value={graticuleSpacing ?? ''}
                onValueChange={(value) => setGraticuleSpacing(value > 0 ? value : undefined)}
                disabled={loading}
                placeholder="Kein Gitternetz"
                min={1}
                max={90}
                stepSize={5}
                allowNumericCharactersOnly
              />
            </FormGroup>

            <FormGroup label="Maßstab (km)" helperText="z.B. 500 für 500 km">
              <NumericInput
                value={scaleBarKm ?? ''}
                onValueChange={(value) => setScaleBarKm(value > 0 ? value : undefined)}
                disabled={loading}
                placeholder="Kein Maßstab"
                min={1}
                max={10000}
                stepSize={100}
                allowNumericCharactersOnly
              />
            </FormGroup>

            <Button
              text="Berechnen"
              intent={Intent.PRIMARY}
              icon="calculator"
              onClick={handleCalculate}
              disabled={loading || !selection}
              large
              fill
              loading={loading}
              style={{ marginTop: 15 }}
            />
          </Card>
        </div>

        <div className="tool-previews">
          <SVGPreview
            svgDataURL={svgDataURL}
            title="Eingabe SVG"
            isLoading={false}
            interactive={!loading}
            selection={selection}
            onSelectionChange={handleSelectionChange}
          />
          <SVGPreview svgBlob={resultBlob} filename={resultFilename} title="Extrahiert" isLoading={loading} />
        </div>
      </div>
    </div>
  );
};
