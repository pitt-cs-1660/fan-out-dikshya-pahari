#!/bin/bash

# colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# check if pitt username is provided
if [ -z "$1" ]; then
    echo -e "${RED}error: pitt username required${NC}"
    echo "usage: $0 <pitt-username>"
    exit 1
fi

PITT_USERNAME="$1"
BUCKET_NAME="cc-images-${PITT_USERNAME}"
RUN_ID=$(date +%s)-$$
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_IMAGE="$SCRIPT_DIR/test-image.jpg"
AWS_REGION="${AWS_REGION:-us-east-1}"

# check if test image exists
if [ ! -f "$TEST_IMAGE" ]; then
    echo -e "${RED}error: test image not found: $TEST_IMAGE${NC}"
    exit 1
fi

echo "===+++++++++++++++++++++++++++++++++++==="
echo "event-driven pipeline test"
echo "===+++++++++++++++++++++++++++++++++++==="
echo "  - bucket: $BUCKET_NAME"
echo "  - run id: $RUN_ID"
echo "  - test image: $TEST_IMAGE"
echo "===+++++++++++++++++++++++++++++++++++==="

SUCCESS_COUNT=0
FAIL_COUNT=0
TOTAL_CHECKS=5

# step 1: upload a valid image
echo ""
echo "step 1: uploading valid image..."
VALID_KEY="uploads/img-${RUN_ID}.jpg"
echo -n "  uploading to s3://${BUCKET_NAME}/${VALID_KEY}... "

if aws s3 cp "$TEST_IMAGE" "s3://${BUCKET_NAME}/${VALID_KEY}" --quiet; then
    echo -e "${GREEN}pass${NC}"
else
    echo -e "${RED}fail${NC}"
    exit 1
fi

# step 2: upload an invalid file
echo ""
echo "step 2: uploading invalid file..."
INVALID_KEY="uploads/doc-${RUN_ID}.txt"
echo "this is not an image" > /tmp/doc-${RUN_ID}.txt
echo -n "  uploading to s3://${BUCKET_NAME}/${INVALID_KEY}... "

if aws s3 cp "/tmp/doc-${RUN_ID}.txt" "s3://${BUCKET_NAME}/${INVALID_KEY}" --quiet; then
    echo -e "${GREEN}pass${NC}"
else
    echo -e "${RED}fail${NC}"
    exit 1
fi

# wait for processing
WAIT_TIME=20
echo ""
echo -e "${YELLOW}waiting ${WAIT_TIME} seconds for lambda processing...${NC}"
sleep $WAIT_TIME

# step 3: check metadata-extractor output in S3
echo ""
echo "step 3: checking metadata-extractor S3 output..."

# check metadata JSON for valid image
echo -n "  processed/metadata/img-${RUN_ID}.json exists... "
if aws s3 ls "s3://${BUCKET_NAME}/processed/metadata/img-${RUN_ID}.json" --region $AWS_REGION 2>/dev/null | grep -q "img-${RUN_ID}.json"; then
    echo -e "${GREEN}pass${NC}"

    # download and show the metadata
    METADATA=$(aws s3 cp "s3://${BUCKET_NAME}/processed/metadata/img-${RUN_ID}.json" - --region $AWS_REGION 2>/dev/null)
    echo "    metadata content:"
    echo "$METADATA" | sed 's/^/    /'
    ((SUCCESS_COUNT++))
else
    echo -e "${RED}fail${NC}"
    ((FAIL_COUNT++))
fi

# check metadata JSON for invalid file (metadata-extractor processes all files)
echo -n "  processed/metadata/doc-${RUN_ID}.json exists... "
if aws s3 ls "s3://${BUCKET_NAME}/processed/metadata/doc-${RUN_ID}.json" --region $AWS_REGION 2>/dev/null | grep -q "doc-${RUN_ID}.json"; then
    echo -e "${GREEN}pass${NC}"
    ((SUCCESS_COUNT++))
else
    echo -e "${RED}fail${NC}"
    ((FAIL_COUNT++))
fi

# step 4: check image-validator output in S3
echo ""
echo "step 4: checking image-validator S3 output..."

# valid image should be copied to processed/valid/
echo -n "  processed/valid/img-${RUN_ID}.jpg exists... "
if aws s3 ls "s3://${BUCKET_NAME}/processed/valid/img-${RUN_ID}.jpg" --region $AWS_REGION 2>/dev/null | grep -q "img-${RUN_ID}.jpg"; then
    echo -e "${GREEN}pass${NC}"
    ((SUCCESS_COUNT++))
else
    echo -e "${RED}fail${NC}"
    ((FAIL_COUNT++))
fi

# invalid file should NOT be in processed/valid/
echo -n "  processed/valid/doc-${RUN_ID}.txt does NOT exist (expected)... "
if aws s3 ls "s3://${BUCKET_NAME}/processed/valid/doc-${RUN_ID}.txt" --region $AWS_REGION 2>/dev/null | grep -q "doc-${RUN_ID}.txt"; then
    echo -e "${RED}fail${NC} (invalid file was copied - it should not be)"
    ((FAIL_COUNT++))
else
    echo -e "${GREEN}pass${NC}"
    ((SUCCESS_COUNT++))
fi

# step 5: check DLQ
echo ""
echo "step 5: checking dead letter queue..."
DLQ_URL=$(aws sqs get-queue-url \
  --queue-name image-processing-dlq \
  --region $AWS_REGION \
  --query 'QueueUrl' \
  --output text 2>/dev/null) || true

echo -n "  image-processing-dlq exists and has messages... "
if [ -n "$DLQ_URL" ] && [ "$DLQ_URL" != "None" ]; then
    DLQ_MSG_COUNT=$(aws sqs get-queue-attributes \
      --queue-url "$DLQ_URL" \
      --attribute-names ApproximateNumberOfMessages \
      --region $AWS_REGION \
      --query 'Attributes.ApproximateNumberOfMessages' \
      --output text 2>/dev/null) || true

    if [ -n "$DLQ_MSG_COUNT" ] && [ "$DLQ_MSG_COUNT" -gt 0 ] 2>/dev/null; then
        echo -e "${GREEN}pass${NC} ($DLQ_MSG_COUNT message(s))"
        ((SUCCESS_COUNT++))
    else
        echo -e "${RED}fail${NC} (DLQ exists but has 0 messages)"
        ((FAIL_COUNT++))
    fi
else
    echo -e "${RED}fail${NC} (DLQ not found)"
    ((FAIL_COUNT++))
fi

# cleanup temp file
rm -f /tmp/doc-${RUN_ID}.txt

# summary
echo ""
echo "===+++++++++++++++++++++++++++++++++++==="
echo "test summary"
echo "===+++++++++++++++++++++++++++++++++++==="
echo "  - successful: ${SUCCESS_COUNT}/${TOTAL_CHECKS}"
echo "  - failed: ${FAIL_COUNT}/${TOTAL_CHECKS}"
echo "===+++++++++++++++++++++++++++++++++++==="

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}all tests passed${NC}"
    exit 0
else
    echo -e "${RED}some tests failed${NC}"
    exit 1
fi
