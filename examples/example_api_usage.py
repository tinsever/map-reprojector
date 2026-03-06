"""
CartA API example usage.

This script demonstrates the main API endpoints against a local server.
"""

import requests
import json
from pathlib import Path

# API Base URL
BASE_URL = "http://localhost:5100/api"

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def health_check():
    """Test the health check endpoint"""
    print_section("1. Health Check")
    
    response = requests.get(f"{BASE_URL}/health/")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ API Status: {data['status']}")
        print(f"  Service: {data['service']}")
    else:
        print(f"✗ Health check failed: {response.status_code}")


def example_reproject_plate_to_equal():
    """Example: Reproject from Plate Carrée to Equal Earth"""
    print_section("2. Reprojektion: Plate Carrée → Equal Earth")
    
    payload = {
        "input_svg": "Weltkarte.svg",
        "direction": "plate-to-equal",
        "input_bounds": [-180, -90, 180, 90],
        "output_width": 1800,
        "padding": 0.0,
        "output_filename": "equal_earth_world.svg"
    }
    
    print("Request:")
    print(json.dumps(payload, indent=2))
    
    response = requests.post(
        f"{BASE_URL}/reproject/",
        json=payload
    )
    
    if response.status_code == 200:
        output_file = "output_equal_earth.svg"
        with open(output_file, 'wb') as f:
            f.write(response.content)
        print(f"\n✓ Erfolg! Datei gespeichert als: {output_file}")
        print(f"  Dateigröße: {len(response.content):,} bytes")
    else:
        print(f"\n✗ Fehler: {response.status_code}")
        print(response.json())


def example_reproject_plate_to_wagner():
    """Example: Reproject from Plate Carrée to Wagner VII"""
    print_section("3. Reprojektion: Plate Carrée → Wagner VII")

    payload = {
        "input_svg": "Weltkarte.svg",
        "direction": "plate-to-wagner",
        "input_bounds": [-180, -90, 180, 90],
        "output_width": 1800,
        "padding": 0.0,
        "output_filename": "wagner_vii_world.svg"
    }

    print("Request:")
    print(json.dumps(payload, indent=2))

    response = requests.post(
        f"{BASE_URL}/reproject/",
        json=payload
    )

    if response.status_code == 200:
        output_file = "output_wagner_vii.svg"
        with open(output_file, 'wb') as f:
            f.write(response.content)
        print(f"\n✓ Erfolg! Datei gespeichert als: {output_file}")
        print(f"  Dateigröße: {len(response.content):,} bytes")
    else:
        print(f"\n✗ Fehler: {response.status_code}")
        print(response.json())


def example_reproject_equal_to_plate():
    """Example: Reproject from Equal Earth to Plate Carrée"""
    print_section("4. Reprojektion: Equal Earth → Plate Carrée")
    
    payload = {
        "input_svg": "output_equal_earth.svg",
        "direction": "equal-to-plate",
        "input_bounds": [-180, -90, 180, 90],
        "output_width": 1800,
        "padding": 0.0,
        "output_filename": "plate_carree_world.svg"
    }
    
    print("Request:")
    print(json.dumps(payload, indent=2))
    
    response = requests.post(
        f"{BASE_URL}/reproject/",
        json=payload
    )
    
    if response.status_code == 200:
        output_file = "output_plate_carree.svg"
        with open(output_file, 'wb') as f:
            f.write(response.content)
        print(f"\n✓ Erfolg! Datei gespeichert als: {output_file}")
    else:
        print(f"\n✗ Fehler: {response.status_code}")
        print(response.json())


def example_extract_europe():
    """Example: Extract Europe with AEQD projection"""
    print_section("5. Kartenausschnitt: Europa (AEQD)")
    
    payload = {
        "input_svg": "Weltkarte.svg",
        "top_left": [-10, 70],
        "bottom_right": [40, 35],
        "input_bounds": [-180, -90, 180, 90],
        "output_width": 800,
        "reproject": True,
        "projection": "aeqd",
        "output_filename": "europa.svg"
    }
    
    print("Request:")
    print(json.dumps(payload, indent=2))
    print("\nExtrahiert Europa von Island bis Türkei")
    print("Mit Azimuthal Equidistant Projektion (minimale Verzerrung)")
    
    response = requests.post(
        f"{BASE_URL}/extract/corners",
        json=payload
    )
    
    if response.status_code == 200:
        output_file = "output_europa.svg"
        with open(output_file, 'wb') as f:
            f.write(response.content)
        print(f"\n✓ Erfolg! Europa-Karte gespeichert als: {output_file}")
    else:
        print(f"\n✗ Fehler: {response.status_code}")
        print(response.json())


