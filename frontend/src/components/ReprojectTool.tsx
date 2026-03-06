import React, { useState } from 'react';
import { OverlayToaster, Position, Intent, Button, Callout } from '@blueprintjs/core';
import type { Toaster } from '@blueprintjs/core';
import { FileUploadZone } from './FileUploadZone';
import { SVGPreview } from './SVGPreview';
import { ReprojectionForm } from './ReprojectionForm';
import type { ReprojectionFormData } from '../api/types';
import { useMapContext } from '../context/MapContext';
import { useApiRequest } from '../hooks/useApiRequest';
import { reprojectSVG } from '../api/apiService';

let toaster: Toaster;
OverlayToaster.createAsync({ position: Position.TOP }).then(t => toaster = t);

export const ReprojectTool: React.FC = () => {
  const { svgFile, svgDataURL, setSvgFile, useDefaultMap } = useMapContext();
  const { loading, error, execute } = useApiRequest(reprojectSVG);
  const [resultBlob, setResultBlob] = useState<Blob | null>(null);
  const [resultFilename, setResultFilename] = useState<string>('reprojected_map.svg');

  const handleFileSelect = (newFile: File | null) => {
    setSvgFile(newFile);
    setResultBlob(null);
  };

  const handleSubmit = async (formData: ReprojectionFormData) => {
    let fileToProcess = svgFile;
    
    if (!fileToProcess && svgDataURL) {
      try {
        const response = await fetch(svgDataURL);
        const blob = await response.blob();
        fileToProcess = new File([blob], 'plate-carree.svg', { type: 'image/svg+xml' });
      } catch {
        toaster.show({ message: 'Fehler beim Laden der Standard-Karte', intent: Intent.DANGER, icon: 'error' });
        return;
      }
    }

    if (!fileToProcess) {
      toaster.show({ message: 'Keine SVG-Datei verfügbar', intent: Intent.WARNING, icon: 'warning-sign' });
      return;
    }

    const options = {
      direction: formData.direction,
      orientation: formData.orientation,
      input_bounds: formData.input_bounds,
      output_width: formData.output_width,
      padding: formData.padding,
      output_filename: `reprojected_${fileToProcess.name}`,
      graticule_spacing: formData.graticule_spacing,
      scale_bar_km: formData.scale_bar_km,
    };

    const result = await execute(fileToProcess, options);

    if (result) {
      setResultBlob(result);
      setResultFilename(options.output_filename);
      toaster.show({ message: 'Reprojektion erfolgreich!', intent: Intent.SUCCESS, icon: 'tick' });
    } else if (error) {
      toaster.show({ message: `Fehler: ${error}`, intent: Intent.DANGER, icon: 'error', timeout: 5000 });
    }
  };

  return (
    <div className="reproject-tool">
      <div className="tool-layout">
        <div className="tool-controls">
          <FileUploadZone onFileSelect={handleFileSelect} currentFile={svgFile} disabled={loading} />
          
          {!svgFile && (
            <Callout intent={Intent.PRIMARY} icon="info-sign">
              Standard Plate Carrée wird verwendet.
            </Callout>
          )}
          
          {svgFile && (
            <Button text="Standard-Karte verwenden" icon="reset" onClick={useDefaultMap} variant="minimal" />
          )}
          
          <ReprojectionForm onSubmit={handleSubmit} disabled={loading} />
        </div>

        <div className="tool-previews">
          <SVGPreview svgDataURL={svgDataURL} title="Eingabe SVG" isLoading={false} />
          <SVGPreview svgBlob={resultBlob} filename={resultFilename} title="Reprojiziert" isLoading={loading} />
        </div>
      </div>
    </div>
  );
};
