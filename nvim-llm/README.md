# nvim-llm

Disclaimer: LLM-assisted/vibe-coded. Using Qwen 3.8 for conversations and coding via browser interface.

Determine if nvim buffers can serve as interface for llm conversations.

## Dependencies
- bash
- nvim/lua
- API keys for OpenRouter

## Usage
conv.sh is a bash file. Grant execution permission and run from command line.

```bash
chmod +x conv.sh
./conv.sh
```

conv.lua can be placed in ~/.config/nvim/after/ftplugin/conv.lua or open and source with luafile.

```lua
--- Inside nvim
luafile <path/to/lua/file>/conv.lua
```

## Getting API keys
OpenRouter (recommended for v0.1-OpenAI-compatible, free models available):
1. Go to https://openrouter.ai
2. Sign in (GitHub/Google)
3. Go to https://openrouter.ai/keys -> "Create Key"
4. Copy the key. It looks like sk-or-v1-...
5. Free models (look at their list to try newer ones if you want): meta-llama/llama-3.1-8b-instruct:free, google/gemma-2-9b-it:free, mistralai/mistral-7b-instruct:free
6. Export the keys.
```bash
# OpenRouter
export LLM_API_URL="https://openrouter.ai/api/v1/chat/completions"
export LLM_API_KEY="sk-or-v1-YOUR_KEY_HERE"
export LLM_MODEL="meta-llama/llama-3.1-8b-instruct:free"
```

## References
- https://chat.qwen.ai/c/22cd7425-0d0f-4d99-a8be-db35f2b7c3dd
