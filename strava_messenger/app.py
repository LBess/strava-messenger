import json
import boto3

VERIFY_TOKEN_PARAMETER_NAME = "strava_messenger_verification_token"

def handleSubscriptionRequest(queryStringParameters):
    """Respond to the Strava subscription validation request

    Doc: https://developers.strava.com/docs/webhooks/
    """
    print("START handle Strava subscription validation request")
    print(queryStringParameters)

    ssmClient = boto3.client("ssm")
    parameterResponse = ssmClient.get_parameter(Name=VERIFY_TOKEN_PARAMETER_NAME)
    verifyToken = parameterResponse["Parameter"]["Value"]
    if (verifyToken != queryStringParameters["hub.verify_token"]):
        raise Exception("Invalid verify_token")

    return {
        "hub.challenge": queryStringParameters["hub.challenge"]
    }


def handleActivityPost(body):
    """Handle Strava activity post
    """
    print("START handle Strava activity post")
    print(body)

    return {
        "message": "yo"
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
            errorMessage = f"Error: Invalid HTTP Method {httpMethod}"
    except Exception as e:
        if (len(e.args) > 0):
            print(e)
            errorMessage = f"Error: {e.args[0]}"
        else:
            "An error occurred"

    if errorMessage != "":
        print(errorMessage)
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": errorMessage
            })
        }
    
    print("SUCCESS")
    return {
        "isBase64Encoded": False,
        "statusCode": 200,
        "headers": {},
        "multiValueHeaders": {},
        "body": json.dumps(responseBody)
    }
