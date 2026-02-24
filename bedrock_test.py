import boto3
import json

REGION = "ap-southeast-2"

client = boto3.client(
    "bedrock-runtime",
    region_name=REGION
)

response = client.invoke_model(
    modelId="amazon.nova-lite-v1:0",
    body=json.dumps({
        "messages": [
            {
                "role": "user",
                "content": [{"text": "Say: Bedrock is working"}]
            }
        ],
        "inferenceConfig": {
            "maxTokens": 50
        }
    })
)

result = json.loads(response["body"].read())
print(result)