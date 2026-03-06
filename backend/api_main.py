"""
CartA - Unified Map Reprojection and Export API

This API provides endpoints for:
- SVG map reprojection (Plate Carrée ↔ Equal Earth)
- Map section extraction with custom projections
- Geographic coordinate transformations
"""

from flask import Flask, request, send_file, jsonify, send_from_directory
from flask_restx import Api, Resource, fields, reqparse
from flask_cors import CORS
import tempfile
import os
import sys
import json
import re
import logging
from pathlib import Path
import traceback
import glob
from xml.etree import ElementTree as ET

# Import the reprojection and extraction functions from packages
from reprojection import (
    plate_to_equal_reproject,
    equal_to_plate_reproject,
    plate_to_wagner_reproject,
    equal_to_wagner_reproject,
)
from extraction import extract_map_section, get_map_section_centered

def _parse_cors_origins(raw_value: str):
    if not raw_value or raw_value.strip() == '*':
        return '*'
    origins = [origin.strip() for origin in raw_value.split(',') if origin.strip()]
    return origins or '*'


logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))

# Initialize Flask app
app = Flask(__name__)
CORS(app, origins=_parse_cors_origins(os.getenv('CORS_ORIGINS', '*')))

# Initialize API with documentation
api = Api(
    app,
    version='1.0',
    title='CartA Map Reprojection API',
    description='API for SVG map reprojection between Plate Carrée and Equal Earth projections, and extracting map sections with custom projections',
    doc='/docs',
    prefix='/api'
)

# Define namespaces
ns_reproject = api.namespace('reproject', description='Map reprojection operations')
ns_extract = api.namespace('extract', description='Map section extraction operations')
ns_health = api.namespace('health', description='Health check operations')
ns_files = api.namespace('files', description='File operations')

VALID_ORIENTATIONS = ['normal', 'upside-down', 'mirrored', 'rotated-180']


@app.route('/api/', methods=['GET'])
def api_index():
    return jsonify({
        'service': 'CartA Map API',
        'status': 'ok',
        'docs_url': '/docs',
        'openapi_url': '/swagger.json',
        'endpoints': {
            'health': '/api/health/',
            'files': '/api/files/',
            'reproject': '/api/reproject/',
            'extract_corners': '/api/extract/corners',
            'extract_center': '/api/extract/center',
        },
    }), 200


def _parse_svg_length(value, fallback):
    if value is None:
        return fallback
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r'-?\d*\.?\d+', str(value))
    return float(match.group(0)) if match else fallback


def _svg_local_name(tag: str) -> str:
    if '}' in tag:
        return tag.split('}', 1)[1]
    return tag


def apply_svg_orientation(svg_path: str, orientation: str) -> None:
    if orientation == 'normal':
        return

    tree = ET.parse(svg_path)
    root = tree.getroot()

    viewbox = root.get('viewBox')
    if viewbox:
        vb_parts = viewbox.split()
        if len(vb_parts) >= 4:
            min_x = float(vb_parts[0])
            min_y = float(vb_parts[1])
            width = float(vb_parts[2])
            height = float(vb_parts[3])
        else:
            width = _parse_svg_length(root.get('width'), 1800.0)
            height = _parse_svg_length(root.get('height'), 900.0)
            min_x, min_y = 0.0, 0.0
    else:
        width = _parse_svg_length(root.get('width'), 1800.0)
        height = _parse_svg_length(root.get('height'), 900.0)
        min_x, min_y = 0.0, 0.0
        root.set('viewBox', f'{min_x} {min_y} {width} {height}')

    center_x = min_x + (width / 2)
    center_y = min_y + (height / 2)

    if orientation == 'upside-down':
        transform = f'translate({center_x} {center_y}) scale(1 -1) translate({-center_x} {-center_y})'
    elif orientation == 'mirrored':
        transform = f'translate({center_x} {center_y}) scale(-1 1) translate({-center_x} {-center_y})'
    elif orientation == 'rotated-180':
        transform = f'translate({center_x} {center_y}) scale(-1 -1) translate({-center_x} {-center_y})'
    else:
        raise ValueError(f'Invalid orientation: {orientation}')

    namespace_match = re.match(r'\{([^}]+)\}', root.tag)
    namespace = namespace_match.group(1) if namespace_match else ''
    group_tag = f'{{{namespace}}}g' if namespace else 'g'

    transform_group = ET.Element(group_tag)
    transform_group.set('transform', transform)

    static_tags = {'defs', 'style', 'title', 'desc', 'metadata', 'script'}
    children = list(root)
    for child in children:
        local_name = _svg_local_name(child.tag)
        if local_name not in static_tags:
            root.remove(child)
            transform_group.append(child)

    root.append(transform_group)
    tree.write(svg_path, encoding='utf-8', xml_declaration=True)

