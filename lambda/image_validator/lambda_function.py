import json
import os
import boto3

s3 = boto3.client('s3')

VALID_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif']

def is_valid_image(key):
    """check if the file has a valid image extension."""
    _, ext = os.path.splitext(key.lower())
    return ext in VALID_EXTENSIONS

def lambda_handler(event, context):
    """
    validates that uploaded files are images.
    raises exception for invalid files (triggers DLQ).

    for valid files, copies the object to the processed/valid/ prefix
    in the same bucket so grading can verify output via S3.

    event structure (SNS wraps the S3 event):
    {
        "Records": [{
            "Sns": {
                "Message": "{\"Records\":[{\"s3\":{...}}]}"  # this is a JSON string!
            }
        }]
    }

    required log format:
        [VALID] {key} is a valid image file
        [INVALID] {key} is not a valid image type

    required S3 output (valid files only):
        copies the file to processed/valid/{filename}
        e.g. uploads/test.jpg -> processed/valid/test.jpg

    important: to trigger the DLQ, you must raise an exception (not return an error).
    """

    print("=== image validator invoked ===")

    # loop through SNS records
    for record in event['Records']:
        # get the SNS message string and parse it as JSON to get the S3 event
        sns_message = record['Sns']['Message']
        s3_event = json.loads(sns_message)

        # loop through the S3 records inside the SNS message
        for s3_record in s3_event['Records']:
            # extract bucket and key from the S3 event
            bucket = s3_record['s3']['bucket']['name']
            key    = s3_record['s3']['object']['key']

            if is_valid_image(key):
                # log valid message
                print(f"[VALID] {key} is a valid image file")

                # get just the filename: "uploads/test.jpg" -> "test.jpg"
                filename = key.split('/')[-1]

                # copy valid file to processed/valid/{filename}
                s3.copy_object(
                    Bucket=bucket,
                    Key=f"processed/valid/{filename}",
                    CopySource={'Bucket': bucket, 'Key': key}
                )

                print(f"[VALID] Copied to s3://{bucket}/processed/valid/{filename}")

            else:
                # log invalid message
                print(f"[INVALID] {key} is not a valid image type")

                # raise exception to trigger the DLQ
                raise ValueError(f"[INVALID] {key} is not a valid image type")

    return {'statusCode': 200, 'body': 'validation complete'}