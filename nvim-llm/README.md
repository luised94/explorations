# nvim-llm

Disclaimer: LLM-assisted/vibe-coded. Using Qwen 3.8 for conversations and coding via browser interface.

Determine if nvim buffers can serve as interface for llm conversations.

## Dependencies
- bash
- nvim/lua

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


## References
- https://chat.qwen.ai/c/22cd7425-0d0f-4d99-a8be-db35f2b7c3dd
