export function validateSVG(file: File): boolean {
  return file.type === 'image/svg+xml' || file.name.endsWith('.svg');
}

export function parseSVGDimensions(svgContent: string): { width: number; height: number } | null {
  try {
    const parser = new DOMParser();
    const doc = parser.parseFromString(svgContent, 'image/svg+xml');
    const svg = doc.querySelector('svg');
    
    if (!svg) return null;
    
    // Try to get dimensions from viewBox
    const viewBox = svg.getAttribute('viewBox');
    if (viewBox) {
      const parts = viewBox.split(/\s+/);
      if (parts.length === 4) {
        return {
          width: parseFloat(parts[2]),
          height: parseFloat(parts[3]),
        };
      }
    }
    
    // Try to get dimensions from width/height attributes
    const width = svg.getAttribute('width');
    const height = svg.getAttribute('height');
    if (width && height) {
      return {
        width: parseFloat(width),
        height: parseFloat(height),
      };
    }
    
    return null;
  } catch (error) {
    console.error('Error parsing SVG:', error);
    return null;
  }
}

/**
 * Convert File to data URL for preview
 */
export function fileToDataURL(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

export function blobToDataURL(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

