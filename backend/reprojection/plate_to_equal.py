from pyproj import Transformer, Geod
from xml.etree import ElementTree as ET
import re
import logging
import numpy as np

logger = logging.getLogger(__name__)

def generate_graticule_path_equal_earth(
    spacing: float,
    transformer,
    out_min_x: float, out_max_x: float,
    out_min_y: float, out_max_y: float,
    out_width: float, out_height: float
) -> str:
    proj_width = out_max_x - out_min_x
    proj_height = out_max_y - out_min_y
    lines = []
    
    def geo_to_svg(lon, lat):
        try:
            proj_x, proj_y = transformer.transform(lon, lat)
            if not np.isfinite(proj_x) or not np.isfinite(proj_y):
                return None, None
            px = ((proj_x - out_min_x) / proj_width) * out_width
            py = ((out_max_y - proj_y) / proj_height) * out_height
            return px, py
        except:
            return None, None
    
    def is_in_view(px, py):
        if px is None or py is None:
            return False
        margin = 50
        return -margin <= px <= out_width + margin and -margin <= py <= out_height + margin
    
    lat_min_global = -90
    lat_max_global = 90
    lon_min_global = -180
    lon_max_global = 180
    
    lon = np.ceil(lon_min_global / spacing) * spacing
    while lon <= lon_max_global:
        segments = []
        current_segment = []
        lat = lat_min_global
        prev_in_view = False
        
        while lat <= lat_max_global:
            px, py = geo_to_svg(lon, lat)
            in_view = is_in_view(px, py)
            
            if in_view:
                if px is not None and py is not None:
                    current_segment.append((px, py))
            else:
                if current_segment and len(current_segment) >= 2:
                    segments.append(current_segment)
                current_segment = []
            
            prev_in_view = in_view
            lat += spacing / 20
        
        if current_segment and len(current_segment) >= 2:
            segments.append(current_segment)
        
        for segment in segments:
            path = f"M {segment[0][0]:.2f},{segment[0][1]:.2f}"
            for px, py in segment[1:]:
                path += f" L {px:.2f},{py:.2f}"
            lines.append(path)
        
        lon += spacing
    
    lat = np.ceil(lat_min_global / spacing) * spacing
    while lat <= lat_max_global:
        segments = []
        current_segment = []
        lon_i = lon_min_global
        prev_in_view = False
        
        while lon_i <= lon_max_global:
            px, py = geo_to_svg(lon_i, lat)
            in_view = is_in_view(px, py)
            
            if in_view:
                if px is not None and py is not None:
                    current_segment.append((px, py))
            else:
                if current_segment and len(current_segment) >= 2:
                    segments.append(current_segment)
                current_segment = []
            
            prev_in_view = in_view
            lon_i += spacing / 20
        
        if current_segment and len(current_segment) >= 2:
            segments.append(current_segment)
        
        for segment in segments:
            path = f"M {segment[0][0]:.2f},{segment[0][1]:.2f}"
            for px, py in segment[1:]:
                path += f" L {px:.2f},{py:.2f}"
            lines.append(path)
        
        lat += spacing
    
    return ' '.join(lines)


def generate_scale_bar_equal_earth(
    distance_km: float,
    center_lon: float, center_lat: float,
    transformer,
    out_min_x: float, out_max_x: float,
    out_min_y: float, out_max_y: float,
    out_width: float, out_height: float,
    margin: float = 20,
    bar_height: float = 8
) -> tuple:
    proj_width = out_max_x - out_min_x
    proj_height = out_max_y - out_min_y
    
    geod = Geod(ellps='WGS84')
    az, _, _ = geod.inv(center_lon, center_lat, center_lon + 1, center_lat)
    end_lon, end_lat, _ = geod.fwd(center_lon, center_lat, az, distance_km * 1000)
    
    def geo_to_svg(lon, lat):
        try:
            proj_x, proj_y = transformer.transform(lon, lat)
            if not np.isfinite(proj_x) or not np.isfinite(proj_y):
                return None, None
            px = ((proj_x - out_min_x) / proj_width) * out_width
            py = ((out_max_y - proj_y) / proj_height) * out_height
            return px, py
        except:
            return None, None
    
    start_px, start_py = geo_to_svg(center_lon, center_lat)
    end_px, end_py = geo_to_svg(end_lon, end_lat)
    
    if start_px is None or end_px is None:
        return None, 0, 0, 0, 0
    
    bar_length = abs(end_px - start_px)
    
    bar_x = margin
    bar_y = out_height - margin - bar_height
    
    path_d = f"M {bar_x},{bar_y} L {bar_x + bar_length},{bar_y} L {bar_x + bar_length},{bar_y + bar_height} L {bar_x},{bar_y + bar_height} Z"
    
    return path_d, bar_x, bar_y, bar_length, bar_height

