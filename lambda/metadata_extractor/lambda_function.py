import json
import os
import boto3
from datetime import datetime

s3 = boto3.client('s3')

def lambda_handler(event, context):
    """
    extracts metadata from S3 upload events received via SNS.
    logs file information to CloudWatch and writes a JSON metadata
    file to the processed/metadata/ prefix in the same bucket.

    event structure (SNS wraps the S3 event):
    {
        "Records": [{
            "Sns": {
                "Message": "{\"Records\":[{\"s3\":{...}}]}"  # this is a JSON string!
            }
        }]
    }

    required log format:
        [METADATA] File: {key}
        [METADATA] Bucket: {bucket}
        [METADATA] Size: {size} bytes
        [METADATA] Upload Time: {timestamp}

    required S3 output:
        writes a JSON file to processed/metadata/{filename}.json containing:
        {
            "file": "{key}",
            "bucket": "{bucket}",
            "size": {size},
            "upload_time": "{timestamp}"
        }
    """

    print("=== metadata extractor invoked ===")

    # loop through SNS records
    for record in event['Records']:
        # get the SNS message string and parse it as JSON to get the S3 event
        sns_message = record['Sns']['Message']
        s3_event = json.loads(sns_message)

        # loop through the S3 records inside the SNS message
        for s3_record in s3_event['Records']:
            # extract fields from the S3 event
            bucket     = s3_record['s3']['bucket']['name']
            key        = s3_record['s3']['object']['key']
            size       = s3_record['s3']['object']['size']
            event_time = s3_record['eventTime']

            # log metadata in the required [METADATA] format
            print(f"[METADATA] File: {key}")
            print(f"[METADATA] Bucket: {bucket}")
            print(f"[METADATA] Size: {size} bytes")
            print(f"[METADATA] Upload Time: {event_time}")

            # build the metadata dict
            metadata = {
                "file":        key,
                "bucket":      bucket,
                "size":        size,
                "upload_time": event_time
            }

            # derive filename without extension: "uploads/test.jpg" -> "test"
            filename = os.path.splitext(key.split('/')[-1])[0]

            # write metadata JSON to processed/metadata/{filename}.json
            s3.put_object(
                Bucket=bucket,
                Key=f"processed/metadata/{filename}.json",
                Body=json.dumps(metadata, indent=4),
                ContentType='application/json'
            )

            print(f"[METADATA] Written to s3://{bucket}/processed/metadata/{filename}.json")

    return {'statusCode': 200, 'body': 'metadata extracted'}