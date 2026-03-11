# Lambda Function Setup Guide

## Overview

AWS Lambda functions will process your image upload events. You'll create two Lambda functions that are triggered by SNS notifications when files are uploaded to the `uploads/` prefix in S3. The Lambda functions are deployed as container images to ECR via [GitHub Actions](../.github/workflows/deploy.yml).

## Prerequisites

- ECR repositories created ([ECR Setup](./ecr-setup.md))
- S3 bucket created ([S3 Setup](./s3-setup.md))
- AWS CLI installed and configured

## Step 1: Create Lambda Execution Role

Lambda functions need an IAM role with permissions to access S3, write to CloudWatch Logs, and send messages to SQS (for the DLQ).

### Create Trust Policy

Create a file named `lambda-trust-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

### Create the IAM Role

```bash
aws iam create-role \
  --role-name lambda-image-processing-role \
  --assume-role-policy-document file://lambda-trust-policy.json
```

### Attach Policies

Attach the necessary managed policies:

```bash
# policy for CloudWatch Logs
aws iam attach-role-policy \
  --role-name lambda-image-processing-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

### Create Custom S3 Access Policy

Create a file named `lambda-s3-policy.json` (replace `<your-pitt-username>` with your actual username):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::cc-images-<your-pitt-username>/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sqs:SendMessage"
      ],
      "Resource": "arn:aws:sqs:us-east-1:<AWS_ACCOUNT_ID>:image-processing-dlq"
    }
  ]
}
```

**Note:** `s3:PutObject` is needed because both lambdas write output to the `processed/` prefix. `s3:GetObject` is needed by the image-validator to copy files.

### Attach the Custom Policy

```bash
aws iam put-role-policy \
  --role-name lambda-image-processing-role \
  --policy-name S3AndSQSAccessPolicy \
  --policy-document file://lambda-s3-policy.json
```

### Get the Role ARN

Save this ARN you'll need it for creating Lambda functions and GitHub Actions:

```bash
aws iam get-role \
  --role-name lambda-image-processing-role \
  --query 'Role.Arn' \
  --output text
```

The output will be something like:
```
arn:aws:iam::ACCOUNT_ID:role/lambda-image-processing-role
```

## Step 2: Create the Dead Letter Queue (DLQ)

The image-validator Lambda needs a DLQ to capture failed validation events (invalid file types).

```bash
aws sqs create-queue \
  --queue-name image-processing-dlq \
  --region us-east-1
```

Save the Queue URL and get the Queue ARN:

```bash
# get queue URL
aws sqs get-queue-url \
  --queue-name image-processing-dlq \
  --region us-east-1

# get queue ARN
aws sqs get-queue-attributes \
  --queue-url <QUEUE_URL> \
  --attribute-names QueueArn \
  --region us-east-1
```

## Step 3: Wait for Initial Image Push

**Important:** Lambda functions that use container images require the image to exist in ECR before you can create the function. You can build and push manually, or let GitHub Actions deploy the image to ECR.

## Step 4: Create Lambda Functions

The GitHub Actions workflow will automatically create Lambda functions when you push code. However, you can also create them manually if needed.

Get your AWS Account ID:

```bash
aws sts get-caller-identity --query 'Account' --output text
```

### Create metadata-extractor

```bash
aws lambda create-function \
  --function-name metadata-extractor \
  --package-type Image \
  --code ImageUri=<AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/metadata-extractor:<IMAGE_TAG> \
  --role <ROLE_ARN> \
  --timeout 30 \
  --memory-size 128 \
  --region us-east-1
```

### Create image-validator (with DLQ)

```bash
aws lambda create-function \
  --function-name image-validator \
  --package-type Image \
  --code ImageUri=<AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/image-validator:<IMAGE_TAG> \
  --role <ROLE_ARN> \
  --timeout 30 \
  --memory-size 128 \
  --dead-letter-config TargetArn=<DLQ_ARN> \
  --region us-east-1
```

**Note:** The `--dead-letter-config` flag is what connects the DLQ to the image-validator. When this Lambda raises an exception, the failed event is sent to the DLQ.

If the function already exists and you need to add the DLQ:

```bash
aws lambda update-function-configuration \
  --function-name image-validator \
  --dead-letter-config TargetArn=<DLQ_ARN> \
  --region us-east-1
```

## Step 5: Grant SNS Invoke Permission

After Lambda functions are created, you need to grant SNS permission to invoke them.

**Note:** You'll need your SNS topic ARN from [SNS Setup](./sns-setup.md). If you haven't created it yet, complete that step first, then return here.

```bash
# grant permission for metadata-extractor
aws lambda add-permission \
  --function-name metadata-extractor \
  --statement-id sns-invoke \
  --action lambda:InvokeFunction \
  --principal sns.amazonaws.com \
  --source-arn arn:aws:sns:us-east-1:<AWS_ACCOUNT_ID>:image-upload-notifications \
  --region us-east-1

# grant permission for image-validator
aws lambda add-permission \
  --function-name image-validator \
  --statement-id sns-invoke \
  --action lambda:InvokeFunction \
  --principal sns.amazonaws.com \
  --source-arn arn:aws:sns:us-east-1:<AWS_ACCOUNT_ID>:image-upload-notifications \
  --region us-east-1
```

## Step 6: Verify Lambda Functions

List your Lambda functions:

```bash
aws lambda list-functions \
  --query 'Functions[?FunctionName==`metadata-extractor` || FunctionName==`image-validator`].FunctionName' \
  --region us-east-1
```

You should see:
```json
[
    "metadata-extractor",
    "image-validator"
]
```

Verify the DLQ is attached to image-validator:

```bash
aws lambda get-function-configuration \
  --function-name image-validator \
  --query 'DeadLetterConfig' \
  --region us-east-1
```

## Cleanup (After Project Completion)

```bash
# delete Lambda functions
aws lambda delete-function --function-name metadata-extractor --region us-east-1
aws lambda delete-function --function-name image-validator --region us-east-1

# delete DLQ
aws sqs delete-queue --queue-url <DLQ_URL> --region us-east-1

# delete IAM role policies
aws iam delete-role-policy --role-name lambda-image-processing-role --policy-name S3AndSQSAccessPolicy

# detach managed policies
aws iam detach-role-policy \
  --role-name lambda-image-processing-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# delete IAM role
aws iam delete-role --role-name lambda-image-processing-role
```
