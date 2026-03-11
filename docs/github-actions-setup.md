# GitHub Actions Setup Guide

## Overview

GitHub Actions will automate the deployment of your Lambda functions. When you push code changes, the workflow will automatically build Docker images, push them to ECR, and update (or create) your Lambda functions.

## Prerequisites

- GitHub repository with this project code
- ECR repositories created ([ECR Setup](./ecr-setup.md))
- Lambda execution role created ([Lambda Setup](./lambda-setup.md))
- AWS CLI installed and configured

## Step 1: Get Your AWS Credentials

You'll need your AWS Access Key ID and Secret Access Key. If you don't have them:

```bash
# get your current user
aws sts get-caller-identity

# if you need to create new access keys
aws iam create-access-key --user-name <your-iam-username>
```

**Important:** Keep these credentials secure and never commit them to your repository.

## Step 2: Add Secrets to GitHub Repository

Add the following secrets to your GitHub repository:

1. Go to your repository on GitHub
2. Click **Settings** > **Secrets and variables** > **Actions**
3. Click **New repository secret**
4. Add these secrets:

### AWS_ACCESS_KEY_ID
Value: Your AWS Access Key ID

### AWS_SECRET_ACCESS_KEY
Value: Your AWS Secret Access Key

## Step 3: Understanding the GitHub Actions Workflow

The workflow file is located at `.github/workflows/deploy.yml`. This workflow will automatically build, push, and deploy your Lambda functions when you push to the main branch.

### Key Configuration: AWS Credentials

The workflow uses your GitHub secrets to authenticate with AWS:

```yaml
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
    aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    aws-region: ${{ env.AWS_REGION }}
```

This step:
- reads your AWS credentials from GitHub secrets
- configures the GitHub Actions runner to use these credentials
- sets the AWS region for all subsequent AWS CLI commands

### Workflow Structure

The workflow has two jobs, one for each Lambda function:
1. `deploy-metadata-extractor` - builds and pushes metadata-extractor
2. `deploy-image-validator` - builds and pushes image-validator

Each job:
1. checks out your code
2. configures AWS credentials using the secrets
3. logs into Amazon ECR
4. builds the Docker image
5. tags and pushes the image to ECR
6. creates or updates the Lambda function

## Step 4: Update the Lambda Role ARN

You need to update the `AWS_LAMBDA_ROLE_ARN` environment variable in `.github/workflows/deploy.yml` with the role ARN you created in the Lambda Setup guide.

### Example: Build, Tag, and Push Step

Here's what the TODO section in each job should look like (using metadata-extractor as an example):

```yaml
- name: Build, tag, and push metadata-extractor image to Amazon ECR
  env:
    ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
    ECR_REPOSITORY: metadata-extractor
    IMAGE_TAG: ${{ github.sha }}
  run: |
    cd lambda/metadata_extractor
    docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
    docker tag $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG $ECR_REGISTRY/$ECR_REPOSITORY:latest
    docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
    docker push $ECR_REGISTRY/$ECR_REPOSITORY:latest
    echo "image=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG" >> $GITHUB_OUTPUT
```

### Understanding the Docker Commands

1. **Navigate to lambda directory**: `cd lambda/metadata_extractor`
   - changes to the directory containing the Dockerfile

2. **Build the image**: `docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .`
   - builds the Docker image using the Dockerfile
   - tags it with your ECR registry URL and the git commit SHA

3. **Tag with latest**: `docker tag ...`
   - creates an additional tag `latest` pointing to the same image

4. **Push specific tag**: `docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG`
   - pushes the image with the commit SHA tag to ECR

5. **Push latest tag**: `docker push $ECR_REGISTRY/$ECR_REPOSITORY:latest`
   - pushes the latest tag to ECR

6. **Output image URI**: `echo "image=..." >> $GITHUB_OUTPUT`
   - saves the newly deployed image URI into a variable for the next step

## Step 5: Verify Deployment

After the workflow completes successfully, verify your Lambda functions were created/updated:

```bash
# list Lambda functions
aws lambda list-functions \
  --query 'Functions[?FunctionName==`metadata-extractor` || FunctionName==`image-validator`].FunctionName' \
  --region us-east-1

# check function details
aws lambda get-function --function-name metadata-extractor --region us-east-1

# verify the image URI points to your ECR
aws lambda get-function --function-name metadata-extractor --region us-east-1 \
  --query 'Code.ImageUri' \
  --output text
```
