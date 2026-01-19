# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OWL (Optimized Workforce Learning) is a hierarchical multi-agent framework for real-world task automation. It achieves state-of-the-art 69.70% accuracy on the GAIA benchmark using a Planner → Coordinator → Workers architecture that decouples planning from execution.

Based on a modified CAMEL 0.2.46 framework.

## Commands

### Setup
```bash
conda create -n owl python=3.11
pip install -r requirements.txt
cp .env_example .env  # Fill in API keys
```

### Running Inference
```bash
# Claude-3.7 based (69.70% accuracy)
python run_gaia_workforce_claude.py

# GPT-4o based (60.61% accuracy)
python run_gaia_workforce.py

# vLLM planner variant
python run_gaia_workforce_vllm_planner.py
```

### Configuration (in run scripts)
- `LEVEL`: Task difficulty (1, 2, or 3)
- `on`: Dataset split ("valid" or "test")
- `test_idx`: List of task indices to evaluate (e.g., `[0, 1, 2]`)
- `MAX_TRIES`: Number of retry attempts per task
- `max_replanning_tries`: Replanning attempts on failure

### Results
- Output: `results/workforce/workforce_{LEVEL}_pass{MAX_TRIES}_*.json`
- Cache: `tmp/` (auto-cleaned at startup)

## Architecture

### Core Components

**Workforce Hierarchy** (`camel/societies/workforce/`):
- **Planner**: Decomposes complex tasks into subtasks
- **Coordinator**: Assigns subtasks to specialized workers
- **Workers**: Execute tasks using available toolkits

**OWL Extensions** (`utils/`):
- `OwlGaiaWorkforce`: GAIA-specific workforce with replanning logic
- `OwlWorkforceChatAgent`: ChatAgent with retry decorator and tool handling
- `GAIABenchmark`: Benchmark integration with scoring

### Agent Types (defined in `construct_agent_list()`)
1. **Web Agent**: Search, browser simulation, webpage extraction (GPT-4o)
2. **Document Processing Agent**: PDF, images, audio, video (Claude-3.7)
3. **Reasoning/Coding Agent**: Code execution, Excel processing (Claude-3.7)

### Toolkits (`camel/toolkits/`)
Key toolkits: `SearchToolkit`, `AsyncBrowserToolkit`, `DocumentProcessingToolkit`, `CodeExecutionToolkit`, `ImageAnalysisToolkit`, `AudioAnalysisToolkit`, `VideoAnalysisToolkit`, `ExcelToolkit`

### Task Flow
1. Task decomposition by Planner using structured prompts
2. Coordinator assigns subtasks to appropriate workers
3. Workers execute with tools, returning results
4. On failure: replanning triggered with failure context
5. Verification subtask validates final answer

## Key Files

- `run_gaia_workforce_claude.py`: Main entry point, defines agent configurations
- `utils/enhanced_workforce.py`: `OwlGaiaWorkforce` with prompts and replanning
- `utils/gaia.py`: `GAIABenchmark` class for evaluation
- `camel/societies/workforce/workforce.py`: Core Workforce orchestration
- `camel/agents/chat_agent.py`: Base ChatAgent implementation

## Environment Variables

Required:
- `OPENAI_API_KEY`: For GPT-4o and O3-mini
- `ANTHROPIC_API_KEY`: For Claude-3.7-sonnet
- `GOOGLE_API_KEY` + `SEARCH_ENGINE_ID`: For web search

Optional:
- `FIRECRAWL_API_KEY`: Enhanced web scraping
- `CHUNKR_API_KEY`: Document chunking
- `HF_TOKEN`: Hugging Face access
