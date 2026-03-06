import React, { useEffect, useState } from 'react';
import { Card, NonIdealState, Spinner, Callout, Button } from '@blueprintjs/core';
import type { FileItem } from '../api/types';
import { fetchFiles, getDownloadUrl } from '../api/apiService';

export const DownloadPage: React.FC = () => {
  const [files, setFiles] = useState<FileItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchFiles()
      .then((response) => {
        setFiles(response.files);
        setError(null);
      })
      .catch((err: Error) => {
        setError(err.message);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const formatSize = (size: number) => {
    if (size < 1024) return `${size} B`;
    if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="download-page" style={{ padding: '20px', maxWidth: '1000px', margin: '0 auto' }}>
      <h2 className="bp5-heading" style={{ marginBottom: '20px' }}>Downloads</h2>

      {loading && (
        <Card style={{ display: 'flex', justifyContent: 'center', padding: '32px' }}>
          <Spinner />
        </Card>
      )}

      {!loading && error && (
        <Callout intent="danger" title="Could not load files">
          {error}
        </Callout>
      )}

      {!loading && !error && files.length === 0 && (
        <Card>
          <NonIdealState
            icon="folder-open"
            title="No files available"
            description="Upload SVG files or keep sample assets in the repository root to make them downloadable here."
          />
        </Card>
      )}

      {!loading && !error && files.length > 0 && (
        <div style={{ display: 'grid', gap: '12px' }}>
          {files.map((file) => (
            <Card key={`${file.source}:${file.name}`}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '16px', alignItems: 'center' }}>
                <div>
                  <div style={{ fontWeight: 600 }}>{file.name}</div>
                  <div className="bp5-text-muted">
                    {file.source} · {formatSize(file.size)}
                  </div>
                </div>
                <Button
                  icon="download"
                  intent="primary"
                  text="Download"
                  onClick={() => {
                    window.location.href = getDownloadUrl(file.name);
                  }}
                />
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};
