# S3 Bucket Setup Guide

## Overview

Amazon S3 (Simple Storage Service) will serve as the trigger point for your event-driven architecture. When images are uploaded to the `uploads/` prefix in your bucket, they will trigger your Lambda functions through SNS.

## Prerequisites

- AWS Account
- AWS CLI installed and configured
- your Pitt username

## Step 1: Create S3 Bucket

Your bucket name must follow the format: `cc-images-{pitt-username}`

For example, if your Pitt username is `dpm79`, your bucket name will be: `cc-images-dpm79`

```bash
# replace <your-pitt-username> with your actual Pitt username
aws s3 mb s3://cc-images-<your-pitt-username> --region us-east-1
```

## Step 2: Create Required Prefixes

Your bucket needs an input prefix and output prefixes for processed results:

```bash
BUCKET_NAME="cc-images-<your-pitt-username>"

# create input prefix
aws s3api put-object --bucket $BUCKET_NAME --key uploads/

# create output prefixes
aws s3api put-object --bucket $BUCKET_NAME --key processed/metadata/
aws s3api put-object --bucket $BUCKET_NAME --key processed/valid/
```

## Step 3: Verify Bucket Structure

Check that the prefix was created:

```bash
aws s3 ls s3://cc-images-<your-pitt-username>/
```

You should see:
```
                           PRE processed/
                           PRE uploads/
```

## Step 4: Configure S3 Event Notifications

S3 event notifications will be configured in the [SNS Setup Guide](./sns-setup.md) after creating your SNS topic.

## Step 5: Grant Grading Access

You need to give me permission to upload artifacts to your bucket.

Create a file named `bucket-policy.json` (replace `<your-pitt-username>` with your actual username):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::523734927941:user/danatpitt"
      },
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::cc-images-<your-pitt-username>",
        "arn:aws:s3:::cc-images-<your-pitt-username>/*"
      ]
    }
  ]
}
```

Apply the policy:

```bash
aws s3api put-bucket-policy \
  --bucket cc-images-<your-pitt-username> \
  --policy file://bucket-policy.json
```

**note:** this does not make your bucket public. It only grants the instructor's IAM identity access to read, write, and list objects in your bucket for grading.

## Bucket Structure Summary

```
cc-images-<your-pitt-username>/
├── uploads/                    # upload images here to trigger the pipeline
└── processed/
    ├── metadata/               # metadata-extractor writes JSON files here
    └── valid/                  # image-validator copies valid images here
```

## Cleanup (After Project Completion)

```bash
# delete all objects first
aws s3 rm s3://cc-images-<your-pitt-username> --recursive

# delete the bucket
aws s3 rb s3://cc-images-<your-pitt-username>
```
