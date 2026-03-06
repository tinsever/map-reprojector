from xml.etree import ElementTree as ET
from pyproj import CRS, Transformer, Geod
import re
import logging
import numpy as np

NUMBER_PATTERN = r'-?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?'
logger = logging.getLogger(__name__)


def parse_transform(transform_str):
    if not transform_str:
        return np.eye(3)
    
    matrix = np.eye(3)
    
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


def parse_path_commands(d):
    commands = []
    pattern = r'([MmLlHhVvCcSsQqTtAaZz])([^MmLlHhVvCcSsQqTtAaZz]*)'
    for match in re.finditer(pattern, d):
        cmd = match.group(1)
        params_str = match.group(2).strip()
        if params_str:
            params = [float(x) for x in re.findall(NUMBER_PATTERN, params_str)]
        else:
            params = []
        commands.append((cmd, params))
    return commands


def generate_graticule_path(
    lon_start: float, lon_end: float,
    lat_start: float, lat_end: float,
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


def generate_scale_bar(
    distance_km: float,
    center_lon: float, center_lat: float,
    transformer,
    out_min_x: float, out_max_x: float,
    out_min_y: float, out_max_y: float,
    out_width: float, out_height: float,
    margin: float = 20,
    bar_height: float = 8
) -> tuple[str, float, float, float, float]:
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


def extract_map_section(
    input_svg: str,
    output_svg: str,
    top_left: tuple[float, float],
    bottom_right: tuple[float, float],
    input_bounds: tuple[float, float, float, float] = (-180, -90, 180, 90),
    output_width: int | None = None,
    reproject: bool = True,
    projection: str = "aeqd",
    graticule_spacing: float | None = None,
    scale_bar_km: float | None = None
) -> None:
    lon_tl, lat_tl = top_left
    lon_br, lat_br = bottom_right
    
    center_lon = (lon_tl + lon_br) / 2
    center_lat = (lat_tl + lat_br) / 2
    
    tree = ET.parse(input_svg)
    root = tree.getroot()
    
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    ET.register_namespace('serif', 'http://www.serif.com/')
    
    viewbox = root.get('viewBox')
    if viewbox:
        vb_parts = viewbox.split()
        vb_x = float(vb_parts[0])
        vb_y = float(vb_parts[1])
        svg_width = float(vb_parts[2])
        svg_height = float(vb_parts[3])
    else:
        w = root.get('width', '1800')
        h = root.get('height', '900')
        vb_x, vb_y = 0, 0
        svg_width = float(re.sub(r'[^\d.]', '', w))
        svg_height = float(re.sub(r'[^\d.]', '', h))
    
    min_lon, min_lat, max_lon, max_lat = input_bounds
    lon_range = max_lon - min_lon
    lat_range = max_lat - min_lat
    
    def collect_transforms(element, current_transform, transforms_map):
        local_transform = parse_transform(element.get('transform'))
        new_transform = current_transform @ local_transform
        transforms_map[element] = new_transform
        for child in element:
            collect_transforms(child, new_transform, transforms_map)
    
    transforms_map = {}
    collect_transforms(root, np.eye(3), transforms_map)
    
    def apply_transform(x, y, matrix):
        pt = np.array([x, y, 1])
        result = matrix @ pt
        return result[0], result[1]
    
    def svg_to_geo(x, y):
        lon = min_lon + ((x - vb_x) / svg_width) * lon_range
        lat = max_lat - ((y - vb_y) / svg_height) * lat_range
        return lon, lat
    
    if reproject:
        if projection == "aeqd":
            proj_string = f"+proj=aeqd +lat_0={center_lat} +lon_0={center_lon} +x_0=0 +y_0=0 +datum=WGS84 +units=m"
            proj_name = "Azimuthal Equidistant"
        elif projection == "laea":
            proj_string = f"+proj=laea +lat_0={center_lat} +lon_0={center_lon} +x_0=0 +y_0=0 +datum=WGS84 +units=m"
            proj_name = "Lambert Azimuthal Equal-Area"
        elif projection == "ortho":
            proj_string = f"+proj=ortho +lat_0={center_lat} +lon_0={center_lon} +x_0=0 +y_0=0 +datum=WGS84 +units=m"
            proj_name = "Orthographic"
        elif projection == "stere":
            proj_string = f"+proj=stere +lat_0={center_lat} +lon_0={center_lon} +x_0=0 +y_0=0 +datum=WGS84 +units=m"
            proj_name = "Stereographic"
        elif projection == "lcc":
            span_lat = abs(lat_tl - lat_br)
            lat_1 = max(-89.0, min(89.0, center_lat - max(span_lat / 4.0, 0.5)))
            lat_2 = max(-89.0, min(89.0, center_lat + max(span_lat / 4.0, 0.5)))
            if abs(lat_1 - lat_2) < 0.1:
                lat_1 = max(-89.0, center_lat - 0.5)
                lat_2 = min(89.0, center_lat + 0.5)
            proj_string = (
                f"+proj=lcc +lat_0={center_lat} +lon_0={center_lon} "
                f"+lat_1={lat_1} +lat_2={lat_2} +x_0=0 +y_0=0 +datum=WGS84 +units=m"
            )
            proj_name = "Lambert Conformal Conic"
        elif projection == "tmerc":
            proj_string = (
                f"+proj=tmerc +lat_0={center_lat} +lon_0={center_lon} "
                "+k=0.9996 +x_0=0 +y_0=0 +datum=WGS84 +units=m"
            )
            proj_name = "Transverse Mercator"
        else:
            proj_string = f"+proj=aeqd +lat_0={center_lat} +lon_0={center_lon} +x_0=0 +y_0=0 +datum=WGS84 +units=m"
            proj_name = "Azimuthal Equidistant"
        
        target_crs = CRS.from_proj4(proj_string)
        transformer = Transformer.from_crs("EPSG:4326", target_crs, always_xy=True)
        
        sample_points = []
        steps = 50
        
        for i in range(steps + 1):
            lon = lon_tl + (i / steps) * (lon_br - lon_tl)
            sample_points.append(transformer.transform(lon, lat_tl))
            sample_points.append(transformer.transform(lon, lat_br))
        
        for i in range(steps + 1):
            lat = lat_br + (i / steps) * (lat_tl - lat_br)
            sample_points.append(transformer.transform(lon_tl, lat))
            sample_points.append(transformer.transform(lon_br, lat))
        
        valid_points = [(x, y) for x, y in sample_points if np.isfinite(x) and np.isfinite(y)]
        
        if not valid_points:
            logger.warning("No valid projected sample points. Falling back to non-reprojected clipping.")
            reproject = False
        else:
            out_min_x = min(p[0] for p in valid_points)
            out_max_x = max(p[0] for p in valid_points)
            out_min_y = min(p[1] for p in valid_points)
            out_max_y = max(p[1] for p in valid_points)
            
            proj_width = out_max_x - out_min_x
            proj_height = out_max_y - out_min_y
            
            if output_width is None:
                output_width = 800
            
            out_width = output_width
            out_height = out_width * (proj_height / proj_width)
            
            def geo_to_output_svg(lon, lat):
                try:
                    proj_x, proj_y = transformer.transform(lon, lat)
                    if not np.isfinite(proj_x) or not np.isfinite(proj_y):
                        return None, None
                    px = ((proj_x - out_min_x) / proj_width) * out_width
                    py = ((out_max_y - proj_y) / proj_height) * out_height
                    return px, py
                except:
                    return None, None
            
            def transform_point(x, y, element_transform):
                vb_x_pt, vb_y_pt = apply_transform(x, y, element_transform)
                lon, lat = svg_to_geo(vb_x_pt, vb_y_pt)
                return geo_to_output_svg(lon, lat)

            def parse_points(points_str):
                values = [float(x) for x in re.findall(NUMBER_PATTERN, points_str or '')]
                pts = []
                i = 0
                while i + 1 < len(values):
                    pts.append((values[i], values[i + 1]))
                    i += 2
                return pts

            def points_to_path(points, close=False):
                if not points:
                    return ''
                parts = [f"M {points[0][0]:.4f},{points[0][1]:.4f}"]
                for x, y in points[1:]:
                    parts.append(f"L {x:.4f},{y:.4f}")
                if close:
                    parts.append('Z')
                return ' '.join(parts)

            def transform_points(points, element_transform, close=False):
                transformed = []
                for x, y in points:
                    nx, ny = transform_point(x, y, element_transform)
                    if nx is not None and ny is not None:
                        transformed.append((nx, ny))
                if close and transformed and transformed[0] != transformed[-1]:
                    transformed.append(transformed[0])
                return transformed
            
            def transform_path(d, element_transform):
                commands = parse_path_commands(d)
                new_path = []
                pen_down = False
                
                current_x, current_y = 0, 0
                start_x, start_y = 0, 0

                def append_densified_line(x0, y0, x1, y1):
                    nonlocal pen_down
                    seg_len = float(np.hypot(x1 - x0, y1 - y0))
                    steps = max(1, min(64, int(seg_len / 8)))
                    emitted = False
                    for step in range(1, steps + 1):
                        t = step / steps
                        sx = x0 + (x1 - x0) * t
                        sy = y0 + (y1 - y0) * t
                        nx, ny = transform_point(sx, sy, element_transform)
                        if nx is None or ny is None:
                            continue
                        if not pen_down:
                            new_path.append(f"M {nx:.4f},{ny:.4f}")
                            pen_down = True
                        else:
                            new_path.append(f"L {nx:.4f},{ny:.4f}")
                        emitted = True
                    return emitted
                
                for cmd, params in commands:
                    is_relative = cmd.islower()
                    cmd_upper = cmd.upper()
                    
                    if cmd_upper == 'Z':
                        if pen_down:
                            new_path.append('Z')
                        current_x, current_y = start_x, start_y
                        
                    elif cmd_upper == 'M':
                        i = 0
                        first = True
                        subpath_visible = False
                        while i + 1 < len(params):
                            x, y = params[i], params[i+1]
                            if is_relative:
                                x += current_x
                                y += current_y
                            if first:
                                start_x, start_y = x, y
                                first = False
                                new_x, new_y = transform_point(x, y, element_transform)
                                if new_x is not None and new_y is not None:
                                    new_path.append(f"M {new_x:.4f},{new_y:.4f}")
                                    pen_down = True
                                    subpath_visible = True
                                else:
                                    pen_down = False
                                    subpath_visible = False
                            else:
                                if subpath_visible:
                                    append_densified_line(current_x, current_y, x, y)
                                else:
                                    new_x, new_y = transform_point(x, y, element_transform)
                                    if new_x is not None and new_y is not None:
                                        new_path.append(f"M {new_x:.4f},{new_y:.4f}")
                                        pen_down = True
                                        subpath_visible = True
                            current_x, current_y = x, y
                            i += 2
                            
                    elif cmd_upper == 'L':
                        i = 0
                        while i + 1 < len(params):
                            x, y = params[i], params[i+1]
                            if is_relative:
                                x += current_x
                                y += current_y
                            if pen_down:
                                append_densified_line(current_x, current_y, x, y)
                            else:
                                new_x, new_y = transform_point(x, y, element_transform)
                                if new_x is not None and new_y is not None:
                                    new_path.append(f"M {new_x:.4f},{new_y:.4f}")
                                    pen_down = True
                            current_x, current_y = x, y
                            i += 2
                            
                    elif cmd_upper == 'H':
                        for x in params:
                            if is_relative:
                                x += current_x
                            if pen_down:
                                append_densified_line(current_x, current_y, x, current_y)
                            else:
                                new_x, new_y = transform_point(x, current_y, element_transform)
                                if new_x is not None and new_y is not None:
                                    new_path.append(f"M {new_x:.4f},{new_y:.4f}")
                                    pen_down = True
                            current_x = x
                            
                    elif cmd_upper == 'V':
                        for y in params:
                            if is_relative:
                                y += current_y
                            if pen_down:
                                append_densified_line(current_x, current_y, current_x, y)
                            else:
                                new_x, new_y = transform_point(current_x, y, element_transform)
                                if new_x is not None and new_y is not None:
                                    new_path.append(f"M {new_x:.4f},{new_y:.4f}")
                                    pen_down = True
                            current_y = y
                            
                    elif cmd_upper == 'C':
                        i = 0
                        while i + 5 < len(params):
                            x1, y1 = params[i], params[i+1]
                            x2, y2 = params[i+2], params[i+3]
                            x, y = params[i+4], params[i+5]
                            if is_relative:
                                x1 += current_x; y1 += current_y
                                x2 += current_x; y2 += current_y
                                x += current_x; y += current_y
                            nx1, ny1 = transform_point(x1, y1, element_transform)
                            nx2, ny2 = transform_point(x2, y2, element_transform)
                            nx, ny = transform_point(x, y, element_transform)
                            if all(v is not None for v in [nx1, ny1, nx2, ny2, nx, ny]):
                                pen_down = True
                                new_path.append(f"C {nx1:.4f},{ny1:.4f} {nx2:.4f},{ny2:.4f} {nx:.4f},{ny:.4f}")
                            current_x, current_y = x, y
                            i += 6
                            
                    elif cmd_upper == 'S':
                        i = 0
                        while i + 3 < len(params):
                            x2, y2 = params[i], params[i+1]
                            x, y = params[i+2], params[i+3]
                            if is_relative:
                                x2 += current_x; y2 += current_y
                                x += current_x; y += current_y
                            nx2, ny2 = transform_point(x2, y2, element_transform)
                            nx, ny = transform_point(x, y, element_transform)
                            if all(v is not None for v in [nx2, ny2, nx, ny]):
                                pen_down = True
                                new_path.append(f"S {nx2:.4f},{ny2:.4f} {nx:.4f},{ny:.4f}")
                            current_x, current_y = x, y
                            i += 4
                            
                    elif cmd_upper == 'Q':
                        i = 0
                        while i + 3 < len(params):
                            x1, y1 = params[i], params[i+1]
                            x, y = params[i+2], params[i+3]
                            if is_relative:
                                x1 += current_x; y1 += current_y
                                x += current_x; y += current_y
                            nx1, ny1 = transform_point(x1, y1, element_transform)
                            nx, ny = transform_point(x, y, element_transform)
                            if all(v is not None for v in [nx1, ny1, nx, ny]):
                                pen_down = True
                                new_path.append(f"Q {nx1:.4f},{ny1:.4f} {nx:.4f},{ny:.4f}")
                            current_x, current_y = x, y
                            i += 4
                            
                    elif cmd_upper == 'T':
                        i = 0
                        while i + 1 < len(params):
                            x, y = params[i], params[i+1]
                            if is_relative:
                                x += current_x
                                y += current_y
                            nx, ny = transform_point(x, y, element_transform)
                            if nx is not None and ny is not None:
                                pen_down = True
                                new_path.append(f"T {nx:.4f},{ny:.4f}")
                            current_x, current_y = x, y
                            i += 2
                            
                    elif cmd_upper == 'A':
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
                            nx, ny = transform_point(x, y, element_transform)
                            curr_nx, curr_ny = transform_point(current_x, current_y, element_transform)
                            if all(v is not None for v in [nx, ny, curr_nx, curr_ny]):
                                test_x, test_y = transform_point(current_x + rx, current_y + ry, element_transform)
                                if test_x is not None and test_y is not None:
                                    scale_x = abs(test_x - curr_nx) if rx != 0 else 1
                                    scale_y = abs(test_y - curr_ny) if ry != 0 else 1
                                    pen_down = True
                                    new_path.append(f"A {scale_x:.4f},{scale_y:.4f} {rotation:.4f} {large_arc} {sweep} {nx:.4f},{ny:.4f}")
                            current_x, current_y = x, y
                            i += 7
                
                return ' '.join(new_path)
            
            def get_path_geo_bbox(d, element_transform):
                commands = parse_path_commands(d)
                min_lon, min_lat = float('inf'), float('inf')
                max_lon, max_lat = float('-inf'), float('-inf')
                current_x, current_y = 0, 0
                
                for cmd, params in commands:
                    is_relative = cmd.islower()
                    cmd_upper = cmd.upper()
                    
                    if cmd_upper == 'M' or cmd_upper == 'L':
                        i = 0
                        while i + 1 < len(params):
                            x, y = params[i], params[i+1]
                            if is_relative:
                                x += current_x
                                y += current_y
                            vb_x_pt, vb_y_pt = apply_transform(x, y, element_transform)
                            lon, lat = svg_to_geo(vb_x_pt, vb_y_pt)
                            min_lon = min(min_lon, lon)
                            max_lon = max(max_lon, lon)
                            min_lat = min(min_lat, lat)
                            max_lat = max(max_lat, lat)
                            current_x, current_y = x, y
                            i += 2
                    elif cmd_upper == 'H':
                        for x in params:
                            if is_relative:
                                x += current_x
                            vb_x_pt, vb_y_pt = apply_transform(x, current_y, element_transform)
                            lon, lat = svg_to_geo(vb_x_pt, vb_y_pt)
                            min_lon = min(min_lon, lon)
                            max_lon = max(max_lon, lon)
                            min_lat = min(min_lat, lat)
                            max_lat = max(max_lat, lat)
                            current_x = x
                    elif cmd_upper == 'V':
                        for y in params:
                            if is_relative:
                                y += current_y
                            vb_x_pt, vb_y_pt = apply_transform(current_x, y, element_transform)
                            lon, lat = svg_to_geo(vb_x_pt, vb_y_pt)
                            min_lon = min(min_lon, lon)
                            max_lon = max(max_lon, lon)
                            min_lat = min(min_lat, lat)
                            max_lat = max(max_lat, lat)
                            current_y = y
                    elif cmd_upper == 'C':
                        i = 0
                        while i + 5 < len(params):
                            pts = [params[i], params[i+1], params[i+2], params[i+3], params[i+4], params[i+5]]
                            if is_relative:
                                pts = [pts[j] + (current_x if j % 2 == 0 else current_y) for j in range(6)]
                            for j in range(0, 6, 2):
                                vb_x_pt, vb_y_pt = apply_transform(pts[j], pts[j+1], element_transform)
                                lon, lat = svg_to_geo(vb_x_pt, vb_y_pt)
                                min_lon = min(min_lon, lon)
                                max_lon = max(max_lon, lon)
                                min_lat = min(min_lat, lat)
                                max_lat = max(max_lat, lat)
                            current_x, current_y = pts[4], pts[5]
                            i += 6
                
                if min_lon == float('inf'):
                    return None
                return (min_lon, min_lat, max_lon, max_lat)
            
            def geo_bbox_intersects_selection(geo_bbox, sel_lon1, sel_lat1, sel_lon2, sel_lat2):
                if geo_bbox is None:
                    return False
                b_lon1, b_lat1, b_lon2, b_lat2 = geo_bbox
                sel_min_lon, sel_max_lon = min(sel_lon1, sel_lon2), max(sel_lon1, sel_lon2)
                sel_min_lat, sel_max_lat = min(sel_lat1, sel_lat2), max(sel_lat1, sel_lat2)
                margin_lat = (sel_max_lat - sel_min_lat) * 0.1
                margin_lon = (sel_max_lon - sel_min_lon) * 0.1
                sel_min_lon -= margin_lon
                sel_max_lon += margin_lon
                sel_min_lat -= margin_lat
                sel_max_lat += margin_lat
                return not (b_lon2 < sel_min_lon or b_lon1 > sel_max_lon or b_lat2 < sel_min_lat or b_lat1 > sel_max_lat)
            
            elements_to_remove = []
            for element in root.iter():
                if element.tag.endswith('path'):
                    d = element.get('d', '')
                    if 'M 0,0' in d and '1800' in d and '900' in d:
                        elements_to_remove.append(element)
                        continue
                    
                    element_transform = transforms_map.get(element, np.eye(3))
                    geo_bbox = get_path_geo_bbox(d, element_transform)
                    if not geo_bbox_intersects_selection(geo_bbox, lon_tl, lat_tl, lon_br, lat_br):
                        elements_to_remove.append(element)
            
            for element in elements_to_remove:
                for parent in root.iter():
                    if element in list(parent):
                        parent.remove(element)
                        break

            original_ocean_rects = []
            for element in list(root):
                if element.tag.endswith('rect'):
                    fill = element.get('fill', '')
                    if fill and '213,237,254' in fill:
                        original_ocean_rects.append(element)
            
            for element in original_ocean_rects:
                root.remove(element)

            def as_path_tag(tag_name: str) -> str:
                if tag_name.startswith('{') and '}' in tag_name:
                    namespace = tag_name.split('}')[0] + '}'
                    return f"{namespace}path"
                return 'path'
            
            for element in root.iter():
                if 'transform' in element.attrib:
                    del element.attrib['transform']
                
                if element.tag.endswith('path') and 'd' in element.attrib:
                    element_transform = transforms_map.get(element, np.eye(3))
                    old_d = element.get('d')
                    new_d = transform_path(old_d, element_transform)
                    if new_d.strip():
                        element.set('d', new_d)
                    else:
                        pass
                elif element.tag.endswith('line'):
                    element_transform = transforms_map.get(element, np.eye(3))
                    try:
                        x1 = float(element.get('x1', '0'))
                        y1 = float(element.get('y1', '0'))
                        x2 = float(element.get('x2', '0'))
                        y2 = float(element.get('y2', '0'))
                        pts = transform_points([(x1, y1), (x2, y2)], element_transform)
                        new_d = points_to_path(pts)
                        if new_d:
                            element.tag = as_path_tag(element.tag)
                            element.attrib.pop('x1', None)
                            element.attrib.pop('y1', None)
                            element.attrib.pop('x2', None)
                            element.attrib.pop('y2', None)
                            element.set('d', new_d)
                    except:
                        pass
                elif element.tag.endswith('polyline'):
                    element_transform = transforms_map.get(element, np.eye(3))
                    pts = parse_points(element.get('points', ''))
                    transformed_pts = transform_points(pts, element_transform)
                    new_d = points_to_path(transformed_pts)
                    if new_d:
                        element.tag = as_path_tag(element.tag)
                        element.attrib.pop('points', None)
                        element.set('d', new_d)
                elif element.tag.endswith('polygon'):
                    element_transform = transforms_map.get(element, np.eye(3))
                    pts = parse_points(element.get('points', ''))
                    transformed_pts = transform_points(pts, element_transform, close=True)
                    new_d = points_to_path(transformed_pts, close=True)
                    if new_d:
                        element.tag = as_path_tag(element.tag)
                        element.attrib.pop('points', None)
                        element.set('d', new_d)
                elif element.tag.endswith('rect'):
                    element_transform = transforms_map.get(element, np.eye(3))
                    try:
                        x = float(element.get('x', '0'))
                        y = float(element.get('y', '0'))
                        w = float(element.get('width', '0'))
                        h = float(element.get('height', '0'))
                        rect_points = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
                        transformed_pts = transform_points(rect_points, element_transform, close=True)
                        new_d = points_to_path(transformed_pts, close=True)
                        if new_d:
                            element.tag = as_path_tag(element.tag)
                            element.attrib.pop('x', None)
                            element.attrib.pop('y', None)
                            element.attrib.pop('width', None)
                            element.attrib.pop('height', None)
                            element.attrib.pop('rx', None)
                            element.attrib.pop('ry', None)
                            element.set('d', new_d)
                    except:
                        pass
            
            ocean_bg = ET.Element('rect', {
                'x': '0',
                'y': '0',
                'width': f'{out_width:.2f}',
                'height': f'{out_height:.2f}',
                'fill': 'rgb(213,237,254)',
                'stroke': 'none'
            })
            root.insert(0, ocean_bg)
            
            if graticule_spacing is not None and graticule_spacing > 0:
                graticule_d = generate_graticule_path(
                    lon_tl, lon_br, lat_br, lat_tl,
                    graticule_spacing, transformer,
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
                scale_result = generate_scale_bar(
                    scale_bar_km, center_lon, center_lat,
                    transformer, out_min_x, out_max_x, out_min_y, out_max_y,
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
            
            metadata = ET.Element('metadata')
            geo_bounds = ET.SubElement(metadata, 'geoBounds')
            ET.SubElement(geo_bounds, 'topLeft').set('lon', str(lon_tl))
            ET.SubElement(geo_bounds, 'topLeft').set('lat', str(lat_tl))
            ET.SubElement(geo_bounds, 'bottomRight').set('lon', str(lon_br))
            ET.SubElement(geo_bounds, 'bottomRight').set('lat', str(lat_br))
            ET.SubElement(geo_bounds, 'center').set('lon', str(center_lon))
            ET.SubElement(geo_bounds, 'center').set('lat', str(center_lat))
            ET.SubElement(geo_bounds, 'projection').text = proj_name
            root.insert(0, metadata)
            
            root.set('viewBox', f"0 0 {out_width:.2f} {out_height:.2f}")
            root.set('width', f"{out_width:.0f}")
            root.set('height', f"{out_height:.0f}")
            
            tree.write(output_svg, encoding='unicode', xml_declaration=True)
            
            logger.info(
                "Extracted section with projection=%s center=(%.1f, %.1f) output=%s size=%sx%s",
                proj_name,
                center_lon,
                center_lat,
                output_svg,
                f"{out_width:.0f}",
                f"{out_height:.0f}",
            )
            return
    
    def geo_to_svg_coords(lon: float, lat: float) -> tuple[float, float]:
        x = vb_x + ((lon - min_lon) / lon_range) * svg_width
        y = vb_y + ((max_lat - lat) / lat_range) * svg_height
        return x, y
    
    x_tl, y_tl = geo_to_svg_coords(lon_tl, lat_tl)
    x_br, y_br = geo_to_svg_coords(lon_br, lat_br)
    
    clip_x = min(x_tl, x_br)
    clip_y = min(y_tl, y_br)
    clip_width = abs(x_br - x_tl)
    clip_height = abs(y_br - y_tl)
    
    if output_width is None:
        out_width = clip_width
        out_height = clip_height
    else:
        out_width = output_width
        out_height = output_width * (clip_height / clip_width)
    
    elements_to_remove = []
    for element in list(root):
        if element.tag.endswith('path'):
            d = element.get('d', '')
            if 'M 0,0' in d and '1800' in d and '900' in d:
                elements_to_remove.append(element)
    
    for element in elements_to_remove:
        root.remove(element)
    
    ocean_bg = ET.Element('rect', {
        'x': f'{clip_x:.2f}',
        'y': f'{clip_y:.2f}',
        'width': f'{clip_width:.2f}',
        'height': f'{clip_height:.2f}',
        'fill': 'rgb(213,237,254)',
        'stroke': 'none'
    })
    root.insert(0, ocean_bg)
    
    metadata = ET.Element('metadata')
    geo_bounds = ET.SubElement(metadata, 'geoBounds')
    ET.SubElement(geo_bounds, 'topLeft').set('lon', str(lon_tl))
    ET.SubElement(geo_bounds, 'topLeft').set('lat', str(lat_tl))
    ET.SubElement(geo_bounds, 'bottomRight').set('lon', str(lon_br))
    ET.SubElement(geo_bounds, 'bottomRight').set('lat', str(lat_br))
    ET.SubElement(geo_bounds, 'center').set('lon', str(center_lon))
    ET.SubElement(geo_bounds, 'center').set('lat', str(center_lat))
    root.insert(0, metadata)
    
    root.set('viewBox', f"{clip_x:.2f} {clip_y:.2f} {clip_width:.2f} {clip_height:.2f}")
    root.set('width', f"{out_width:.0f}")
    root.set('height', f"{out_height:.0f}")
    
    tree.write(output_svg, encoding='unicode', xml_declaration=True)
    
    logger.info(
        "Extracted section without reprojection output=%s size=%sx%s",
        output_svg,
        f"{out_width:.0f}",
        f"{out_height:.0f}",
    )


def get_map_section_centered(
    input_svg: str,
    output_svg: str,
    center: tuple[float, float],
    span_lon: float,
    span_lat: float,
    input_bounds: tuple[float, float, float, float] = (-180, -90, 180, 90),
    output_width: int | None = None,
    reproject: bool = True,
    projection: str = "aeqd",
    graticule_spacing: float | None = None,
    scale_bar_km: float | None = None
) -> None:
    center_lon, center_lat = center
    
    top_left = (center_lon - span_lon / 2, center_lat + span_lat / 2)
    bottom_right = (center_lon + span_lon / 2, center_lat - span_lat / 2)
    
    extract_map_section(
        input_svg=input_svg,
        output_svg=output_svg,
        top_left=top_left,
        bottom_right=bottom_right,
        input_bounds=input_bounds,
        output_width=output_width,
        reproject=reproject,
        projection=projection,
        graticule_spacing=graticule_spacing,
        scale_bar_km=scale_bar_km
    )
