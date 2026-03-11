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

    # todo: loop through event['Records']
    # todo: for each record, get the SNS message string from record['Sns']['Message']
    # todo: parse the SNS message string as JSON to get the S3 event
    # todo: loop through the S3 event's 'Records'
    # todo: extract bucket name from s3_record['s3']['bucket']['name']
    # todo: extract object key from s3_record['s3']['object']['key']
    # todo: use is_valid_image() to check the file extension
    # todo: if valid:
    #         - print the [VALID] message: print(f"[VALID] {key} is a valid image file")
    #         - get the filename from the key (e.g. "uploads/test.jpg" -> "test.jpg")
    #           hint: use key.split('/')[-1]
    #         - copy the object to processed/valid/{filename}
    #           hint: s3.copy_object(Bucket=bucket, Key=f"processed/valid/{filename}",
    #                 CopySource={'Bucket': bucket, 'Key': key})
    # todo: if invalid:
    #         - print the [INVALID] message: print(f"[INVALID] {key} is not a valid image type")
    #         - raise ValueError to trigger DLQ

    return {'statusCode': 200, 'body': 'validation complete'}
