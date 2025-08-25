#!/usr/bin/env python3
"""
Script to generate Matt-GPT responses for each Matt message in the conversation transcript.
Version 2: Uses proper conversational message structure in the prompt.
"""

import pandas as pd
import requests
import json
import os
from typing import List, Dict
import time

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

class MattGPTResponseGeneratorV2:
    def __init__(self):
        self.api_url = "http://127.0.0.1:9005/chat"
        self.bearer_token = os.getenv('MATT_GPT_BEARER_TOKEN')
        self.openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
        
        if not self.bearer_token or not self.openrouter_api_key:
            raise ValueError("Missing required environment variables: MATT_GPT_BEARER_TOKEN and OPENROUTER_API_KEY")
    
    def format_conversation_as_structured_history(self, conversation_history: List[Dict]) -> str:
        """Format conversation history as a structured conversation flow."""
        if not conversation_history:
            return ""
            
        formatted_history = "Previous conversation messages:\n\n"
        for i, msg in enumerate(conversation_history, 1):
            role = "User" if msg['type'] == 'user' else "Assistant"
            participant = msg['participant_name']
            content = msg['content']
            formatted_history += f"Message {i} - {role} ({participant}):\n{content}\n\n"
        return formatted_history
    
    def get_matt_gpt_response(self, conversation_history: List[Dict], current_assistant_message: str) -> str:
        """Get a response from Matt-GPT with structured conversation history."""
        headers = {
            'Authorization': f'Bearer {self.bearer_token}',
            'Content-Type': 'application/json'
        }
        
        # Format conversation history in a more structured way
        history_context = self.format_conversation_as_structured_history(conversation_history)
        
        # Create a prompt that emphasizes the conversational flow
        prompt = f"""You are responding as Matt in an ongoing conversation. Here is the conversation history:

{history_context}

The assistant just said:
"{current_assistant_message}"

Please respond as Matt would, taking into account:
1. The full conversation context above
2. Matt's previous responses in this conversation
3. The natural flow and progression of the discussion
4. Matt's conversational style and personality

Your response should feel like a natural continuation of Matt's participation in this specific conversation."""
        
        payload = {
            'message': prompt,
            'openrouter_api_key': self.openrouter_api_key,
            'other_conversation_context': False
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json().get('response', 'Error: No response generated')
        except requests.exceptions.RequestException as e:
            print(f"Error calling Matt-GPT API: {e}")
            return f"Error: API call failed - {str(e)}"
        except Exception as e:
            print(f"Unexpected error: {e}")
            return f"Error: {str(e)}"
    
    def process_csv(self, input_file: str, output_file: str):
        """Process the CSV file and generate Matt-GPT responses with structured conversation history."""
        print(f"Reading {input_file}...")
        df = pd.read_csv(input_file)
        
        # Add new columns for Matt-GPT responses (v2)
        df['matt_gpt_v2_response_1'] = ''
        df['matt_gpt_v2_response_2'] = ''
        df['matt_gpt_v2_response_3'] = ''
        
        # Sort by message_id to ensure chronological order
        df = df.sort_values('message_id').reset_index(drop=True)
        
        # Find all Matt "user" messages (the real Matt responses we want to generate alternatives for)
        matt_user_messages = df[(df['type'] == 'user') & (df['participant_name'] == 'Matt')].copy()
        
        print(f"Found {len(matt_user_messages)} Matt user messages to process...")
        
        total_matt_messages = len(matt_user_messages)
        for idx, matt_message in matt_user_messages.iterrows():
            message_id = matt_message['message_id']
            current_position = list(matt_user_messages.index).index(idx) + 1
            print(f"Processing message {message_id} ({current_position}/{total_matt_messages})...")
            print(f"  Original Matt response: {matt_message['content'][:100]}...")
            
            # Get all conversation history up to (but not including) this Matt message
            conversation_history = df[df['message_id'] < message_id].copy()
            
            # Get the assistant message that this Matt message is responding to
            previous_assistant_msg = conversation_history[conversation_history['type'] == 'assistant'].iloc[-1] if len(conversation_history[conversation_history['type'] == 'assistant']) > 0 else None
            
            if previous_assistant_msg is not None:
                print(f"  Responding to: {previous_assistant_msg['content'][:100]}...")
                
                # Convert to list of dicts for structured formatting
                history_records = conversation_history.to_dict('records')
                assistant_prompt = previous_assistant_msg['content']
                
                # Generate 3 Matt-GPT responses
                for i in range(1, 4):
                    print(f"  Generating v2 response {i}/3...")
                    start_time = time.time()
                    response = self.get_matt_gpt_response(history_records, assistant_prompt)
                    elapsed = time.time() - start_time
                    print(f"    V2 Response {i} generated in {elapsed:.1f}s: {response[:100]}...")
                    
                    # Update the dataframe
                    df.loc[df['message_id'] == message_id, f'matt_gpt_v2_response_{i}'] = response
                    
                    # Small delay to avoid overwhelming the API
                    time.sleep(1)
                print(f"  Completed message {message_id}\n")
            else:
                print(f"  Skipping message {message_id} - no previous assistant message found")
        
        # Save the enhanced CSV
        print(f"Saving results to {output_file}...")
        df.to_csv(output_file, index=False)
        print("Done!")

def main():
    generator = MattGPTResponseGeneratorV2()
    
    # Use the existing file as input and add v2 columns
    input_file = "example_conversations/decision_mate_transcript_data_with_mattgpt.csv"
    output_file = "example_conversations/decision_mate_transcript_data_with_mattgpt_v2.csv"
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file {input_file} not found!")
        return
    
    generator.process_csv(input_file, output_file)

if __name__ == "__main__":
    main()