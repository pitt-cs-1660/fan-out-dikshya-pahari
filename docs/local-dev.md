# Local Development Guide

This guide will help you test your Lambda functions locally before deploying to AWS.

## Prerequisites

- Python 3.13 installed
- Docker Desktop installed
- AWS CLI installed and configured

## Setting Up Your Development Environment

### 1. Navigate to a Lambda Function Directory

```bash
cd lambda/metadata_extractor  # or image_validator
```

### 2. Implement Your Lambda Handler

Edit `lambda_function.py` to implement your logic. The handler should:

**metadata_extractor:**
- parse the SNS event to get the S3 event
- extract bucket name, object key, file size, and upload time
- log metadata in the required `[METADATA]` format
- write a JSON metadata file to `processed/metadata/{filename}.json`

**image_validator:**
- parse the SNS event to get the S3 event
- check if the file extension is a valid image type
- if valid: log `[VALID]` and copy the file to `processed/valid/`
- if invalid: log `[INVALID]` and raise an exception (triggers DLQ)

### Python Refresher

if you're rusty on Python, here are the building blocks you'll need:

**looping through a list of dicts:**

```python
data = {"items": [{"name": "alice"}, {"name": "bob"}]}

for item in data["items"]:
    print(item["name"])
# alice
# bob
```

**parsing a JSON string into a dict:**

```python
import json

raw = '{"key": "uploads/photo.jpg", "size": 102400}'
parsed = json.loads(raw)  # string --> dict
print(parsed["key"])      # uploads/photo.jpg
print(parsed["size"])     # 102400
```

**extracting a filename from a path:**

```python
import os

key = "uploads/test-image.jpg"
filename = key.split("/")[-1]           # "test-image.jpg"
name, ext = os.path.splitext(filename)  # ("test-image", ".jpg")
```

**writing a dict as JSON to S3 with boto3:**

```python
import json
import boto3

s3 = boto3.client("s3")

metadata = {"file": "uploads/test.jpg", "bucket": "my-bucket", "size": 102400}

s3.put_object(
    Bucket="my-bucket",
    Key="output/test.json",
    Body=json.dumps(metadata),
    ContentType="application/json"
)
```

**copying an object within the same S3 bucket:**

```python
s3.copy_object(
    Bucket="my-bucket",
    Key="processed/valid/test.jpg",
    CopySource={"Bucket": "my-bucket", "Key": "uploads/test.jpg"}
)
```

## Local Testing

> **why no `pip install` in the Dockerfile?** these lambdas only depend on `boto3` (the AWS SDK for Python), which is pre-installed in the `public.ecr.aws/lambda/python:3.13` base image. in a real-world lambda with third-party dependencies (e.g. Pillow, requests, pandas), you would add a `requirements.txt` and a `RUN pip install -r requirements.txt` step in the Dockerfile. this assignment keeps things simple so you can focus on the event-driven architecture rather than dependency management.

### Setting Up a Virtual Environment

for local testing outside Docker, you need `boto3` installed. **always use a virtual environment** rather than installing packages globally:

```bash
# create a virtual environment (run from the project root)
python3 -m venv .venv

# activate it
source .venv/bin/activate    # linux/mac
# .venv\Scripts\activate     # windows

# install dependencies
pip install boto3 pytest
```

> **note:** make sure to activate the virtual environment (`source .venv/bin/activate`) each time you open a new terminal before running any of the test methods below.

### Method 1: Test with Docker (Most Realistic)

Build and test your Lambda container locally to ensure it works exactly as it will in AWS. this method does **not** require the virtual environment since everything runs inside the container.

each lambda directory includes sample test event JSON files you can use:
- `lambda/metadata_extractor/test-event.json` — valid image upload
- `lambda/image_validator/test-event-valid.json` — valid image upload
- `lambda/image_validator/test-event-invalid.json` — invalid file upload (.txt)

**metadata-extractor:**

