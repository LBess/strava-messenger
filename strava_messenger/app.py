import json
from random import randint
import boto3

# ParameterStore variable names
VERIFY_TOKEN_PARAMETER_NAME = "strava_messenger_verification_token"
STRAVA_SUBSCRIPTION_ID_PARAMETER_NAME = "strava_api_subscription_id"
SNS_TOPIC_ARN_PARAMETER_NAME = "strava_messenger_sns_topic_arn"

DYNAMO_TABLE_NAME = "Messages"

# Strava Webhook API constants
OBJECT_TYPE_ACTIVITY = "activity"
ASPECT_TYPE_CREATE = "create"

def handleSubscriptionRequest(queryStringParameters):
    """Respond to the Strava subscription validation request

    Doc: https://developers.strava.com/docs/webhooks/

    Parameters
    ----------
    queryStringParameters: dict, required

    Returns
    ------
    HTTP Body: dict
    """
    print("START handle Strava subscription validation request")

    ssmClient = boto3.client("ssm")
    parameterResponse = ssmClient.get_parameter(Name=VERIFY_TOKEN_PARAMETER_NAME)
    verifyToken = parameterResponse["Parameter"]["Value"]
    if verifyToken != queryStringParameters["hub.verify_token"]:
        raise Exception("Invalid verify_token")

    return {
        "hub.challenge": queryStringParameters["hub.challenge"]
    }


def handleActivityPost(body):
    """Handle Strava activity post
    """
    print("START handle Strava activity post")
    
    ssmClient = boto3.client("ssm")
    parameterResponse = ssmClient.get_parameter(Name=STRAVA_SUBSCRIPTION_ID_PARAMETER_NAME)
    subscriptionId = int(parameterResponse["Parameter"]["Value"])
    if body["subscription_id"] != subscriptionId:
        raise Exception("Invalid subscription_id")
        
    if body["object_type"] != OBJECT_TYPE_ACTIVITY:
        raise Exception(f"object_type does not equal {OBJECT_TYPE_ACTIVITY}")
    
    if body["aspect_type"] != ASPECT_TYPE_CREATE:
        raise Exception(f"aspect_type does not eqaul {ASPECT_TYPE_CREATE}")

    # Query the message table
    print("Querying DynamoDB...")
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(DYNAMO_TABLE_NAME)
    # Choose a random value from the table
    dbResponse = table.get_item(
        Key={
            "ID": str(randint(0, table.item_count - 1))
        }
    )

    # Build the message
    motivationMessage = dbResponse["Item"]["Message"]
    stravaActivityId = body["object_id"]
    snsMessage = f"{motivationMessage}\n\n Strava Activity {stravaActivityId}"

    # Send the message
    print(f"SNS message: {snsMessage}")
    parameterResponse = ssmClient.get_parameter(Name=SNS_TOPIC_ARN_PARAMETER_NAME)
    snsTopicArn = parameterResponse["Parameter"]["Value"]
    snsClient = boto3.client("sns")
    snsClient.publish(TopicArn=snsTopicArn, Message=snsMessage, Subject=f"Strava Activity {stravaActivityId}")

    # TODO: Get the owner_id for myself and remove this print
    ownerId = body["owner_id"]
    print(f"owner_id: {ownerId}")

    return {
        "message": "success"
    }


def handler(event, context):
    """Entry point for the Lambda

    Parameters
    ----------
    event: dict, required
    context: object, required

    Returns
    ------
    API Gateway Lambda Proxy Output Format: dict
    """
    
    errorMessage = ""
    responseBody = {}
    try:
        httpMethod = event["httpMethod"]
        if (httpMethod == "GET"):
            queryStringParameters = event["queryStringParameters"]
            responseBody = handleSubscriptionRequest(queryStringParameters)
        elif (httpMethod == "POST"):
            requestBody = json.loads(event["body"])
            responseBody = handleActivityPost(requestBody)
        else:
            errorMessage = f"Invalid HTTP Method {httpMethod}"
    except Exception as e:
        if (len(e.args) > 0):
            errorMessage = e.args[0]
        else:
            errorMessage = "An unspecified error occurred"

    if errorMessage != "":
        responseBody["error"] = errorMessage
    
    # Since we are returning through the API gateway, we have to include a number
    # of these fields.
    return {
        "isBase64Encoded": False,
        "statusCode": 200,
        "headers": {},
        "multiValueHeaders": {},
        "body": json.dumps(responseBody)
    }
