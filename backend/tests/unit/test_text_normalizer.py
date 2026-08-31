import pytest
from app.services.text_normalizer import normalize_text, remove_control_characters, normalize_line_endings, normalize_whitespace

def test_remove_control_characters():
    # \x00 is control char, \n and \t are allowed whitespaces
    input_str = "Hello\x00World\nGood\x07Day\t!"
    assert remove_control_characters(input_str) == "HelloWorld\nGoodDay\t!"

def test_normalize_line_endings():
    # Convert \r\n to \n and limit 3+ newlines to 2
    input_str = "Para1\r\n\r\n\r\nPara2\n\n\n\n\nPara3"
    assert normalize_line_endings(input_str) == "Para1\n\nPara2\n\nPara3"

def test_normalize_whitespace():
    # Condense multiple horizontal spaces/tabs but keep newlines intact
    input_str = "Name\t\tAge    Role\nBob   28   Admin"
    assert normalize_whitespace(input_str) == "Name Age Role\nBob 28 Admin"

def test_normalize_text_full():
    input_str = "  Héllò \x00 World!\r\n\r\n\r\nThis is    a test.  "
    assert normalize_text(input_str) == "Héllò World!\n\nThis is a test."