# Define models for Swagger documentation
reproject_model = api.model('ReprojectRequest', {
    'direction': fields.String(
        required=True,
        description='Reprojection direction',
        enum=[
            'plate-to-equal',
            'equal-to-plate',
            'plate-to-wagner',
            'equal-to-wagner',
        ],
        example='plate-to-equal'
    ),
    'input_bounds': fields.List(
        fields.Float,
        required=False,
        description='Geographic bounds [min_lon, min_lat, max_lon, max_lat]',
        example=[-180, -90, 180, 90],
        default=[-180, -90, 180, 90]
    ),
    'output_width': fields.Integer(
        required=False,
        description='Output width in pixels',
        example=1800,
        default=1800
    ),
    'padding': fields.Float(
        required=False,
        description='Padding fraction around output',
        example=0.0,
        default=0.0
    ),
    'output_filename': fields.String(
        required=False,
        description='Output filename for download',
        example='reprojected_map.svg',
        default='reprojected_map.svg'
    ),
    'graticule_spacing': fields.Float(
        required=False,
        description='Spacing between graticule lines in degrees (e.g., 10 for 10°)',
        example=10.0
    ),
    'scale_bar_km': fields.Float(
        required=False,
        description='Scale bar distance in kilometers',
        example=100.0
    ),
    'orientation': fields.String(
        required=False,
        description='Output orientation',
        enum=VALID_ORIENTATIONS,
        example='normal',
        default='normal'
    )
})

extract_corner_model = api.model('ExtractCornerRequest', {
    'top_left': fields.List(
        fields.Float,
        required=True,
        description='Top-left corner [longitude, latitude]',
        example=[-10, 70]
    ),
    'bottom_right': fields.List(
        fields.Float,
        required=True,
        description='Bottom-right corner [longitude, latitude]',
        example=[40, 35]
    ),
    'input_bounds': fields.List(
        fields.Float,
        required=False,
        description='Input geographic bounds [min_lon, min_lat, max_lon, max_lat]',
        example=[-180, -90, 180, 90],
        default=[-180, -90, 180, 90]
    ),
    'output_width': fields.Integer(
        required=False,
        description='Output width in pixels',
        example=800
    ),
    'reproject': fields.Boolean(
        required=False,
        description='Apply centered projection for minimal distortion',
        example=True,
        default=True
    ),
    'projection': fields.String(
        required=False,
        description='Projection type',
        enum=['aeqd', 'laea', 'ortho', 'stere', 'lcc', 'tmerc'],
        example='aeqd',
        default='aeqd'
    ),
    'output_filename': fields.String(
        required=False,
        description='Output filename for download',
        example='map_section.svg',
        default='map_section.svg'
    ),
    'graticule_spacing': fields.Float(
        required=False,
        description='Spacing between graticule lines in degrees (e.g., 10 for 10°)',
        example=10.0
    ),
    'scale_bar_km': fields.Float(
        required=False,
        description='Scale bar distance in kilometers',
        example=100.0
    )
})

extract_center_model = api.model('ExtractCenterRequest', {
    'center': fields.List(
        fields.Float,
        required=True,
        description='Center point [longitude, latitude]',
        example=[10.5, 51.0]
    ),
    'span_lon': fields.Float(
        required=True,
        description='Longitude span in degrees',
        example=15.0
    ),
    'span_lat': fields.Float(
        required=True,
        description='Latitude span in degrees',
        example=10.0
    ),
    'input_bounds': fields.List(
        fields.Float,
        required=False,
        description='Input geographic bounds [min_lon, min_lat, max_lon, max_lat]',
        example=[-180, -90, 180, 90],
        default=[-180, -90, 180, 90]
    ),
    'output_width': fields.Integer(
        required=False,
        description='Output width in pixels',
        example=800
    ),
    'reproject': fields.Boolean(
        required=False,
        description='Apply centered projection for minimal distortion',
        example=True,
        default=True
    ),
    'projection': fields.String(
        required=False,
        description='Projection type',
        enum=['aeqd', 'laea', 'ortho', 'stere', 'lcc', 'tmerc'],
        example='aeqd',
        default='aeqd'
    ),
    'output_filename': fields.String(
        required=False,
        description='Output filename for download',
        example='map_section.svg',
        default='map_section.svg'
    ),
    'graticule_spacing': fields.Float(
        required=False,
        description='Spacing between graticule lines in degrees (e.g., 10 for 10°)',
        example=10.0
    ),
    'scale_bar_km': fields.Float(
        required=False,
        description='Scale bar distance in kilometers',
        example=100.0
    )
})


