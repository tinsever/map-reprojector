import React, { useState } from 'react';
import {
  FormGroup,
  HTMLSelect,
  NumericInput,
  Slider,
  Collapse,
  Button,
  Card,
} from '@blueprintjs/core';
import type { ProjectionDirection, ProjectionOrientation, ReprojectionFormData } from '../api/types';

export type { ReprojectionFormData };

export interface ReprojectionFormProps {
  onSubmit: (data: ReprojectionFormData) => void;
  disabled?: boolean;
}

export const ReprojectionForm: React.FC<ReprojectionFormProps> = ({
  onSubmit,
  disabled = false,
}) => {
  const [direction, setDirection] = useState<ProjectionDirection>('plate-to-equal');
  const [orientation, setOrientation] = useState<ProjectionOrientation>('normal');
  const [outputWidth, setOutputWidth] = useState(1800);
  const [padding, setPadding] = useState(0);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [graticuleSpacing, setGraticuleSpacing] = useState<number | undefined>(undefined);
  const [scaleBarKm, setScaleBarKm] = useState<number | undefined>(undefined);
  
  const [minLon, setMinLon] = useState(-180);
  const [minLat, setMinLat] = useState(-90);
  const [maxLon, setMaxLon] = useState(180);
  const [maxLat, setMaxLat] = useState(90);

  const handleSubmit = () => {
    onSubmit({
      direction,
      orientation,
      input_bounds: [minLon, minLat, maxLon, maxLat],
      output_width: outputWidth,
      padding,
      graticule_spacing: graticuleSpacing,
      scale_bar_km: scaleBarKm,
    });
  };

  return (
    <Card>
      <FormGroup label="Richtung">
        <HTMLSelect
          value={direction}
          onChange={(e) => setDirection(e.target.value as ProjectionDirection)}
          disabled={disabled}
          fill
        >
          <option value="plate-to-equal">Plate Carrée → Equal Earth</option>
          <option value="equal-to-plate">Equal Earth → Plate Carrée</option>
          <option value="plate-to-wagner">Plate Carrée → Wagner VII</option>
          <option value="equal-to-wagner">Equal Earth → Wagner VII</option>
        </HTMLSelect>
      </FormGroup>

      <FormGroup label="Ausgabebreite (px)">
        <NumericInput
          value={outputWidth}
          onValueChange={setOutputWidth}
          min={100}
          max={10000}
          stepSize={100}
          disabled={disabled}
          fill
        />
      </FormGroup>

      <FormGroup label="Ausrichtung">
        <HTMLSelect
          value={orientation}
          onChange={(e) => setOrientation(e.target.value as ProjectionOrientation)}
          disabled={disabled}
          fill
        >
          <option value="normal">Normal</option>
          <option value="upside-down">Upside Down</option>
          <option value="mirrored">Spiegeln (horizontal)</option>
          <option value="rotated-180">180° drehen</option>
        </HTMLSelect>
      </FormGroup>

      <FormGroup label={`Padding: ${padding.toFixed(2)}`}>
        <Slider
          value={padding}
          onChange={setPadding}
          min={0}
          max={0.5}
          stepSize={0.01}
          labelStepSize={0.1}
          disabled={disabled}
        />
      </FormGroup>

      <FormGroup label="Gitternetz (°)" helperText="z.B. 10 für alle 10°">
        <NumericInput
          value={graticuleSpacing ?? ''}
          onValueChange={(value) => setGraticuleSpacing(value > 0 ? value : undefined)}
          disabled={disabled}
          placeholder="Kein Gitternetz"
          min={1}
          max={90}
          stepSize={5}
          allowNumericCharactersOnly
          fill
        />
      </FormGroup>

      <FormGroup label="Maßstab (km)" helperText="z.B. 500 für 500 km">
        <NumericInput
          value={scaleBarKm ?? ''}
          onValueChange={(value) => setScaleBarKm(value > 0 ? value : undefined)}
          disabled={disabled}
          placeholder="Kein Maßstab"
          min={1}
          max={10000}
          stepSize={100}
          allowNumericCharactersOnly
          fill
        />
      </FormGroup>

      <Button
        text={showAdvanced ? 'Erweitert ausblenden' : 'Erweitert anzeigen'}
        icon={showAdvanced ? 'chevron-up' : 'chevron-down'}
        minimal
        onClick={() => setShowAdvanced(!showAdvanced)}
        style={{ marginBottom: 10 }}
      />

      <Collapse isOpen={showAdvanced}>
        <Card elevation={1}>
          <h4>Eingabe-Bounds</h4>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <FormGroup label="Min Längengrad">
              <NumericInput
                value={minLon}
                onValueChange={setMinLon}
                min={-180}
                max={180}
                disabled={disabled}
                fill
              />
            </FormGroup>
            <FormGroup label="Min Breitengrad">
              <NumericInput
                value={minLat}
                onValueChange={setMinLat}
                min={-90}
                max={90}
                disabled={disabled}
                fill
              />
            </FormGroup>
            <FormGroup label="Max Längengrad">
              <NumericInput
                value={maxLon}
                onValueChange={setMaxLon}
                min={-180}
                max={180}
                disabled={disabled}
                fill
              />
            </FormGroup>
            <FormGroup label="Max Breitengrad">
              <NumericInput
                value={maxLat}
                onValueChange={setMaxLat}
                min={-90}
                max={90}
                disabled={disabled}
                fill
              />
            </FormGroup>
          </div>
        </Card>
      </Collapse>

      <Button
        text="Reprojizieren"
        intent="primary"
        icon="refresh"
        onClick={handleSubmit}
        disabled={disabled}
        large
        fill
        style={{ marginTop: 20 }}
      />
    </Card>
  );
};
