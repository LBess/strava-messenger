import json
import boto3

VERIFY_TOKEN_PARAMETER_NAME = "strava_messenger_verification_token"
SNS_TOPIC_ARN = "arn:aws:sns:us-east-1:650994256587:strava-motivation"
SUBSCRIPTION_ID = 222977
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
    print(queryStringParameters)

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
    print(body)
    
    if body["subscription_id"] != SUBSCRIPTION_ID:
        raise Exception("Invalid subscription_id")
        
    if body["object_type"] != OBJECT_TYPE_ACTIVITY:
        return {
            "message": "object_type is not activity"
        }
    
    if body["aspect_type"] != ASPECT_TYPE_CREATE:
        return {
            "message": f"aspect_type is not {ASPECT_TYPE_CREATE}"
        }


    stravaActivityId = body["object_id"]
    snsSubject = f"Strava Activity {stravaActivityId}"
    snsMessage = "I\'m the boss of this gym."

    snsClient = boto3.client("sns")
    snsClient.publish(TopicArn=SNS_TOPIC_ARN, Message=snsMessage, Subject=snsSubject)

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
            "An error occurred"

    if errorMessage != "":
        print(f"Error: {errorMessage}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": errorMessage
            })
        }
    
    return {
        "isBase64Encoded": False,
        "statusCode": 200,
        "headers": {},
        "multiValueHeaders": {},
        "body": json.dumps(responseBody)
    }