@ns_health.route('/')
class Health(Resource):
    @api.doc('health_check')
    def get(self):
        """Health check endpoint"""
        return {'status': 'healthy', 'service': 'CartA Map API'}, 200


@ns_reproject.route('/')
class Reproject(Resource):
    @api.doc('reproject_svg')
    @api.expect(reproject_model)
    @api.response(200, 'Success - Returns reprojected SVG file')
    @api.response(400, 'Bad Request - Invalid parameters')
    @api.response(404, 'Not Found - Input file not found')
    @api.response(500, 'Internal Server Error')
    def post(self):
        """
        Reproject an SVG map between Plate Carrée, Equal Earth, and Wagner VII projections
        
        Supports file upload (multipart/form-data) or JSON request with input_svg path.
        
        **Directions:**
        - `plate-to-equal`: Convert from Plate Carrée to Equal Earth
        - `equal-to-plate`: Convert from Equal Earth to Plate Carrée
        - `plate-to-wagner`: Convert from Plate Carrée to Wagner VII
        - `equal-to-wagner`: Convert from Equal Earth to Wagner VII
        
        **Example with file upload (multipart/form-data):**
        - Upload file with key 'file'
        - Include other parameters as form fields
        
        **Example with JSON:**
        ```json
        {
            "input_svg": "Weltkarte.svg",
            "direction": "plate-to-equal",
            "input_bounds": [-180, -90, 180, 90],
            "output_width": 1800,
            "padding": 0.0
        }
        ```
        """
        tmp_input_path = None
        output_svg = None
        
        try:
            # Check if file is uploaded (multipart/form-data)
            if 'file' in request.files:
                uploaded_file = request.files['file']
                if uploaded_file.filename:
                    # Save uploaded file temporarily
                    tmp_input_path = tempfile.NamedTemporaryFile(delete=False, suffix='.svg').name
                    uploaded_file.save(tmp_input_path)
                    input_svg = tmp_input_path
                else:
                    return {'error': 'No file selected'}, 400
                
                # Get parameters from form data
                direction = request.form.get('direction', 'plate-to-equal')
                input_bounds_str = request.form.get('input_bounds', '[-180, -90, 180, 90]')
                input_bounds = tuple(json.loads(input_bounds_str))
                output_width = int(request.form.get('output_width', 1800))
                padding = float(request.form.get('padding', 0.0))
                output_filename = request.form.get('output_filename', 'reprojected_map.svg')
                graticule_spacing = float(request.form.get('graticule_spacing')) if request.form.get('graticule_spacing') else None
                scale_bar_km = float(request.form.get('scale_bar_km')) if request.form.get('scale_bar_km') else None
                orientation = request.form.get('orientation', 'normal')
            else:
                # JSON request
                data = request.get_json()
                if not data:
                    return {'error': 'No JSON data or file provided'}, 400
                
                input_svg = data.get('input_svg', 'Weltkarte.svg')
                direction = data.get('direction', 'plate-to-equal')
                input_bounds = tuple(data.get('input_bounds', [-180, -90, 180, 90]))
                output_width = data.get('output_width', 1800)
                padding = data.get('padding', 0.0)
                output_filename = data.get('output_filename', 'reprojected_map.svg')
                graticule_spacing = data.get('graticule_spacing')
                scale_bar_km = data.get('scale_bar_km')
                orientation = data.get('orientation', 'normal')
            
            # Validate direction
            valid_directions = [
                'plate-to-equal',
                'equal-to-plate',
                'plate-to-wagner',
                'equal-to-wagner',
            ]
            if direction not in valid_directions:
                return {
                    'error': 'Invalid direction. Must be one of: ' + ', '.join(valid_directions)
                }, 400

            if orientation not in VALID_ORIENTATIONS:
                return {
                    'error': 'Invalid orientation. Must be one of: ' + ', '.join(VALID_ORIENTATIONS)
                }, 400
            
            # Check if input file exists
            if not os.path.exists(input_svg):
                return {'error': f'Input SVG file not found: {input_svg}'}, 404
            
            # Create temporary output file
            output_svg = tempfile.NamedTemporaryFile(delete=False, suffix='.svg').name
            
            # Perform reprojection
            if direction == 'plate-to-equal':
                plate_to_equal_reproject(
                    input_svg=input_svg,
                    output_svg=output_svg,
                    input_bounds=input_bounds,
                    output_width=output_width,
                    padding=padding,
                    graticule_spacing=graticule_spacing,
                    scale_bar_km=scale_bar_km
                )
            elif direction == 'equal-to-plate':
                equal_to_plate_reproject(
                    input_svg=input_svg,
                    output_svg=output_svg,
                    input_bounds=input_bounds,
                    output_width=output_width,
                    padding=padding,
                    graticule_spacing=graticule_spacing,
                    scale_bar_km=scale_bar_km
                )
            elif direction == 'plate-to-wagner':
                plate_to_wagner_reproject(
                    input_svg=input_svg,
                    output_svg=output_svg,
                    input_bounds=input_bounds,
                    output_width=output_width,
                    padding=padding,
                    graticule_spacing=graticule_spacing,
                    scale_bar_km=scale_bar_km
                )
            elif direction == 'equal-to-wagner':
                equal_to_wagner_reproject(
                    input_svg=input_svg,
                    output_svg=output_svg,
                    input_bounds=input_bounds,
                    output_width=output_width,
                    padding=padding,
                    graticule_spacing=graticule_spacing,
                    scale_bar_km=scale_bar_km
                )
            else:
                # This should never happen due to validation above, but just in case
                return {
                    'error': f'Unsupported direction: {direction}'
                }, 400

            apply_svg_orientation(output_svg, orientation)
            
            # Check if output file was created
            if not os.path.exists(output_svg):
                return {
                    'error': f'Output file was not created: {output_svg}'
                }, 500
            
            # Return the SVG file
            return send_file(
                output_svg,
                mimetype='image/svg+xml',
                as_attachment=True,
                download_name=output_filename
            )
        
        except Exception as e:
            tb = traceback.format_exc()
            app.logger.exception("Reprojection failed")
            # Cleanup output file on error
            if output_svg and os.path.exists(output_svg):
                try:
                    os.unlink(output_svg)
                except:
                    pass
            return {
                'error': str(e),
                'traceback': tb
            }, 500
        
        finally:
            # Cleanup temporary input file
            if tmp_input_path and os.path.exists(tmp_input_path):
                try:
                    os.unlink(tmp_input_path)
                except:
                    pass