def example_extract_germany_centered():
    """Example: Extract Germany using center point"""
    print_section("6. Kartenausschnitt: Deutschland (zentriert, LAEA)")
    
    payload = {
        "input_svg": "Weltkarte.svg",
        "center": [10.5, 51.0],  # Zentrum Deutschlands
        "span_lon": 15.0,
        "span_lat": 10.0,
        "input_bounds": [-180, -90, 180, 90],
        "output_width": 600,
        "reproject": True,
        "projection": "laea",
        "output_filename": "deutschland.svg"
    }
    
    print("Request:")
    print(json.dumps(payload, indent=2))
    print("\nExtrahiert Deutschland mit 15° Länge und 10° Breite")
    print("Mit Lambert Azimuthal Equal-Area (flächentreu)")
    
    response = requests.post(
        f"{BASE_URL}/extract/center",
        json=payload
    )
    
    if response.status_code == 200:
        output_file = "output_deutschland.svg"
        with open(output_file, 'wb') as f:
            f.write(response.content)
        print(f"\n✓ Erfolg! Deutschland-Karte gespeichert als: {output_file}")
    else:
        print(f"\n✗ Fehler: {response.status_code}")
        print(response.json())


def example_extract_americas_ortho():
    """Example: Extract Americas with Orthographic projection"""
    print_section("7. Kartenausschnitt: Amerika (Orthographic)")
    
    payload = {
        "input_svg": "Weltkarte.svg",
        "center": [-95, 35],  # Zentrum USA
        "span_lon": 120.0,
        "span_lat": 90.0,
        "input_bounds": [-180, -90, 180, 90],
        "output_width": 800,
        "reproject": True,
        "projection": "ortho",
        "output_filename": "americas_globe.svg"
    }
    
    print("Request:")
    print(json.dumps(payload, indent=2))
    print("\nExtrahiert Amerika mit Orthographischer Projektion")
    print("Erzeugt eine 'Globus-Ansicht'")
    
    response = requests.post(
        f"{BASE_URL}/extract/center",
        json=payload
    )
    
    if response.status_code == 200:
        output_file = "output_americas_ortho.svg"
        with open(output_file, 'wb') as f:
            f.write(response.content)
        print(f"\n✓ Erfolg! Amerika-Globus gespeichert als: {output_file}")
    else:
        print(f"\n✗ Fehler: {response.status_code}")
        print(response.json())


def example_file_upload():
    """Example: Upload a file and reproject it"""
    print_section("8. Datei-Upload: Reprojektion mit Upload")
    
    # Check if we have a test file
    test_file = "Weltkarte.svg"
    if not Path(test_file).exists():
        print(f"✗ Testdatei '{test_file}' nicht gefunden. Überspringe...")
        return
    
    with open(test_file, 'rb') as f:
        files = {'file': f}
        data = {
            'direction': 'plate-to-equal',
            'output_width': '1200',
            'padding': '0.05'
        }
        
        print(f"Uploading: {test_file}")
        print("Parameters:")
        print(json.dumps(data, indent=2))
        
        response = requests.post(
            f"{BASE_URL}/reproject/",
            files=files,
            data=data
        )
    
    if response.status_code == 200:
        output_file = "output_uploaded.svg"
        with open(output_file, 'wb') as f:
            f.write(response.content)
        print(f"\n✓ Erfolg! Upload und Reprojektion abgeschlossen: {output_file}")
    else:
        print(f"\n✗ Fehler: {response.status_code}")
        print(response.json())


def main():
    """Run all examples"""
    print("\n" + "=" * 80)
    print("  CartA API - Beispiel-Nutzung")
    print("  " + "=" * 76)
    print("  " + "Stellen Sie sicher, dass die API läuft: python api_main.py")
    print("=" * 80)
    
    try:
        # Test health check first
        health_check()
        
        # Run examples
        example_reproject_plate_to_equal()
        example_reproject_plate_to_wagner()
        example_extract_europe()
        example_extract_germany_centered()
        example_extract_americas_ortho()
        
        # Only run these if previous examples succeeded
        if Path("output_equal_earth.svg").exists():
            example_reproject_equal_to_plate()
        
        example_file_upload()
        
        print_section("Zusammenfassung")
        print("✓ Alle Beispiele erfolgreich ausgeführt!")
        print("\nErstelle Dateien:")
        for file in Path(".").glob("output_*.svg"):
            size = file.stat().st_size
            print(f"  - {file.name} ({size:,} bytes)")
        
    except requests.exceptions.ConnectionError:
        print("\n✗ Fehler: Kann nicht mit API verbinden.")
        print("  Stellen Sie sicher, dass die API läuft:")
        print("  $ python api_main.py")
    except Exception as e:
        print(f"\n✗ Unerwarteter Fehler: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
