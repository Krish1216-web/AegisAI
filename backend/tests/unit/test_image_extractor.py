import pytest
import os
import tempfile
from PIL import Image

from app.services.extractors.image import ImageExtractor, MockOCRProvider

def test_image_extractor_metadata():
    extractor = ImageExtractor()
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as f:
        temp_path = f.name
        
    try:
        # Create a simple 100x100 PNG image
        img = Image.new("RGB", (100, 100), color="blue")
        img.save(temp_path, "PNG")
        
        res = extractor.extract(temp_path)
        assert res.metadata["width"] == 100
        assert res.metadata["height"] == 100
        assert res.metadata["format"] == "PNG"
        assert res.metadata["ocr_available"] is False
        assert res.text == ""
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
