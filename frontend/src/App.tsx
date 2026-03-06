import { useState, useEffect } from 'react';
import { Navbar, NavbarGroup, NavbarHeading, NavbarDivider, Button, Alignment, Tag, Intent } from '@blueprintjs/core';
import { MapProvider } from './context/MapContext';
import { MapPage } from './components/MapPage';
import { ReprojectTool } from './components/ReprojectTool';
import { ExtractTool } from './components/ExtractTool';
import { DownloadPage } from './components/DownloadPage';
import { healthCheck } from './api/apiService';
import './App.scss';

type Page = 'map' | 'reproject' | 'extract' | 'download';

function App() {
  const [currentPage, setCurrentPage] = useState<Page>('map');
  const [apiStatus, setApiStatus] = useState<'checking' | 'healthy' | 'error'>('checking');

  useEffect(() => {
    healthCheck()
      .then((response) => {
        if (response.status === 'healthy') {
          setApiStatus('healthy');
        } else {
          setApiStatus('error');
        }
      })
      .catch(() => {
        setApiStatus('error');
      });
  }, []);

  const renderPage = () => {
    switch (currentPage) {
      case 'map':
        return <MapPage />;
      case 'reproject':
        return <ReprojectTool />;
      case 'extract':
        return <ExtractTool />;
      case 'download':
        return <DownloadPage />;
    }
  };

  return (
    <MapProvider>
      <div className="bp5-dark">
        <Navbar fixedToTop>
          <NavbarGroup align="left">
            <NavbarHeading>CartA</NavbarHeading>
            <NavbarDivider />
            <Button
              icon="globe"
              text="Karte"
              active={currentPage === 'map'}
              onClick={() => setCurrentPage('map')}
              variant="minimal"
            />
            <Button
              icon="refresh"
              text="Reprojektion"
              active={currentPage === 'reproject'}
              onClick={() => setCurrentPage('reproject')}
              variant="minimal"
            />
            <Button
              icon="map"
              text="Ausschnitt"
              active={currentPage === 'extract'}
              onClick={() => setCurrentPage('extract')}
              variant="minimal"
            />
            <Button
              icon="download"
              text="Downloads"
              active={currentPage === 'download'}
              onClick={() => setCurrentPage('download')}
              variant="minimal"
            />
          </NavbarGroup>
          <NavbarGroup align={Alignment.RIGHT}>
            {apiStatus === 'checking' && (
              <Tag minimal>Prüfe API...</Tag>
            )}
            {apiStatus === 'healthy' && (
              <Tag intent={Intent.SUCCESS} minimal>API verbunden</Tag>
            )}
            {apiStatus === 'error' && (
              <Tag intent={Intent.WARNING} minimal>API getrennt</Tag>
            )}
          </NavbarGroup>
        </Navbar>

        <main>
          {renderPage()}
        </main>
      </div>
    </MapProvider>
  );
}

export default App;
