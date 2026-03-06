import axios, { AxiosError } from 'axios';
import type {
  ReprojectOptions,
  ExtractCornersParams,
  ExtractCenterParams,
  HealthResponse,
  ApiError,
  FileListResponse,
} from './types';

const API_BASE_URL = '/api';

/**
 * Health check endpoint
 */
export async function healthCheck(): Promise<HealthResponse> {
  const response = await axios.get<HealthResponse>(`${API_BASE_URL}/health/`);
  return response.data;
}

/**
 * Fetch list of available map files
 */
export async function fetchFiles(): Promise<FileListResponse> {
  const response = await axios.get<FileListResponse>(`${API_BASE_URL}/files/`);
  return response.data;
}

/**
 * Get download URL for a file
 */
export function getDownloadUrl(filename: string): string {
  return `${API_BASE_URL}/files/${filename}`;
}

/**
 * Reproject SVG between Plate Carrée and Equal Earth
 */
export async function reprojectSVG(
  file: File,
  options: ReprojectOptions
): Promise<Blob> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('direction', options.direction);
  if (options.orientation) {
    formData.append('orientation', options.orientation);
  }
  
  if (options.input_bounds) {
    formData.append('input_bounds', JSON.stringify(options.input_bounds));
  }
  if (options.output_width) {
    formData.append('output_width', options.output_width.toString());
  }
  if (options.padding !== undefined) {
    formData.append('padding', options.padding.toString());
  }
  if (options.output_filename) {
    formData.append('output_filename', options.output_filename);
  }
  if (options.graticule_spacing !== undefined) {
    formData.append('graticule_spacing', options.graticule_spacing.toString());
  }
  if (options.scale_bar_km !== undefined) {
    formData.append('scale_bar_km', options.scale_bar_km.toString());
  }

  const response = await axios.post(`${API_BASE_URL}/reproject/`, formData, {
    responseType: 'blob',
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
}

/**
 * Extract map section using corner coordinates
 */
export async function extractByCorners(
  file: File,
  params: ExtractCornersParams
): Promise<Blob> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('top_left', JSON.stringify(params.top_left));
  formData.append('bottom_right', JSON.stringify(params.bottom_right));
  
  if (params.input_bounds) {
    formData.append('input_bounds', JSON.stringify(params.input_bounds));
  }
  if (params.output_width) {
    formData.append('output_width', params.output_width.toString());
  }
  if (params.reproject !== undefined) {
    formData.append('reproject', params.reproject.toString());
  }
  if (params.projection) {
    formData.append('projection', params.projection);
  }
  if (params.output_filename) {
    formData.append('output_filename', params.output_filename);
  }
  if (params.graticule_spacing !== undefined) {
    formData.append('graticule_spacing', params.graticule_spacing.toString());
  }
  if (params.scale_bar_km !== undefined) {
    formData.append('scale_bar_km', params.scale_bar_km.toString());
  }

  const response = await axios.post(`${API_BASE_URL}/extract/corners`, formData, {
    responseType: 'blob',
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
}

/**
 * Extract map section using center point and span
 */
export async function extractByCenter(
  file: File,
  params: ExtractCenterParams
): Promise<Blob> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('center', JSON.stringify(params.center));
  formData.append('span_lon', params.span_lon.toString());
  formData.append('span_lat', params.span_lat.toString());
  
  if (params.input_bounds) {
    formData.append('input_bounds', JSON.stringify(params.input_bounds));
  }
  if (params.output_width) {
    formData.append('output_width', params.output_width.toString());
  }
  if (params.reproject !== undefined) {
    formData.append('reproject', params.reproject.toString());
  }
  if (params.projection) {
    formData.append('projection', params.projection);
  }
  if (params.output_filename) {
    formData.append('output_filename', params.output_filename);
  }
  if (params.graticule_spacing !== undefined) {
    formData.append('graticule_spacing', params.graticule_spacing.toString());
  }
  if (params.scale_bar_km !== undefined) {
    formData.append('scale_bar_km', params.scale_bar_km.toString());
  }

  const response = await axios.post(`${API_BASE_URL}/extract/center`, formData, {
    responseType: 'blob',
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
}

/**
 * Extract error message from API error
 */
export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<ApiError>;
    if (axiosError.response?.data) {
      // If response is a Blob (error from blob response), try to parse it
      if (axiosError.response.data instanceof Blob) {
        return 'Server error occurred. Please try again.';
      }
      return axiosError.response.data.error || axiosError.message;
    }
    return axiosError.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'An unknown error occurred';
}
