from aws_cdk import (
    Duration,
    Stack,
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_integrations as apigwv2_i,
    aws_lambda as _lambda,
    aws_iam as iam,
    CfnOutput,
)
from constructs import Construct

class BedrockResponseStreamingCicStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)


        ######################################################################################################################################
        #api gateway

        web_socket_api = apigwv2.WebSocketApi(self, "web_socket_api",)
        apigwv2.WebSocketStage(
            self, 
            "stage",
            web_socket_api=web_socket_api,
            stage_name="dev",
            auto_deploy=True
        )

        ######################################################################################################################################
        #lambdas

        bedrock_orchestration = _lambda.Function(
            self,
            "bedrock-orchestration-lambda",
            runtime = _lambda.Runtime.PYTHON_3_12 ,
            code = _lambda.Code.from_asset("./lambdas"),
            handler = "bedrock_orchestration.lambda_handler", # Points to the 'bedrock_orchestration' file in the lambda directory
            timeout = Duration.minutes(15),
            environment={
                "WEBSOCKET_URL": web_socket_api.api_endpoint
            }
        )

        bedrock_orchestration.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonBedrockFullAccess")
        )
        bedrock_orchestration.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonAPIGatewayInvokeFullAccess")
        )


        websocket_opener = _lambda.Function(
            self,
            "websocket-opener-lambda",
            runtime = _lambda.Runtime.PYTHON_3_12 ,
            code = _lambda.Code.from_asset("./lambdas"),
            handler = "websocket_opener.lambda_handler", # Points to the 'websocket_opener' file in the lambda directory
            environment={
                "BEDROCK_ORCHESTRATION_ARN": bedrock_orchestration.function_arn
            }
        )
        bedrock_orchestration.grant_invoke(websocket_opener) #give it permission to invoke the second lambda function

        ######################################################################################################################################
        #api gateway integrations

        web_socket_api.add_route(
            "sendMessage",
            integration = apigwv2_i.WebSocketLambdaIntegration("websocket-opener", websocket_opener),
            return_response=True
        )

        CfnOutput(self, "websocket-url",
            value = web_socket_api.api_endpoint,
        )

