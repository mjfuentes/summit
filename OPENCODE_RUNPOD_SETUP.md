# OpenCode + RunPod Setup Guide

Simple guide to use OpenCode locally with CodeLlama models hosted on RunPod for massive cost savings.

## Why This Approach?

- **90% Cost Savings**: $2-8/day vs $30-60/day with Claude Code
- **Better Performance**: Local OpenCode with full file system access
- **No Vendor Lock-in**: Use any open source model
- **Simple Setup**: Manual deployment, no complex automation needed

## Step 1: Deploy Model on RunPod (Manual)

### 1.1 Create RunPod Account
- Go to [runpod.io](https://runpod.io)
- Sign up and add payment method
- Get your API key from settings

### 1.2 Deploy CodeLlama Model
1. Go to **Serverless** → **Templates**
2. Search for "codellama" or use this template:
   ```
   runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04
   ```
3. Configure:
   - **Name**: `summit-codellama-13b`
   - **GPU**: RTX 4090 (best price/performance)
   - **Min Workers**: 0 (scales to zero)
   - **Max Workers**: 2
   - **Idle Timeout**: 5 seconds
   - **Container Disk**: 20GB
   - **Volume**: 10GB

### 1.3 Model Handler Code
Create this handler in your RunPod template:

```python
import runpod
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# Load model once at startup
model_name = "codellama/CodeLlama-13b-Instruct-hf"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16,
    device_map="auto"
)

def handler(job):
    """OpenAI-compatible API handler"""
    job_input = job.get("input", {})
    
    messages = job_input.get("messages", [])
    max_tokens = job_input.get("max_tokens", 1000)
    temperature = job_input.get("temperature", 0.7)
    
    # Format for CodeLlama
    prompt = format_codellama_prompt(messages)
    
    # Generate response
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=temperature,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id
        )
    
    response = tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
    
    return {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": response
            }
        }]
    }

def format_codellama_prompt(messages):
    """Format messages for CodeLlama chat format"""
    formatted = ""
    
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        
        if role == "system":
            formatted += f"<s>[INST] <<SYS>>\n{content}\n<</SYS>>\n\n"
        elif role == "user":
            if formatted and not formatted.endswith("[INST] "):
                formatted += f"<s>[INST] {content} [/INST]"
            else:
                formatted += f"{content} [/INST]"
        elif role == "assistant":
            formatted += f" {content} </s>"
    
    # If the last message was from user, we're ready for assistant response
    if not formatted.endswith("[/INST]"):
        formatted += " "
    
    return formatted

runpod.serverless.start({"handler": handler})
```

### 1.4 Get Your Endpoint URL
After deployment, you'll get an endpoint URL like:
```
https://api.runpod.ai/v2/your-endpoint-id/runsync
```

## Step 2: Install OpenCode Locally

```bash
# Install OpenCode
curl -fsSL https://raw.githubusercontent.com/opencode-ai/opencode/main/install | bash

# Verify installation
opencode --version
```

## Step 3: Configure OpenCode for RunPod

### 3.1 Create OpenCode Config
```bash
mkdir -p ~/.config/opencode
```

Create `~/.config/opencode/config.json`:
```json
{
  "defaultAgent": "coder",
  "localEndpoint": "https://api.runpod.ai/v2/your-endpoint-id/runsync",
  "agents": {
    "coder": {
      "model": "codellama/CodeLlama-13b-Instruct-hf",
      "reasoningEffort": "high"
    }
  }
}
```

### 3.2 Set Environment Variable
```bash
# Add to your ~/.bashrc or ~/.zshrc
export RUNPOD_ENDPOINT_URL="https://api.runpod.ai/v2/your-endpoint-id/runsync"
```

## Step 4: Test the Setup

### 4.1 Test OpenCode
```bash
cd /path/to/your/project
opencode "Analyze this codebase and suggest improvements"
```

### 4.2 Test with Summit
```bash
# Set environment variable to use OpenCode
export USE_OPENCODE=true

# Start Summit web interface
python start_web.py
```

## Step 5: Usage Examples

### Basic Development Task
```bash
opencode "Add error handling to the authentication module"
```

### Code Review
```bash
opencode "Review the changes in src/auth.py and suggest improvements"
```

### Bug Fixing
```bash
opencode "Fix the failing tests in tests/test_auth.py"
```

### Feature Implementation
```bash
opencode "Implement JWT token refresh functionality following the existing patterns"
```

## Cost Comparison

| Provider | Model | Cost Structure | Daily Cost (Heavy Use) |
|----------|-------|----------------|------------------------|
| **Claude Code** | Claude 3.5 Sonnet | $0.03/1K tokens | $30-60/day |
| **RunPod + CodeLlama** | CodeLlama 13B | $0.34/hour active | $2-8/day |
| **Savings** | - | - | **80-90% reduction** |

## Troubleshooting

### OpenCode Not Connecting
1. Check your endpoint URL in config
2. Verify RunPod deployment is active
3. Test endpoint directly with curl

### Model Loading Issues
1. Ensure sufficient GPU memory (RTX 4090 = 24GB)
2. Check RunPod logs for errors
3. Try reducing model precision if needed

### Performance Optimization
1. Use RTX 4090 for best price/performance
2. Set idle timeout to 5 seconds for cost efficiency
3. Scale workers based on usage patterns

## Advanced Configuration

### Multiple Models
You can deploy different models for different tasks:
- **CodeLlama 13B**: Best for coding tasks (no gating)
- **CodeLlama 34B**: Higher quality coding (more GPU memory)
- **Mistral 7B**: Lightweight general tasks

### Custom Prompts
Create custom OpenCode commands in `~/.config/opencode/commands/`:

```markdown
# summit-implement.md
# Summit Feature Implementation

Please implement the requested feature following Summit's standards:
- Maintain >70% test coverage
- Follow existing code patterns
- Apply proper formatting (Black, isort)
- Add comprehensive error handling
- Use professional coding standards

Use the available tools to read, write, and test code as needed.
```

## Summary

This setup gives you:
-  **90% cost savings** over Claude Code
-  **Local OpenCode** with full terminal integration
-  **Open source models** with no vendor lock-in
-  **Simple manual deployment** - no complex automation
-  **Scales to zero** when not in use
-  **Full control** over model behavior and costs

Perfect for Summit's autonomous development needs while keeping costs minimal! 