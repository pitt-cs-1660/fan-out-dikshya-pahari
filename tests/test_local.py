"""
local unit tests for lambda handlers.
run with: python -m pytest tests/test_local.py -v

note: these tests mock boto3 so no AWS credentials are needed.
"""

import json
import sys
import os
from unittest.mock import patch, MagicMock
import pytest

# add lambda directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'metadata_extractor'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'image_validator'))


def make_sns_event(key, bucket="cc-images-testuser", size=102400, event_time="2026-03-08T12:00:00.000Z"):
    """helper to create a mock SNS event wrapping an S3 event."""
    s3_event = {
        "Records": [{
            "eventVersion": "2.1",
            "eventSource": "aws:s3",
            "awsRegion": "us-east-1",
            "eventTime": event_time,
            "eventName": "ObjectCreated:Put",
            "s3": {
                "s3SchemaVersion": "1.0",
                "bucket": {
                    "name": bucket,
                    "arn": f"arn:aws:s3:::{bucket}"
                },
                "object": {
                    "key": key,
                    "size": size
                }
            }
        }]
    }

    return {
        "Records": [{
            "EventSource": "aws:sns",
            "Sns": {
                "Message": json.dumps(s3_event)
            }
        }]
    }


class TestMetadataExtractor:
    """tests for the metadata-extractor lambda."""

    @patch('lambda_function.s3')
    def test_valid_image_metadata(self, mock_s3, capsys):
        """test that metadata is extracted, logged, and written to S3."""
        import importlib
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'metadata_extractor'))
        mod = importlib.import_module('lambda_function')
        importlib.reload(mod)

        with patch.object(mod, 's3') as mock_s3:
            event = make_sns_event("uploads/test.jpg", size=102400)
            result = mod.lambda_handler(event, None)

            assert result["statusCode"] == 200

            captured = capsys.readouterr()
            assert "[METADATA] File: uploads/test.jpg" in captured.out
            assert "[METADATA] Bucket: cc-images-testuser" in captured.out
            assert "[METADATA] Size: 102400 bytes" in captured.out
            assert "[METADATA] Upload Time:" in captured.out

            # verify S3 put_object was called for metadata JSON
            mock_s3.put_object.assert_called_once()
            call_args = mock_s3.put_object.call_args
            assert call_args[1]['Bucket'] == 'cc-images-testuser'
            assert call_args[1]['Key'] == 'processed/metadata/test.json'
            assert call_args[1]['ContentType'] == 'application/json'

            # verify the JSON content
            body = json.loads(call_args[1]['Body'])
            assert body['file'] == 'uploads/test.jpg'
            assert body['bucket'] == 'cc-images-testuser'
            assert body['size'] == 102400

    @patch('lambda_function.s3')
    def test_multiple_fields_present(self, mock_s3, capsys):
        """test that all four metadata fields are logged."""
        import importlib
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'metadata_extractor'))
        mod = importlib.import_module('lambda_function')
        importlib.reload(mod)

        with patch.object(mod, 's3'):
            event = make_sns_event("uploads/photo.png", size=204800)
            mod.lambda_handler(event, None)

            captured = capsys.readouterr()
            metadata_lines = [line for line in captured.out.split('\n') if '[METADATA]' in line]
            assert len(metadata_lines) >= 4


class TestImageValidator:
    """tests for the image-validator lambda."""

    @pytest.mark.parametrize("filename", [
        "uploads/test.jpg",
        "uploads/test.jpeg",
        "uploads/test.png",
        "uploads/test.gif",
        "uploads/TEST.JPG",
    ])
    def test_valid_image_extensions(self, filename, capsys):
        """test that valid image extensions pass validation and are copied to S3."""
        import importlib
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'image_validator'))
        mod = importlib.import_module('lambda_function')
        importlib.reload(mod)

        with patch.object(mod, 's3') as mock_s3:
            event = make_sns_event(filename)
            result = mod.lambda_handler(event, None)

            assert result["statusCode"] == 200
            captured = capsys.readouterr()
            assert "[VALID]" in captured.out

            # verify S3 copy was called
            mock_s3.copy_object.assert_called_once()

    @pytest.mark.parametrize("filename", [
        "uploads/document.txt",
        "uploads/spreadsheet.csv",
        "uploads/archive.zip",
        "uploads/script.py",
    ])
    def test_invalid_file_extensions(self, filename, capsys):
        """test that invalid file extensions raise ValueError (triggers DLQ)."""
        import importlib
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'image_validator'))
        mod = importlib.import_module('lambda_function')
        importlib.reload(mod)

        with patch.object(mod, 's3') as mock_s3:
            event = make_sns_event(filename)

            with pytest.raises(ValueError):
                mod.lambda_handler(event, None)

            captured = capsys.readouterr()
            assert "[INVALID]" in captured.out

            # verify S3 copy was NOT called for invalid files
            mock_s3.copy_object.assert_not_called()

    def test_is_valid_image_helper(self):
        """test the is_valid_image helper function directly."""
        import importlib
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'image_validator'))
        mod = importlib.import_module('lambda_function')
        importlib.reload(mod)

        assert mod.is_valid_image("photo.jpg") is True
        assert mod.is_valid_image("photo.JPEG") is True
        assert mod.is_valid_image("photo.png") is True
        assert mod.is_valid_image("photo.gif") is True
        assert mod.is_valid_image("document.txt") is False
        assert mod.is_valid_image("archive.zip") is False
