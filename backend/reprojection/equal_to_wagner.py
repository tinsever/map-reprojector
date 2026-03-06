from pyproj import Transformer
from xml.etree import ElementTree as ET
import re
import logging
import numpy as np

WAGNER_VII_CRS = "+proj=wag7 +type=crs"
EQUAL_EARTH_CRS = "ESRI:54035"
logger = logging.getLogger(__name__)


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


def reproject_svg(input_svg, output_svg, input_bounds=(-180, -90, 180, 90), output_width=1800, padding=0.0, graticule_spacing=None, scale_bar_km=None):
    """
    Reproject SVG from Equal Earth projection to Wagner VII projection.

    Args:
        input_svg: Path to input SVG file (Equal Earth projection)
        output_svg: Path to output SVG file (Wagner VII projection)
        input_bounds: Tuple (min_lon, min_lat, max_lon, max_lat) - geographic bounds for output
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

    # Get dimensions from viewBox
    viewbox = root.get('viewBox')
    if viewbox:
        vb_parts = viewbox.split()
        vb_width = float(vb_parts[2])
        vb_height = float(vb_parts[3])
    else:
        vb_width = 1641
        vb_height = 801

    logger.debug("ViewBox dimensions: %s × %s", vb_width, vb_height)

    number_pattern = r'-?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?'

    # Collect transforms
    def collect_transforms(element, current_transform, transforms_map):
        local_transform = parse_transform(element.get('transform'))
        new_transform = current_transform @ local_transform
        transforms_map[element] = new_transform
        for child in element:
            collect_transforms(child, new_transform, transforms_map)

    transforms_map = {}
    collect_transforms(root, np.eye(3), transforms_map)

    # Find actual content bounds by scanning all path coordinates
    min_vb_x, min_vb_y = float('inf'), float('inf')
    max_vb_x, max_vb_y = float('-inf'), float('-inf')

    def apply_transform(x, y, matrix):
        pt = np.array([x, y, 1])
        result = matrix @ pt
        return result[0], result[1]

    def get_path_bounds(d, element_transform):
        """Get bounds of a single path in viewBox coordinates"""
        path_min_x, path_min_y = float('inf'), float('inf')
        path_max_x, path_max_y = float('-inf'), float('-inf')
        coords = re.findall(number_pattern, d)
        i = 0
        while i + 1 < len(coords):
            try:
                x, y = float(coords[i]), float(coords[i + 1])
                vb_x, vb_y = apply_transform(x, y, element_transform)
                path_min_x = min(path_min_x, vb_x)
                path_min_y = min(path_min_y, vb_y)
                path_max_x = max(path_max_x, vb_x)
                path_max_y = max(path_max_y, vb_y)
            except:
                pass
            i += 2
        return path_min_x, path_min_y, path_max_x, path_max_y

    def scan_path_bounds(d, element_transform):
        nonlocal min_vb_x, min_vb_y, max_vb_x, max_vb_y
        pmin_x, pmin_y, pmax_x, pmax_y = get_path_bounds(d, element_transform)
        min_vb_x = min(min_vb_x, pmin_x)
        min_vb_y = min(min_vb_y, pmin_y)
        max_vb_x = max(max_vb_x, pmax_x)
        max_vb_y = max(max_vb_y, pmax_y)

    # First pass: scan all paths to find bounds
    for element in root.iter():
        if element.tag.endswith('path') and 'd' in element.attrib:
            element_transform = transforms_map.get(element, np.eye(3))
            scan_path_bounds(element.get('d'), element_transform)

    content_width = max_vb_x - min_vb_x
    content_height = max_vb_y - min_vb_y
    logger.debug(
        "Content bounds: x=[%.2f, %.2f], y=[%.2f, %.2f], size=%.2f×%.2f",
        min_vb_x,
        max_vb_x,
        min_vb_y,
        max_vb_y,
        content_width,
        content_height,
    )

    # Create transformers
    forward_equal = Transformer.from_crs("EPSG:4326", EQUAL_EARTH_CRS, always_xy=True)
    inverse_equal = Transformer.from_crs(EQUAL_EARTH_CRS, "EPSG:4326", always_xy=True)
    forward_wagner = Transformer.from_crs("EPSG:4326", WAGNER_VII_CRS, always_xy=True)

    # Calculate TRUE Equal Earth bounds
    ee_max_x, _ = forward_equal.transform(180, 0)
    ee_min_x, _ = forward_equal.transform(-180, 0)
    _, ee_max_y = forward_equal.transform(0, 90)
    _, ee_min_y = forward_equal.transform(0, -90)

    ee_width = ee_max_x - ee_min_x
    ee_height = ee_max_y - ee_min_y

    def viewbox_to_equal(vb_x, vb_y):
        """Convert viewBox coordinates to Equal Earth projected coordinates"""
        norm_x = (vb_x - min_vb_x) / content_width
        norm_y = (vb_y - min_vb_y) / content_height
        ee_x = ee_min_x + norm_x * ee_width
        ee_y = ee_max_y - norm_y * ee_height
        return ee_x, ee_y

    # Sample many points along the boundary to get accurate output bounds
    sample_points = []
    steps = 100

    # Top and bottom edges
    for i in range(steps + 1):
        lon = input_bounds[0] + (i / steps) * (input_bounds[2] - input_bounds[0])
        sample_points.append(forward_wagner.transform(lon, input_bounds[1]))
        sample_points.append(forward_wagner.transform(lon, input_bounds[3]))

    # Left and right edges
    for i in range(steps + 1):
        lat = input_bounds[1] + (i / steps) * (input_bounds[3] - input_bounds[1])
        sample_points.append(forward_wagner.transform(input_bounds[0], lat))
        sample_points.append(forward_wagner.transform(input_bounds[2], lat))

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

    def proj_to_svg(x, y):
        """Convert projected Wagner VII coords to output SVG pixels"""
        px = ((x - out_min_x) / (out_max_x - out_min_x)) * out_width
        py = ((out_max_y - y) / (out_max_y - out_min_y)) * out_height
        return px, py

    def is_valid_ee_point(ee_x, ee_y):
        """Check if point is within valid Equal Earth boundary"""
        try:
            _, lat = inverse_equal.transform(0, ee_y)
            if abs(lat) > 90:
                return False
            max_x_at_lat, _ = forward_equal.transform(180, lat)
            return abs(ee_x) <= abs(max_x_at_lat) * 1.01
        except:
            return False

    def is_background_path(d, element_transform, element):
        """Check if this path is likely the ocean/water background"""
        # Check if it's in a water-related group
        parent = None
        for p in root.iter():
            for child in p:
                if child == element:
                    parent = p
                    break

        if parent is not None:
            parent_id = parent.get('id', '').lower()
            if 'wasser' in parent_id or 'water' in parent_id or 'ocean' in parent_id or 'gewaesser' in parent_id:
                # Check if it's large (covers most of the content area)
                pmin_x, pmin_y, pmax_x, pmax_y = get_path_bounds(d, element_transform)
                path_width = pmax_x - pmin_x
                path_height = pmax_y - pmin_y
                # If path covers more than 80% of content area, it's likely background
                if path_width > content_width * 0.8 and path_height > content_height * 0.8:
                    return True

        # Also check by size alone - very large paths that span most of the area
        pmin_x, pmin_y, pmax_x, pmax_y = get_path_bounds(d, element_transform)
        path_width = pmax_x - pmin_x
        path_height = pmax_y - pmin_y
        if path_width > content_width * 0.95 and path_height > content_height * 0.95:
            return True

        return False

    def transform_path(d, element_transform):
        """Transform path d attribute"""

        def replace_coords(match):
            cmd = match.group(1)
            coords_str = match.group(2).strip()
            coords = re.findall(number_pattern, coords_str)
            new_coords = []

            i = 0
            while i < len(coords):
                if i + 1 < len(coords):
                    try:
                        x, y = float(coords[i]), float(coords[i + 1])
                        vb_x, vb_y = apply_transform(x, y, element_transform)
                        ee_x, ee_y = viewbox_to_equal(vb_x, vb_y)

                        if is_valid_ee_point(ee_x, ee_y):
                            lon, lat = inverse_equal.transform(ee_x, ee_y)
                            lon = max(-180, min(180, lon))
                            lat = max(-90, min(90, lat))
                            proj_x, proj_y = forward_wagner.transform(lon, lat)
                            out_x, out_y = proj_to_svg(proj_x, proj_y)
                            new_coords.extend([f"{out_x:.2f}", f"{out_y:.2f}"])
                        else:
                            # For invalid points, project to nearest valid point on boundary
                            try:
                                # Clamp Y first
                                clamped_ee_y = max(ee_min_y, min(ee_max_y, ee_y))
                                _, lat = inverse_equal.transform(0, clamped_ee_y)
                                lat = max(-89.99, min(89.99, lat))
                                # Get max X at this latitude
                                max_x, _ = forward_equal.transform(180, lat)
                                # Clamp X to boundary
                                if ee_x > 0:
                                    clamped_x = min(ee_x, max_x)
                                else:
                                    clamped_x = max(ee_x, -max_x)
                                lon, lat = inverse_equal.transform(clamped_x, clamped_ee_y)
                                lon = max(-180, min(180, lon))
                                lat = max(-90, min(90, lat))
                                proj_x, proj_y = forward_wagner.transform(lon, lat)
                                out_x, out_y = proj_to_svg(proj_x, proj_y)
                                new_coords.extend([f"{out_x:.2f}", f"{out_y:.2f}"])
                            except:
                                new_coords.extend(["900.00", "450.00"])
                    except:
                        new_coords.extend([coords[i], coords[i + 1]])
                    i += 2
                else:
                    i += 1

            return cmd + ' ' + ' '.join(new_coords)

        return re.sub(r'([MLCQTSAZmlcqtsaz])([^MLCQTSAZmlcqtsaz]*)', replace_coords, d)

    # Generate border path by sampling the projection boundary
    border_points = []
    border_steps = 200

    # Top edge (west to east)
    for i in range(border_steps):
        lon = input_bounds[0] + (i / (border_steps - 1)) * (input_bounds[2] - input_bounds[0])
        x, y = forward_wagner.transform(lon, input_bounds[3])
        px, py = proj_to_svg(x, y)
        border_points.append((px, py))

    # Right edge (north to south)
    for i in range(border_steps):
        lat = input_bounds[3] - (i / (border_steps - 1)) * (input_bounds[3] - input_bounds[1])
        x, y = forward_wagner.transform(input_bounds[2], lat)
        px, py = proj_to_svg(x, y)
        border_points.append((px, py))

    # Bottom edge (east to west)
    for i in range(border_steps):
        lon = input_bounds[2] - (i / (border_steps - 1)) * (input_bounds[2] - input_bounds[0])
        x, y = forward_wagner.transform(lon, input_bounds[1])
        px, py = proj_to_svg(x, y)
        border_points.append((px, py))

    # Left edge (south to north)
    for i in range(border_steps):
        lat = input_bounds[1] + (i / (border_steps - 1)) * (input_bounds[3] - input_bounds[1])
        x, y = forward_wagner.transform(input_bounds[0], lat)
        px, py = proj_to_svg(x, y)
        border_points.append((px, py))

    # Create border path
    border_d = f"M {border_points[0][0]:.2f},{border_points[0][1]:.2f} "
    for px, py in border_points[1:]:
        border_d += f"L {px:.2f},{py:.2f} "
    border_d += "Z"

    # Track elements to remove (backgrounds we'll replace)
    elements_to_replace = []
    background_styles = []

    # Second pass: identify background paths
    for element in root.iter():
        if element.tag.endswith('path') and 'd' in element.attrib:
            element_transform = transforms_map.get(element, np.eye(3))
            if is_background_path(element.get('d'), element_transform, element):
                # Store the style info
                style = element.get('style', '')
                fill = element.get('fill', '')
                if not fill and 'fill:' in style:
                    fill_match = re.search(r'fill:\s*([^;]+)', style)
                    if fill_match:
                        fill = fill_match.group(1)
                if fill:
                    background_styles.append((fill, style))
                elements_to_replace.append(element)

    logger.debug("Background paths replaced: %s", len(elements_to_replace))

    # Remove background paths from their parents
    for element in elements_to_replace:
        for parent in root.iter():
            if element in list(parent):
                parent.remove(element)
                break

    # Third pass: transform all remaining paths
    for element in root.iter():
        if 'transform' in element.attrib:
            del element.attrib['transform']

        if element.tag.endswith('path') and 'd' in element.attrib:
            element_transform = transforms_map.get(element, np.eye(3))
            element.set('d', transform_path(element.get('d'), element_transform))

    # Add ocean background (filled Wagner VII shape) at the beginning
    if background_styles:
        fill_color = background_styles[0][0]
    else:
        fill_color = '#b3d1e6'  # Default ocean blue

    ocean_path = ET.Element('path', {
        'd': border_d,
        'fill': fill_color,
        'stroke': 'none'
    })
    root.insert(0, ocean_path)

    # Add border path at the end (so it's on top)
    border_path = ET.Element('path', {
        'd': border_d,
        'fill': 'none',
        'stroke': '#000000',
        'stroke-width': '2',
        'stroke-linejoin': 'round'
    })
    root.append(border_path)

    # Set output dimensions
    root.set('width', f"{out_width:.0f}")
    root.set('height', f"{out_height:.0f}")
    root.set('viewBox', f"0 0 {out_width:.0f} {out_height:.0f}")

    tree.write(output_svg, encoding='unicode', xml_declaration=True)
    logger.info("Reprojected map written to %s (%sx%s)", output_svg, f"{out_width:.0f}", f"{out_height:.0f}")