def parse_transform(transform_str):
    """Parse SVG transform attribute and return transformation matrix"""
    if not transform_str:
        return np.eye(3)
    
    matrix = np.eye(3)
    
    # Handle matrix()
    matrix_match = re.search(r'matrix\s*\(\s*([^)]+)\s*\)', transform_str)
    if matrix_match:
        values = [float(v) for v in re.split(r'[,\s]+', matrix_match.group(1).strip())]
        if len(values) == 6:
            a, b, c, d, e, f = values
            matrix = np.array([
                [a, c, e],
                [b, d, f],
                [0, 0, 1]
            ])
    
    # Handle translate()
    translate_match = re.search(r'translate\s*\(\s*([^)]+)\s*\)', transform_str)
    if translate_match:
        values = [float(v) for v in re.split(r'[,\s]+', translate_match.group(1).strip())]
        tx, ty = values[0], values[1] if len(values) > 1 else 0
        trans = np.array([
            [1, 0, tx],
            [0, 1, ty],
            [0, 0, 1]
        ])
        matrix = matrix @ trans
    
    # Handle scale()
    scale_match = re.search(r'scale\s*\(\s*([^)]+)\s*\)', transform_str)
    if scale_match:
        values = [float(v) for v in re.split(r'[,\s]+', scale_match.group(1).strip())]
        sx = values[0]
        sy = values[1] if len(values) > 1 else sx
        scale = np.array([
            [sx, 0, 0],
            [0, sy, 0],
            [0, 0, 1]
        ])
        matrix = matrix @ scale
    
    return matrix

