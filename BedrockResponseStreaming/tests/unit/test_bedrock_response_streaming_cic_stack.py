import aws_cdk as core
import aws_cdk.assertions as assertions

from bedrock_response_streaming_cic.bedrock_response_streaming_cic_stack import BedrockResponseStreamingCicStack

# example tests. To run these tests, uncomment this file along with the example
# resource in bedrock_response_streaming_cic/bedrock_response_streaming_cic_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = BedrockResponseStreamingCicStack(app, "bedrock-response-streaming-cic")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