@ns_extract.route('/corners')
class ExtractCorners(Resource):
    @api.doc('extract_corners')
    @api.expect(extract_corner_model)
    @api.response(200, 'Success - Returns extracted map section')
    @api.response(400, 'Bad Request - Invalid parameters')
    @api.response(404, 'Not Found - Input file not found')
    @api.response(500, 'Internal Server Error')
    def post(self):
        """
        Extract a map section using corner coordinates
        
        Extracts a rectangular section from a Plate Carrée SVG map and optionally
        reprojects it to a centered projection for minimal distortion.
        
        **Projections:**
        - `aeqd`: Azimuthal Equidistant (preserves distances from center)
        - `laea`: Lambert Azimuthal Equal-Area (preserves areas)
        - `ortho`: Orthographic (globe view)
        - `stere`: Stereographic (preserves angles)
        - `lcc`: Lambert Conformal Conic (preserves local angles)
        - `tmerc`: Transverse Mercator (conformal, good near central meridian)
        
        **Example with file upload:**
        - Upload file with key 'file'
        - Include other parameters as form fields (JSON strings for arrays)
        
        **Example with JSON:**
        ```json
        {
            "input_svg": "Weltkarte.svg",
            "top_left": [-10, 70],
            "bottom_right": [40, 35],
            "output_width": 800,
            "reproject": true,
            "projection": "aeqd"
        }
        ```
        """
        tmp_input_path = None
        output_svg = None
        
        try:
            # Check if file is uploaded
            if 'file' in request.files:
                uploaded_file = request.files['file']
                if uploaded_file.filename:
                    tmp_input_path = tempfile.NamedTemporaryFile(delete=False, suffix='.svg').name
                    uploaded_file.save(tmp_input_path)
                    input_svg = tmp_input_path
                else:
                    return {'error': 'No file selected'}, 400
                
                # Parse form data
                top_left = json.loads(request.form.get('top_left'))
                bottom_right = json.loads(request.form.get('bottom_right'))
                input_bounds = tuple(json.loads(request.form.get('input_bounds', '[-180, -90, 180, 90]')))
                output_width = int(request.form.get('output_width')) if request.form.get('output_width') else None
                reproject = request.form.get('reproject', 'true').lower() == 'true'
                projection = request.form.get('projection', 'aeqd')
                output_filename = request.form.get('output_filename', 'map_section.svg')
                graticule_spacing = float(request.form.get('graticule_spacing')) if request.form.get('graticule_spacing') else None
                scale_bar_km = float(request.form.get('scale_bar_km')) if request.form.get('scale_bar_km') else None
            else:
                # JSON request
                data = request.get_json()
                if not data:
                    return {'error': 'No JSON data or file provided'}, 400
                
                input_svg = data.get('input_svg', 'Weltkarte.svg')
                top_left = data.get('top_left')
                bottom_right = data.get('bottom_right')
                input_bounds = tuple(data.get('input_bounds', [-180, -90, 180, 90]))
                output_width = data.get('output_width')
                reproject = data.get('reproject', True)
                projection = data.get('projection', 'aeqd')
                output_filename = data.get('output_filename', 'map_section.svg')
                graticule_spacing = data.get('graticule_spacing')
                scale_bar_km = data.get('scale_bar_km')
            
            # Validate required parameters
            if not top_left or not bottom_right:
                return {'error': 'top_left and bottom_right coordinates are required'}, 400
            
            # Check if input file exists
            if not os.path.exists(input_svg):
                return {'error': f'Input SVG file not found: {input_svg}'}, 404
            
            # Create temporary output file
            output_svg = tempfile.NamedTemporaryFile(delete=False, suffix='.svg').name
            
            # Extract map section
            extract_map_section(
                input_svg=input_svg,
                output_svg=output_svg,
                top_left=tuple(top_left),
                bottom_right=tuple(bottom_right),
                input_bounds=input_bounds,
                output_width=output_width,
                reproject=reproject,
                projection=projection,
                graticule_spacing=graticule_spacing,
                scale_bar_km=scale_bar_km
            )
            
            # Return the SVG file
            return send_file(
                output_svg,
                mimetype='image/svg+xml',
                as_attachment=True,
                download_name=output_filename
            )
        
        except Exception as e:
            return {
                'error': str(e),
                'traceback': traceback.format_exc()
            }, 500
        
        finally:
            # Cleanup temporary input file
            if tmp_input_path and os.path.exists(tmp_input_path):
                try:
                    os.unlink(tmp_input_path)
                except:
                    pass


