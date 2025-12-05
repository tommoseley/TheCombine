Epic ID: LLM-300
Epic Title: Pluggable LLMProvider Abstraction

Instructions:
Create a new Epic with the following requirements:

Epic Summary

Introduce a LLMProvider abstraction so The Combine can dynamically route worker calls to different LLM backends—OpenAI, Anthropic, Azure OpenAI, AWS Bedrock, or customer-hosted private models—based on tenant/project configuration.

Business Rationale

Enterprises may require that LLMs run inside their perimeter

Keys and credentials must remain under customer control

Ensures long-term neutrality across model vendors

Enables on-prem and hybrid installations without code changes

Required Stories

Define the LLMProvider interface (supports tools, streaming, token limits)

Implement OpenAIProvider

Implement AnthropicProvider

Implement support for Azure OpenAI + custom endpoints

Add tenant/project-level LLM routing configuration

Update orchestrator to use LLMProvider for all worker calls

Add logging, metrics, and error-handling for provider selection

Deliverable

Full Epic document with stories, story points, and acceptance criteria.