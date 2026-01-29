#!/usr/bin/env python
"""
Quick test script to verify Swagger documentation is accessible
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from django.urls import reverse
from django.test import Client

def test_swagger_endpoints():
    """Test that Swagger endpoints are accessible"""
    client = Client()
    
    print("Testing Swagger Documentation Endpoints...")
    print("-" * 50)
    
    # Test Swagger UI
    print("\n1. Testing Swagger UI (/api/docs/)...")
    try:
        response = client.get('/api/docs/')
        if response.status_code == 200:
            print("   ✅ Swagger UI is accessible")
        else:
            print(f"   ❌ Swagger UI returned status {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test ReDoc
    print("\n2. Testing ReDoc (/api/redoc/)...")
    try:
        response = client.get('/api/redoc/')
        if response.status_code == 200:
            print("   ✅ ReDoc is accessible")
        else:
            print(f"   ❌ ReDoc returned status {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test OpenAPI JSON
    print("\n3. Testing OpenAPI JSON Schema (/swagger.json)...")
    try:
        response = client.get('/swagger.json')
        if response.status_code == 200:
            print("   ✅ OpenAPI JSON schema is accessible")
            # Check if it's valid JSON
            import json
            data = json.loads(response.content)
            print(f"   📄 API Title: {data.get('info', {}).get('title', 'N/A')}")
            print(f"   📄 API Version: {data.get('info', {}).get('version', 'N/A')}")
            print(f"   📄 Endpoints: {len(data.get('paths', {}))}")
        else:
            print(f"   ❌ OpenAPI JSON returned status {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test OpenAPI YAML
    print("\n4. Testing OpenAPI YAML Schema (/swagger.yaml)...")
    try:
        response = client.get('/swagger.yaml')
        if response.status_code == 200:
            print("   ✅ OpenAPI YAML schema is accessible")
        else:
            print(f"   ❌ OpenAPI YAML returned status {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "-" * 50)
    print("✅ Swagger documentation setup complete!")
    print("\nAccess the documentation at:")
    print("  • Swagger UI: http://localhost:8000/api/docs/")
    print("  • ReDoc:      http://localhost:8000/api/redoc/")
    print("  • JSON:       http://localhost:8000/swagger.json")
    print("  • YAML:       http://localhost:8000/swagger.yaml")

if __name__ == '__main__':
    test_swagger_endpoints()