@ns_extract.route('/center')
class ExtractCenter(Resource):
    @api.doc('extract_center')
    @api.expect(extract_center_model)
    @api.response(200, 'Success - Returns extracted map section')
    @api.response(400, 'Bad Request - Invalid parameters')
    @api.response(404, 'Not Found - Input file not found')
    @api.response(500, 'Internal Server Error')
    def post(self):
        """
        Extract a map section using center point and span
        
        Extracts a map section centered on a specific point with defined longitude
        and latitude spans. Optionally reprojects to a centered projection.
        
        **Projections:**
        - `aeqd`: Azimuthal Equidistant (preserves distances from center)
        - `laea`: Lambert Azimuthal Equal-Area (preserves areas)
        - `ortho`: Orthographic (globe view)
        - `stere`: Stereographic (preserves angles)
        - `lcc`: Lambert Conformal Conic (preserves local angles)
        - `tmerc`: Transverse Mercator (conformal, good near central meridian)
        
        **Example:**
        ```json
        {
            "input_svg": "Weltkarte.svg",
            "center": [10.5, 51.0],
            "span_lon": 15.0,
            "span_lat": 10.0,
            "output_width": 600,
            "reproject": true,
            "projection": "laea"
        }
        ```
        """
        tmp_input_path = None
        output_svg = None
        
        try:
            # Check if file is uploaded
            if 'file' in request.files:
                uploaded_file = request.files['file']
                if uploaded_file.filename:
                    tmp_input_path = tempfile.NamedTemporaryFile(delete=False, suffix='.svg').name
                    uploaded_file.save(tmp_input_path)
                    input_svg = tmp_input_path
                else:
                    return {'error': 'No file selected'}, 400
                
                # Parse form data
                center = json.loads(request.form.get('center'))
                span_lon = float(request.form.get('span_lon'))
                span_lat = float(request.form.get('span_lat'))
                input_bounds = tuple(json.loads(request.form.get('input_bounds', '[-180, -90, 180, 90]')))
                output_width = int(request.form.get('output_width')) if request.form.get('output_width') else None
                reproject = request.form.get('reproject', 'true').lower() == 'true'
                projection = request.form.get('projection', 'aeqd')
                output_filename = request.form.get('output_filename', 'map_section.svg')
                graticule_spacing = float(request.form.get('graticule_spacing')) if request.form.get('graticule_spacing') else None
                scale_bar_km = float(request.form.get('scale_bar_km')) if request.form.get('scale_bar_km') else None
            else:
                # JSON request
                data = request.get_json()
                if not data:
                    return {'error': 'No JSON data or file provided'}, 400
                
                input_svg = data.get('input_svg', 'Weltkarte.svg')
                center = data.get('center')
                span_lon = data.get('span_lon')
                span_lat = data.get('span_lat')
                input_bounds = tuple(data.get('input_bounds', [-180, -90, 180, 90]))
                output_width = data.get('output_width')
                reproject = data.get('reproject', True)
                projection = data.get('projection', 'aeqd')
                output_filename = data.get('output_filename', 'map_section.svg')
                graticule_spacing = data.get('graticule_spacing')
                scale_bar_km = data.get('scale_bar_km')
            
            # Validate required parameters
            if not center or span_lon is None or span_lat is None:
                return {'error': 'center, span_lon, and span_lat are required'}, 400
            
            # Check if input file exists
            if not os.path.exists(input_svg):
                return {'error': f'Input SVG file not found: {input_svg}'}, 404
            
            # Create temporary output file
            output_svg = tempfile.NamedTemporaryFile(delete=False, suffix='.svg').name
            
            # Extract map section
            get_map_section_centered(
                input_svg=input_svg,
                output_svg=output_svg,
                center=tuple(center),
                span_lon=float(span_lon),
                span_lat=float(span_lat),
                input_bounds=input_bounds,
                output_width=output_width,
                reproject=reproject,
                projection=projection,
                graticule_spacing=graticule_spacing,
                scale_bar_km=scale_bar_km
            )
            
            # Return the SVG file
            return send_file(
                output_svg,
                mimetype='image/svg+xml',
                as_attachment=True,
                download_name=output_filename
            )
        
        except Exception as e:
            return {
                'error': str(e),
                'traceback': traceback.format_exc()
            }, 500
        
        finally:
            # Cleanup temporary input file
            if tmp_input_path and os.path.exists(tmp_input_path):
                try:
                    os.unlink(tmp_input_path)
                except:
                    pass


