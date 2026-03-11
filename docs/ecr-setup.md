# ECR Setup Guide

## Overview

Amazon Elastic Container Registry (ECR) is a fully managed Docker container registry that makes it easy to store, manage, and deploy Docker container images. For this project, you'll create two ECR repositories to store your Lambda function container images.

## Prerequisites

- AWS Account
- AWS CLI installed and configured

## Step 1: Create ECR Repositories

You need to create two ECR repositories, one for each Lambda function. They must be named: `metadata-extractor` and `image-validator`.

Run the create repository command for each:

```bash
aws ecr create-repository \
  --repository-name metadata-extractor \
  --region us-east-1

aws ecr create-repository \
  --repository-name image-validator \
  --region us-east-1
```

## Step 2: Verify Repository Creation

List your repositories to confirm they were created:

```bash
aws ecr describe-repositories \
  --repository-names metadata-extractor image-validator \
  --region us-east-1
```

You should see output containing both repositories:
```json
{
    "repositories": [
        {
            "repositoryArn": "arn:aws:ecr:us-east-1:AWS_ACCOUNT_ID:repository/metadata-extractor",
            "registryId": "AWS_ACCOUNT_ID",
            "repositoryName": "metadata-extractor",
            "repositoryUri": "AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/metadata-extractor",
            "createdAt": "2026-03-08T10:00:00.000000-05:00",
            "imageTagMutability": "MUTABLE",
            "imageScanningConfiguration": {
                "scanOnPush": false
            },
            "encryptionConfiguration": {
                "encryptionType": "AES256"
            }
        },
        {
            "repositoryArn": "arn:aws:ecr:us-east-1:AWS_ACCOUNT_ID:repository/image-validator",
            "registryId": "AWS_ACCOUNT_ID",
            "repositoryName": "image-validator",
            "repositoryUri": "AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/image-validator",
            "createdAt": "2026-03-08T10:00:05.000000-05:00",
            "imageTagMutability": "MUTABLE",
            "imageScanningConfiguration": {
                "scanOnPush": false
            },
            "encryptionConfiguration": {
                "encryptionType": "AES256"
            }
        }
    ]
}
```

## Step 3: Note Your Repository URIs

Each repository has a unique URI in the format:
```
{AWS_ACCOUNT_ID}.dkr.ecr.{AWS_REGION}.amazonaws.com/{REPOSITORY_NAME}
```

Get your repository URIs:

```bash
aws ecr describe-repositories \
  --repository-names metadata-extractor image-validator \
  --region us-east-1 \
  --query 'repositories[*].[repositoryName,repositoryUri]' \
  --output table
```

Save these URIs - you'll need them for GitHub Actions configuration.

## Cleanup (After Project Completion)

To delete repositories and all images:

```bash
aws ecr delete-repository --repository-name metadata-extractor --force --region us-east-1
aws ecr delete-repository --repository-name image-validator --force --region us-east-1
```