def reproject_svg(input_svg, output_svg, input_bounds, output_width=1800, padding=0.0, graticule_spacing=None, scale_bar_km=None):
    """
    Reproject SVG from Plate Carrée (equirectangular) to Equal Earth projection.
    
    Args:
        input_svg: Path to input SVG file (Plate Carrée projection)
        output_svg: Path to output SVG file (Equal Earth projection)
        input_bounds: Tuple (min_lon, min_lat, max_lon, max_lat) - geographic bounds of input
        output_width: Desired output width in pixels (default: 1800)
        padding: Fraction of padding to add around output (0.0 = none, default: 0.0)
    
    Returns:
        None (writes output file)
    """
    # Parse SVG
    tree = ET.parse(input_svg)
    root = tree.getroot()
    
    # Register SVG namespace
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    
    # Get dimensions from viewBox if available (including origin offset)
    viewbox = root.get('viewBox')
    vb_x, vb_y = 0, 0
    if viewbox:
        vb_parts = viewbox.split()
        vb_x = float(vb_parts[0])
        vb_y = float(vb_parts[1])
        width = float(vb_parts[2])
        height = float(vb_parts[3])
    else:
        try:
            w = root.get('width', str(output_width))
            width = float(re.sub(r'[^\d.]', '', w))
        except:
            width = output_width
        
        try:
            h = root.get('height', str(output_width/2))
            height = float(re.sub(r'[^\d.]', '', h))
        except:
            height = width / 2
    
    logger.debug("Input SVG: %s × %s, viewBox origin: (%s, %s)", width, height, vb_x, vb_y)
    
    # Collect transforms from SVG hierarchy
    def collect_transforms(element, current_transform, transforms_map):
        local_transform = parse_transform(element.get('transform'))
        new_transform = current_transform @ local_transform
        transforms_map[element] = new_transform
        for child in element:
            collect_transforms(child, new_transform, transforms_map)
    
    transforms_map = {}
    collect_transforms(root, np.eye(3), transforms_map)
    
    # Create transformers
    forward_transformer = Transformer.from_crs("EPSG:4326", "ESRI:54035", always_xy=True)
    
    # Sample many points along the boundary to get accurate output bounds
    sample_points = []
    steps = 100
    
    # Top and bottom edges
    for i in range(steps + 1):
        lon = input_bounds[0] + (i / steps) * (input_bounds[2] - input_bounds[0])
        sample_points.append(forward_transformer.transform(lon, input_bounds[1]))
        sample_points.append(forward_transformer.transform(lon, input_bounds[3]))
    
    # Left and right edges
    for i in range(steps + 1):
        lat = input_bounds[1] + (i / steps) * (input_bounds[3] - input_bounds[1])
        sample_points.append(forward_transformer.transform(input_bounds[0], lat))
        sample_points.append(forward_transformer.transform(input_bounds[2], lat))
    
    out_min_x = min(p[0] for p in sample_points)
    out_max_x = max(p[0] for p in sample_points)
    out_min_y = min(p[1] for p in sample_points)
    out_max_y = max(p[1] for p in sample_points)
    
    # Add configurable padding
    if padding > 0:
        x_range = out_max_x - out_min_x
        y_range = out_max_y - out_min_y
        out_min_x -= x_range * padding
        out_max_x += x_range * padding
        out_min_y -= y_range * padding
        out_max_y += y_range * padding
    
    # Calculate output dimensions maintaining projection aspect ratio
    proj_aspect = (out_max_x - out_min_x) / (out_max_y - out_min_y)
    out_width = output_width
    out_height = out_width / proj_aspect
    
    logger.debug("Output dimensions: %.0f × %.0f", out_width, out_height)
    
    def apply_transform(x, y, matrix):
        """Apply transformation matrix to point"""
        pt = np.array([x, y, 1])
        result = matrix @ pt
        return result[0], result[1]
    
    def svg_to_geo(x, y):
        """Convert SVG pixel coords to geographic coords (accounting for viewBox origin)"""
        lon = input_bounds[0] + ((x - vb_x) / width) * (input_bounds[2] - input_bounds[0])
        lat = input_bounds[3] - ((y - vb_y) / height) * (input_bounds[3] - input_bounds[1])
        return lon, lat
    
    def geo_to_svg(x, y):
        """Convert reprojected coords back to SVG pixels"""
        px = ((x - out_min_x) / (out_max_x - out_min_x)) * out_width
        py = ((out_max_y - y) / (out_max_y - out_min_y)) * out_height
        return px, py
    
    def transform_point(x, y, element_transform):
        """Transform a point from input SVG to output SVG"""
        # Apply element's cumulative transform
        vb_x_pt, vb_y_pt = apply_transform(x, y, element_transform)
        # Convert to geographic
        lon, lat = svg_to_geo(vb_x_pt, vb_y_pt)
        # Project to Equal Earth
        proj_x, proj_y = forward_transformer.transform(lon, lat)
        # Convert to output SVG coordinates
        return geo_to_svg(proj_x, proj_y)
    
    def get_lon(x, y, element_transform):
        """Get longitude of a point (for antimeridian detection)"""
        vb_x_pt, vb_y_pt = apply_transform(x, y, element_transform)
        lon, lat = svg_to_geo(vb_x_pt, vb_y_pt)
        return lon
    
    def crosses_antimeridian(lon1, lon2, threshold=170):
        """Check if two longitudes cross the antimeridian (180°/-180° boundary)"""
        # If one is near +180 and other near -180, it's a crossing
        return abs(lon1 - lon2) > threshold
    
    def parse_path_commands(d):
        """Parse SVG path into list of (command, params) tuples"""
        commands = []
        # Match command letter followed by its parameters
        pattern = r'([MmLlHhVvCcSsQqTtAaZz])([^MmLlHhVvCcSsQqTtAaZz]*)'
        for match in re.finditer(pattern, d):
            cmd = match.group(1)
            params_str = match.group(2).strip()
            if params_str:
                # Parse numbers (including negative and decimal)
                params = [float(x) for x in re.findall(r'-?[\d.]+(?:[eE][+-]?\d+)?', params_str)]
            else:
                params = []
            commands.append((cmd, params))
        return commands
    
    def transform_path(d, element_transform):
        """Transform path d attribute with proper command handling"""
        commands = parse_path_commands(d)
        new_path = []
        
        # Track current point for relative commands
        current_x, current_y = 0, 0
        start_x, start_y = 0, 0  # For Z command
        
        for cmd, params in commands:
            is_relative = cmd.islower()
            cmd_upper = cmd.upper()
            
            if cmd_upper == 'Z':
                # Close path - check for antimeridian crossing before closing
                curr_lon = get_lon(current_x, current_y, element_transform)
                start_lon = get_lon(start_x, start_y, element_transform)
                
                if crosses_antimeridian(curr_lon, start_lon):
                    # Don't close path if it would cross the antimeridian
                    # Just leave the path open (no Z command)
                    pass
                else:
                    new_path.append('Z')
                current_x, current_y = start_x, start_y
                
            elif cmd_upper == 'M':
                # Move to - can have multiple coordinate pairs (implicit L after first)
                new_coords = []
                i = 0
                first = True
                while i + 1 < len(params):
                    x, y = params[i], params[i+1]
                    if is_relative:
                        x += current_x
                        y += current_y
                    new_x, new_y = transform_point(x, y, element_transform)
                    if first:
                        new_path.append(f"M {new_x:.2f},{new_y:.2f}")
                        start_x, start_y = x, y
                        first = False
                    else:
                        # Implicit LineTo - check for antimeridian crossing
                        prev_lon = get_lon(current_x, current_y, element_transform)
                        curr_lon = get_lon(x, y, element_transform)
                        
                        if crosses_antimeridian(prev_lon, curr_lon):
                            new_path.append(f"M {new_x:.2f},{new_y:.2f}")
                        else:
                            new_path.append(f"L {new_x:.2f},{new_y:.2f}")
                    current_x, current_y = x, y
                    i += 2
                    
            elif cmd_upper == 'L':
                # Line to - check for antimeridian crossing
                i = 0
                while i + 1 < len(params):
                    x, y = params[i], params[i+1]
                    if is_relative:
                        x += current_x
                        y += current_y
                    
                    # Check for antimeridian crossing
                    prev_lon = get_lon(current_x, current_y, element_transform)
                    curr_lon = get_lon(x, y, element_transform)
                    
                    new_x, new_y = transform_point(x, y, element_transform)
                    
                    if crosses_antimeridian(prev_lon, curr_lon):
                        # Don't draw line across the map - use MoveTo instead
                        new_path.append(f"M {new_x:.2f},{new_y:.2f}")
                    else:
                        new_path.append(f"L {new_x:.2f},{new_y:.2f}")
                    
                    current_x, current_y = x, y
                    i += 2
                    
            elif cmd_upper == 'H':
                # Horizontal line - check for antimeridian crossing
                for x in params:
                    if is_relative:
                        x += current_x
                    
                    prev_lon = get_lon(current_x, current_y, element_transform)
                    curr_lon = get_lon(x, current_y, element_transform)
                    
                    new_x, new_y = transform_point(x, current_y, element_transform)
                    
                    if crosses_antimeridian(prev_lon, curr_lon):
                        new_path.append(f"M {new_x:.2f},{new_y:.2f}")
                    else:
                        new_path.append(f"L {new_x:.2f},{new_y:.2f}")
                    current_x = x
                    
            elif cmd_upper == 'V':
                # Vertical line (no antimeridian crossing possible - same longitude)
                for y in params:
                    if is_relative:
                        y += current_y
                    new_x, new_y = transform_point(current_x, y, element_transform)
                    new_path.append(f"L {new_x:.2f},{new_y:.2f}")
                    current_y = y
                    
            elif cmd_upper == 'C':
                # Cubic bezier: x1 y1 x2 y2 x y - check for antimeridian crossing
                i = 0
                while i + 5 < len(params):
                    x1, y1 = params[i], params[i+1]
                    x2, y2 = params[i+2], params[i+3]
                    x, y = params[i+4], params[i+5]
                    if is_relative:
                        x1 += current_x; y1 += current_y
                        x2 += current_x; y2 += current_y
                        x += current_x; y += current_y
                    
                    # Check for antimeridian crossing between start and end
                    prev_lon = get_lon(current_x, current_y, element_transform)
                    curr_lon = get_lon(x, y, element_transform)
                    
                    nx, ny = transform_point(x, y, element_transform)
                    
                    if crosses_antimeridian(prev_lon, curr_lon):
                        # Skip the curve and just move to end point
                        new_path.append(f"M {nx:.2f},{ny:.2f}")
                    else:
                        nx1, ny1 = transform_point(x1, y1, element_transform)
                        nx2, ny2 = transform_point(x2, y2, element_transform)
                        new_path.append(f"C {nx1:.2f},{ny1:.2f} {nx2:.2f},{ny2:.2f} {nx:.2f},{ny:.2f}")
                    
                    current_x, current_y = x, y
                    i += 6
                    
            elif cmd_upper == 'S':
                # Smooth cubic bezier: x2 y2 x y - check for antimeridian crossing
                i = 0
                while i + 3 < len(params):
                    x2, y2 = params[i], params[i+1]
                    x, y = params[i+2], params[i+3]
                    if is_relative:
                        x2 += current_x; y2 += current_y
                        x += current_x; y += current_y
                    
                    prev_lon = get_lon(current_x, current_y, element_transform)
                    curr_lon = get_lon(x, y, element_transform)
                    
                    nx, ny = transform_point(x, y, element_transform)
                    
                    if crosses_antimeridian(prev_lon, curr_lon):
                        new_path.append(f"M {nx:.2f},{ny:.2f}")
                    else:
                        nx2, ny2 = transform_point(x2, y2, element_transform)
                        new_path.append(f"S {nx2:.2f},{ny2:.2f} {nx:.2f},{ny:.2f}")
                    
                    current_x, current_y = x, y
                    i += 4
                    
            elif cmd_upper == 'Q':
                # Quadratic bezier: x1 y1 x y - check for antimeridian crossing
                i = 0
                while i + 3 < len(params):
                    x1, y1 = params[i], params[i+1]
                    x, y = params[i+2], params[i+3]
                    if is_relative:
                        x1 += current_x; y1 += current_y
                        x += current_x; y += current_y
                    
                    prev_lon = get_lon(current_x, current_y, element_transform)
                    curr_lon = get_lon(x, y, element_transform)
                    
                    nx, ny = transform_point(x, y, element_transform)
                    
                    if crosses_antimeridian(prev_lon, curr_lon):
                        new_path.append(f"M {nx:.2f},{ny:.2f}")
                    else:
                        nx1, ny1 = transform_point(x1, y1, element_transform)
                        new_path.append(f"Q {nx1:.2f},{ny1:.2f} {nx:.2f},{ny:.2f}")
                    
                    current_x, current_y = x, y
                    i += 4
                    
            elif cmd_upper == 'T':
                # Smooth quadratic bezier: x y - check for antimeridian crossing
                i = 0
                while i + 1 < len(params):
                    x, y = params[i], params[i+1]
                    if is_relative:
                        x += current_x
                        y += current_y
                    
                    prev_lon = get_lon(current_x, current_y, element_transform)
                    curr_lon = get_lon(x, y, element_transform)
                    
                    nx, ny = transform_point(x, y, element_transform)
                    
                    if crosses_antimeridian(prev_lon, curr_lon):
                        new_path.append(f"M {nx:.2f},{ny:.2f}")
                    else:
                        new_path.append(f"T {nx:.2f},{ny:.2f}")
                    
                    current_x, current_y = x, y
                    i += 2
                    
            elif cmd_upper == 'A':
                # Arc: rx ry x-rotation large-arc sweep x y - check for antimeridian crossing
                i = 0
                while i + 6 < len(params):
                    rx, ry = params[i], params[i+1]
                    rotation = params[i+2]
                    large_arc = int(params[i+3])
                    sweep = int(params[i+4])
                    x, y = params[i+5], params[i+6]
                    if is_relative:
                        x += current_x
                        y += current_y
                    
                    prev_lon = get_lon(current_x, current_y, element_transform)
                    curr_lon = get_lon(x, y, element_transform)
                    
                    # Transform endpoint
                    nx, ny = transform_point(x, y, element_transform)
                    
                    if crosses_antimeridian(prev_lon, curr_lon):
                        new_path.append(f"M {nx:.2f},{ny:.2f}")
                    else:
                        # Transform current point to get scale factors for rx, ry
                        curr_nx, curr_ny = transform_point(current_x, current_y, element_transform)
                        # Approximate scale for radii (use average scale)
                        test_x, test_y = transform_point(current_x + rx, current_y + ry, element_transform)
                        scale_x = abs(test_x - curr_nx) if rx != 0 else 1
                        scale_y = abs(test_y - curr_ny) if ry != 0 else 1
                        new_rx = scale_x
                        new_ry = scale_y
                        new_path.append(f"A {new_rx:.2f},{new_ry:.2f} {rotation:.2f} {large_arc} {sweep} {nx:.2f},{ny:.2f}")
                    
                    current_x, current_y = x, y
                    i += 7
        
        return ' '.join(new_path)
    
    # Generate border path by sampling the projection boundary
    border_points = []
    border_steps = 200
    
    # Top edge (west to east)
    for i in range(border_steps):
        lon = input_bounds[0] + (i / (border_steps - 1)) * (input_bounds[2] - input_bounds[0])
        x, y = forward_transformer.transform(lon, input_bounds[3])
        px, py = geo_to_svg(x, y)
        border_points.append((px, py))
    
    # Right edge (north to south)
    for i in range(border_steps):
        lat = input_bounds[3] - (i / (border_steps - 1)) * (input_bounds[3] - input_bounds[1])
        x, y = forward_transformer.transform(input_bounds[2], lat)
        px, py = geo_to_svg(x, y)
        border_points.append((px, py))
    
    # Bottom edge (east to west)
    for i in range(border_steps):
        lon = input_bounds[2] - (i / (border_steps - 1)) * (input_bounds[2] - input_bounds[0])
        x, y = forward_transformer.transform(lon, input_bounds[1])
        px, py = geo_to_svg(x, y)
        border_points.append((px, py))
    
    # Left edge (south to north)
    for i in range(border_steps):
        lat = input_bounds[1] + (i / (border_steps - 1)) * (input_bounds[3] - input_bounds[1])
        x, y = forward_transformer.transform(input_bounds[0], lat)
        px, py = geo_to_svg(x, y)
        border_points.append((px, py))
    
    # Create border path
    border_d = f"M {border_points[0][0]:.2f},{border_points[0][1]:.2f} "
    for px, py in border_points[1:]:
        border_d += f"L {px:.2f},{py:.2f} "
    border_d += "Z"
    
    # Helper to detect if a path is a rectangular border (full-width/height frame)
    def is_rectangular_border(d, element_transform):
        """Check if path is a rectangular border that spans the full input dimensions"""
        coords = re.findall(r'-?[\d.]+', d)
        if len(coords) < 8:
            return False
        try:
            # Get all x,y pairs
            points = []
            for i in range(0, len(coords) - 1, 2):
                x, y = float(coords[i]), float(coords[i+1])
                vb_x_pt, vb_y_pt = apply_transform(x, y, element_transform)
                points.append((vb_x_pt, vb_y_pt))
            
            if len(points) < 4:
                return False
            
            # Check if it spans nearly the full width and height
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            path_width = max(xs) - min(xs)
            path_height = max(ys) - min(ys)
            
            # If it spans >90% of input dimensions and is roughly rectangular, it's a border
            if path_width > width * 0.9 and path_height > height * 0.9:
                return True
        except:
            pass
        return False
    
    # Collect elements to remove (rects and rectangular border paths)
    elements_to_remove = []
    
    for element in root.iter():
        # Mark rect elements for removal
        if element.tag.endswith('rect'):
            elements_to_remove.append(element)
        # Mark rectangular border paths for removal
        elif element.tag.endswith('path') and 'd' in element.attrib:
            element_transform = transforms_map.get(element, np.eye(3))
            if is_rectangular_border(element.get('d'), element_transform):
                elements_to_remove.append(element)
    
    # Remove marked elements
    for element in elements_to_remove:
        for parent in root.iter():
            if element in list(parent):
                parent.remove(element)
                break
    
    logger.debug("Removed %s rectangular elements", len(elements_to_remove))
    
    # Transform all remaining paths and remove transforms
    for element in root.iter():
        # Remove transform attribute after applying it
        if 'transform' in element.attrib:
            del element.attrib['transform']
        
        if element.tag.endswith('path') and 'd' in element.attrib:
            element_transform = transforms_map.get(element, np.eye(3))
            element.set('d', transform_path(element.get('d'), element_transform))
    
    # Add ocean background (filled Equal Earth shape) at the beginning
    ocean_path = ET.Element('path', {
        'd': border_d,
        'fill': 'rgb(213,237,254)',
        'stroke': 'none'
    })
    root.insert(0, ocean_path)
    
    if graticule_spacing is not None and graticule_spacing > 0:
        graticule_d = generate_graticule_path_equal_earth(
            graticule_spacing, forward_transformer,
            out_min_x, out_max_x, out_min_y, out_max_y,
            out_width, out_height
        )
        if graticule_d.strip():
            graticule_path = ET.Element('path', {
                'd': graticule_d,
                'fill': 'none',
                'stroke': '#999999',
                'stroke-width': '0.5',
                'stroke-dasharray': '2,2',
                'opacity': '0.5'
            })
            root.insert(1, graticule_path)
    
    if scale_bar_km is not None and scale_bar_km > 0:
        center_lon = (input_bounds[0] + input_bounds[2]) / 2
        center_lat = (input_bounds[1] + input_bounds[3]) / 2
        scale_result = generate_scale_bar_equal_earth(
            scale_bar_km, center_lon, center_lat,
            forward_transformer, out_min_x, out_max_x, out_min_y, out_max_y,
            out_width, out_height
        )
        if scale_result[0]:
            scale_d, bar_x, bar_y, bar_length, bar_height = scale_result
            scale_path = ET.Element('path', {
                'd': scale_d,
                'fill': '#333333',
                'stroke': '#000000',
                'stroke-width': '0.5'
            })
            root.append(scale_path)
            
            if scale_bar_km >= 1:
                label_text = f"{int(scale_bar_km)} km"
            else:
                label_text = f"{scale_bar_km} km"
            
            scale_label = ET.Element('text', {
                'x': f'{bar_x:.2f}',
                'y': f'{bar_y - 3:.2f}',
                'font-family': 'Arial, sans-serif',
                'font-size': '10',
                'fill': '#333333'
            })
            scale_label.text = label_text
            root.append(scale_label)
    
    # Add border path at the end (so it's on top)
    border_path = ET.Element('path', {
        'd': border_d,
        'fill': 'none',
        'stroke': '#000000',
        'stroke-width': '2',
        'stroke-linejoin': 'round'
    })
    root.append(border_path)
    
    # Set proper output dimensions
    root.set('width', f"{out_width:.0f}")
    root.set('height', f"{out_height:.0f}")
    root.set('viewBox', f"0 0 {out_width:.0f} {out_height:.0f}")
    
    tree.write(output_svg, encoding='unicode', xml_declaration=True)
    logger.info("Reprojected map written to %s", output_svg)
