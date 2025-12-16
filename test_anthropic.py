#!/usr/bin/env python3
"""
Simple test harness to verify Anthropic API connection.
Requires: pip install anthropic
"""

import os
import sys
from anthropic import Anthropic
from config import ANTHROPIC_API_KEY

def test_api_connection():
    """Test the Anthropic API connection with a simple query."""
    # Check for API key
    api_key = ANTHROPIC_API_KEY # os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ ERROR: ANTHROPIC_API_KEY environment variable not set")
        assert False
    
    print(f"✓ API key found (starts with: {api_key[:8]}...)")
    
    try:
        # Initialize the client
        client = Anthropic(api_key=api_key)
        print("✓ Anthropic client initialized")
        
        # Make a simple test request
        print("\n🔄 Testing API connection with a simple query...")
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=100,
            messages=[
                {
                    "role": "user",
                    "content": "Reply with exactly: 'API connection successful!'"
                }
            ]
        )
        
        # Extract response
        response_text = message.content[0].text
        print(f"\n📨 Response received:")
        print(f"   {response_text}")
        
        # Display usage info
        print(f"\n📊 Token usage:")
        print(f"   Input tokens:  {message.usage.input_tokens}")
        print(f"   Output tokens: {message.usage.output_tokens}")
        
        print(f"\n✅ SUCCESS: API connection verified!")
        print(f"   Model: {message.model}")
        print(f"   Role: {message.role}")
        
        assert True
        
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}")
        print(f"   {str(e)}")
        assert False

if __name__ == "__main__":
    success = test_api_connection()
    sys.exit(0 if success else 1)