# Define directories to search for files
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads')
ASSETS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'deploy', 'assets')

@ns_files.route('/')
class FileList(Resource):
    @api.doc('list_files')
    def get(self):
        """List available map files"""
        files = []
        
        # Helper to add files from directory
        def add_files_from_dir(directory, source_name):
            if os.path.exists(directory):
                for filepath in glob.glob(os.path.join(directory, '*.svg')):
                    filename = os.path.basename(filepath)
                    stat = os.stat(filepath)
                    files.append({
                        'name': filename,
                        'source': source_name,
                        'size': stat.st_size,
                        'modified': stat.st_mtime
                    })

        add_files_from_dir(UPLOAD_FOLDER, 'uploads')
        # Also include root directory SVG files (like Weltkarte.svg)
        root_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
        for filepath in glob.glob(os.path.join(root_dir, '*.svg')):
             filename = os.path.basename(filepath)
             stat = os.stat(filepath)
             files.append({
                'name': filename,
                'source': 'root',
                'size': stat.st_size,
                'modified': stat.st_mtime
             })

        return {'files': files}, 200

@ns_files.route('/<path:filename>')
class FileDownload(Resource):
    @api.doc('download_file')
    def get(self, filename):
        """Download a map file"""
        # Check root
        root_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
        if os.path.exists(os.path.join(root_dir, filename)):
            return send_from_directory(root_dir, filename, as_attachment=True)
        
        # Check uploads
        if os.path.exists(os.path.join(UPLOAD_FOLDER, filename)):
            return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)
            
        return {'error': 'File not found'}, 404

if __name__ == '__main__':
    debug = os.getenv('FLASK_DEBUG', '0') == '1'
    app.run(debug=debug, host='0.0.0.0', port=5100)