```bash
cd lambda/metadata_extractor
docker build -t metadata-extractor:test .
docker run --rm -p 9000:8080 \
  -e AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id) \
  -e AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key) \
  -e AWS_DEFAULT_REGION=us-east-1 \
  metadata-extractor:test

# in another terminal
curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" \
  -d @test-event.json
```

**image-validator:**

```bash
cd lambda/image_validator
docker build -t image-validator:test .
docker run --rm -p 9000:8080 \
  -e AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id) \
  -e AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key) \
  -e AWS_DEFAULT_REGION=us-east-1 \
  image-validator:test

# in another terminal — valid image (should succeed)
curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" \
  -d @test-event-valid.json

# invalid file (should return an error)
curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" \
  -d @test-event-invalid.json
```

> **note:** the `-e` flags pass your AWS credentials into the container so the S3 calls work locally. without them, event parsing and log output still work — only the S3 writes will fail. once deployed to AWS, the lambda execution role provides credentials automatically.

### Method 2: Test with Python Directly

with your virtual environment activated, you can test with a mock event. note that the handler will make real S3 calls, so you need valid AWS credentials configured:

```bash
cd lambda/metadata_extractor
python -c "
import json
from lambda_function import lambda_handler

# create a mock SNS event
event = {
    'Records': [{
        'Sns': {
            'Message': json.dumps({
                'Records': [{
                    'eventTime': '2026-03-08T12:00:00.000Z',
                    's3': {
                        'bucket': {'name': 'cc-images-testuser'},
                        'object': {'key': 'uploads/test.jpg', 'size': 102400}
                    }
                }]
            })
        }
    }]
}

result = lambda_handler(event, None)
print(json.dumps(result, indent=2))
"
```

### Method 3: Test with pytest (Recommended for Local)

the `tests/test_local.py` file mocks boto3 so you can test your handler logic without AWS credentials or a real S3 bucket. with your virtual environment activated:

```bash
python -m pytest tests/test_local.py -v
```

### Method 4: Test in the AWS Console (Once Deployed)

Once your Lambda function is deployed to AWS, you can test it directly in the console UI:

1. open the [Lambda functions page](https://console.aws.amazon.com/lambda/home#/functions) in the AWS console
2. click on your function name (e.g. `metadata-extractor`)
3. select the **Test** tab
4. under **Test event**, choose **Create new event**
5. give it a name like `test-valid-image`
6. paste the contents of one of the test event JSON files (from your lambda directory) into the editor
7. click **Test**
8. expand **Details** under **Execution result** to see the function output and logs

this is the easiest way to debug once your image is live in ECR, since it runs against your real S3 bucket and you can see CloudWatch logs inline. see the [AWS docs on testing Lambda functions](https://docs.aws.amazon.com/lambda/latest/dg/testing-functions.html) for more details.

## Debugging Tips

### Understanding the SNS Event Structure

When S3 sends an event to SNS, and SNS invokes Lambda, the event is **double-wrapped**:

```python
# lambda receives this structure:
event = {
    "Records": [{
        "Sns": {
            "Message": "{\"Records\":[{\"s3\":{...}}]}"  # this is a STRING, not dict!
        }
    }]
}

# you must parse it like this:
for record in event['Records']:
    sns_message = record['Sns']['Message']  # this is a JSON string
    s3_event = json.loads(sns_message)       # parse the string to dict
    for s3_record in s3_event['Records']:
        bucket = s3_record['s3']['bucket']['name']
        key = s3_record['s3']['object']['key']
```

### Common Mistakes

| Mistake | Solution |
|---------|----------|
| `KeyError: 'Records'` | check if you're parsing the SNS Message correctly (it's a JSON string) |
| `TypeError: string indices must be integers` | you forgot to `json.loads()` the SNS Message |
| Lambda not triggered | verify SNS subscription shows "Confirmed" |
| DLQ not receiving messages | verify DLQ is attached to Lambda, not SNS. also verify you are raising an exception, not returning an error |

### AWS Credentials for Local Testing

For local testing with actual S3 buckets, ensure your AWS credentials are configured:

```bash
aws configure
```

Or set environment variables:
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```
