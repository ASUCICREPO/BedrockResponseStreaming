import json
import boto3
import os

def lambda_handler(event, context):
        
    #get the inputs from the previous lambda
    prompt = event["prompt"]
    connectionId = event["connectionId"]

    
    #create the model client to call, the RAG agent, and gateway connection for response
    apiGatewayURL = "https" + os.environ['WEBSOCKET_URL'][3:] + "/dev"    #https URL for the api gateway websocket
    gateway = boto3.client("apigatewaymanagementapi", endpoint_url=apiGatewayURL)
    bedrock = boto3.client(service_name="bedrock-runtime", region_name="us-west-2")

    prompt_template = """

    Your Persona:
    You are an intelligent and personable AI made by ASU Cloud Innovation Center (CIC), designed to answer questions about the Response Streaming Feature in Amazon Bedrock.
    
    Your goal is to answer the user's query as accurately, and understandably as possible. Using only the source materials provided, not your own knowledge.

    Your Rules:
    1) You must answer the user's query as accurately as possible using the source, so far as they are relevant to the query.
    2) You must respond to topics not relevant to the CIC and Response Streaming (or dangerous/offensive topics) in the pattern described in XML below.
    3) Stay in character, you were created by the CIC and your knowledge is limited to Response Streaming and not beyond it.

    The Source is incuded below, you may use it to answer the user's query.

    <Source>
    Bedrock Streaming Response

    What it does

        The Response Streaming setup for bedrock is the same pipeline as the standard Bedrock invocation process, with one major difference. Rather than returning the full text in a single request, it returns each token as they’re outputted. This allows for quicker response times, and more interesting frontend UIs.

        The specific demo uses a React hosted frontend utilizing the Chatbot Template (https://github.com/ASUCICREPO/ChatbotTemplate), this invokes the backend through an Api Gateway Websocket, rather than the standard REST api gateway. Through this the request is routed to a lambda function, the “connection opener” lambda. The purpose of this lambda is to allow the initial opening of the websocket connection, and to call the main function. (TODO: I believe this can be done with step functions to simplify to one lambda) Next the main lambda function will call bedrock through the converse stream API, for each token returned, it will be sent back to the api gateway to the frontend.

    How we can use it at the CIC

    The main way that we can use it at the CIC is to improve the Time to First Token. For most LLM pipelines the process looks like: 


    Request->Processing->Generation->Response in Full

    By streaming the response we can fully get rid of  the Generation step, since the first response is received as soon as the first token is generated. 

        Request->Processing->Response of First Token

    This is especially useful for projects that require more complex thought (Longer responses). The longer the average response length, the more time implementing streaming can save. This saved time can be used to do additional pre-processing (RAG, more complex thought time, etc), or use a slower but more intelligent model, such as Haiku -> Sonnet/Opus. The other major use for streaming the response is to create more interesting frontend UI’s, since you receive each token, you can create a cursor effect that shows the output as its generated, boosting the appeal of the design.

    In summary, it is best used for projects with complex thinking processes, and long responses to decrease the time to the first token, and for better looking UIs.

    </Source>


    The user's Question is attached directly below:


    """

    prompt_template += prompt

    
    #Create the prompt API call to bedrock, includes: Model, content type, how the call is formatted, and the model specific info (tokens, prompt, etc)
    kwargs = {
        "modelId": "anthropic.claude-3-sonnet-20240229-v1:0",
        "contentType": "application/json",
        "accept": "application/json",
        "body": json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [
            {
                "role": "user",
                "content": [
                {
                    "type": "text",
                    "text": prompt_template
                }
                ]
            }
            ],
            "temperature": 0.35,
        })
    }

    #Call the model with a response stream (creates an iterable object when converted)
    response = bedrock.invoke_model_with_response_stream(**kwargs)
    

    #Convert the model specific API response into general packet with start/stop info, here converts from Claude API response (Could be done for any model)
    stream = response.get('body')
    if stream:

        #for each returned token from the model:
        for token in stream:

            #The "chunk" contains the model-specific response
            chunk = token.get('chunk')
            if chunk:
                
                #Decode the LLm response body from bytes
                chunk_text = json.loads(chunk['bytes'].decode('utf-8'))
                
                #Construct the response body based on the LLM response, (Where the generated text starts/stops)
                if chunk_text['type'] == "content_block_start":
                    block_type = "start"
                    message_text = ""
                    
                elif chunk_text['type'] == "content_block_delta":
                    block_type = "delta"
                    message_text = chunk_text['delta']['text']    
                    
                elif chunk_text['type'] == "content_block_stop":
                    block_type = "end"
                    message_text = ""

                else:
                    block_type = "blank"
                    message_text = ""

                
                #Send the response body back through the gateway to the client    
                data = {
                    'statusCode': 200,
                    'type': block_type,
                    'text': message_text,
                }
                gateway.post_to_connection(ConnectionId=connectionId, Data=json.dumps(data))
                
    return {
        'statusCode': 200
    }
    