export type ProjectionDirection =
  | 'plate-to-equal'
  | 'equal-to-plate'
  | 'plate-to-wagner'
  | 'equal-to-wagner';

export type ProjectionOrientation = 'normal' | 'upside-down' | 'mirrored' | 'rotated-180';

export type ProjectionType = 'aeqd' | 'laea' | 'ortho' | 'stere' | 'lcc' | 'tmerc';

export interface ReprojectOptions {
  direction: ProjectionDirection;
  orientation?: ProjectionOrientation;
  input_bounds?: [number, number, number, number]; // [min_lon, min_lat, max_lon, max_lat]
  output_width?: number;
  padding?: number;
  output_filename?: string;
  graticule_spacing?: number;
  scale_bar_km?: number;
}

export interface ReprojectionFormData {
  direction: ProjectionDirection;
  orientation: ProjectionOrientation;
  input_bounds: [number, number, number, number];
  output_width: number;
  padding: number;
  graticule_spacing?: number;
  scale_bar_km?: number;
}

export type CoordinateMode = 'corners' | 'center';

export interface ExtractionFormData {
  mode: CoordinateMode;
  top_left?: [number, number];
  bottom_right?: [number, number];
  center?: [number, number];
  span_lon?: number;
  span_lat?: number;
  input_bounds: [number, number, number, number];
  output_width?: number;
  reproject: boolean;
  projection: ProjectionType;
}

export interface ExtractCornersParams {
  top_left: [number, number];
  bottom_right: [number, number];
  input_bounds?: [number, number, number, number];
  output_width?: number;
  reproject?: boolean;
  projection?: ProjectionType;
  output_filename?: string;
  graticule_spacing?: number;
  scale_bar_km?: number;
}

export interface ExtractCenterParams {
  center: [number, number];
  span_lon: number;
  span_lat: number;
  input_bounds?: [number, number, number, number];
  output_width?: number;
  reproject?: boolean;
  projection?: ProjectionType;
  output_filename?: string;
  graticule_spacing?: number;
  scale_bar_km?: number;
}

export interface HealthResponse {
  status: string;
  service?: string;
}

export interface ApiError {
  error: string;
  traceback?: string;
}

export interface FileItem {
  name: string;
  source: string;
  size: number;
  modified: number;
}

export interface FileListResponse {
  files: FileItem[];
}
