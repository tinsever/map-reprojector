import React, { useCallback, useState } from 'react';
import { Card, FileInput, Callout, Intent, NonIdealState } from '@blueprintjs/core';
import { validateSVG } from '../utils/svgUtils';

interface FileUploadZoneProps {
  onFileSelect: (file: File | null) => void;
  accept?: string;
  disabled?: boolean;
  currentFile?: File | null;
}

export const FileUploadZone: React.FC<FileUploadZoneProps> = ({
  onFileSelect,
  accept = '.svg',
  disabled = false,
  currentFile,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFile = useCallback(
    (file: File | null) => {
      setError(null);
      if (!file) {
        onFileSelect(null);
        return;
      }
      if (!validateSVG(file)) {
        setError('Bitte eine gültige SVG-Datei wählen');
        return;
      }
      onFileSelect(file);
    },
    [onFileSelect]
  );

  const handleFileInput = useCallback(
    (event: React.FormEvent<HTMLInputElement>) => {
      const files = (event.target as HTMLInputElement).files;
      if (files && files.length > 0) {
        handleFile(files[0]);
      }
    },
    [handleFile]
  );

  const handleDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    if (!disabled) setIsDragging(true);
  }, [disabled]);

  const handleDragLeave = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      setIsDragging(false);
      if (disabled) return;
      const files = event.dataTransfer.files;
      if (files && files.length > 0) {
        handleFile(files[0]);
      }
    },
    [disabled, handleFile]
  );

  return (
    <>
      <Card
        interactive={!disabled}
        elevation={isDragging ? 3 : 1}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        style={{ opacity: disabled ? 0.5 : 1 }}
      >
        <NonIdealState
          icon="upload"
          title="SVG hochladen"
          description="Per Drag & Drop oder Datei auswählen"
          action={
            <FileInput
              text={currentFile ? currentFile.name : 'Datei wählen...'}
              onInputChange={handleFileInput}
              inputProps={{ accept }}
              disabled={disabled}
            />
          }
        />
      </Card>

      {currentFile && (
        <Callout intent={Intent.SUCCESS} icon="tick">
          <strong>{currentFile.name}</strong> ({(currentFile.size / 1024).toFixed(1)} KB)
        </Callout>
      )}

      {error && (
        <Callout intent={Intent.DANGER} icon="error">{error}</Callout>
      )}
    </>
  );
};
