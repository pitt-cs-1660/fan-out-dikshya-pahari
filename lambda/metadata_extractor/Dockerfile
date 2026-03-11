FROM public.ecr.aws/lambda/python:3.13

# note: boto3 is pre-installed in the lambda base image, so no pip install is needed.
# in a real-world lambda you would typically COPY a requirements.txt and run
# pip install -r requirements.txt here to install additional dependencies.

# copy function code
COPY lambda_function.py ${LAMBDA_TASK_ROOT}/

# set the CMD to your handler
CMD [ "lambda_function.lambda_handler" ]
