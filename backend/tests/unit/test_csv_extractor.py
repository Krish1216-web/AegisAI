import pytest
import os
import tempfile

from app.services.extractors.csv import CSVExtractor

def test_csv_extractor_comma():
    extractor = CSVExtractor()
    csv_data = "Name,Age,Role\nAlice,30,Auditor\nBob,28,Admin"
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as f:
        f.write(csv_data.encode("utf-8"))
        temp_path = f.name
        
    try:
        res = extractor.extract(temp_path)
        assert "Name | Age | Role" in res.text
        assert "Alice | 30 | Auditor" in res.text
        assert res.metadata["delimiter"] == ","
        assert res.metadata["column_count"] == 3
        assert res.metadata["row_count"] == 3
    finally:
        os.remove(temp_path)

def test_csv_extractor_semicolon():
    extractor = CSVExtractor()
    csv_data = "City;Country;Pop\nLondon;UK;9M\nParis;France;2.1M"
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as f:
        f.write(csv_data.encode("utf-8"))
        temp_path = f.name
        
    try:
        res = extractor.extract(temp_path)
        assert "City | Country | Pop" in res.text
        assert "London | UK | 9M" in res.text
        assert res.metadata["delimiter"] == ";"
        assert res.metadata["column_count"] == 3
        assert res.metadata["row_count"] == 3
    finally:
        os.remove(temp_path)
