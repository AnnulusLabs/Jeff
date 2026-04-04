"""
JEFF MODEL DIET — The Complete Guide to Running Frontier Models on Consumer Hardware
Consolidated from months of research across RTX 3090 (24GB) + MI60 (32GB) + 64GB DDR5

"If it doesn't fit, make it fit. If it fits, make it faster."

AnnulusLabs LLC · April 2026
"""

# ═══════════════════════════════════════════════════════════════════════
# 1. QUANTIZATION HIERARCHY
# ═══════════════════════════════════════════════════════════════════════
#
# Rule of thumb: ~0.6-0.8 GB per 1B params at Q4
# Full precision: ~2 GB per 1B params
#
# DYNAMIC QUANTIZATION (Unsloth method — state of the art)
#   - Critical layers (first 3 dense, down_proj, attention) stay at 4-6 bit
#   - Bulk MoE experts crushed to 1.58-bit
#   - DeepSeek R1 671B: 1.4TB → 131GB and still functional
#   - Key: naive uniform quantization breaks models. Dynamic doesn't.
#
# EXL2 FORMAT (ExLlamaV2)
#   - Mixed bitrate within model: 2-8 bits per weight
#   - 56 tok/s on T4 GPU — fastest quantized inference
#   - Best for pure GPU speed, single card
#
# GGUF (llama.cpp)
#   - Q4_K_M: best quality/size tradeoff for most models
#   - Q3_K_M: aggressive, some quality loss, big VRAM savings
#   - IQ2/IQ1: extreme compression, quality degrades noticeably
#   - Universal compatibility, CPU+GPU hybrid
#
# JANG FORMAT (MLX — Apple Silicon only)
#   - Only working quant format for MiniMax on MLX
#   - Standard MLX uniform quant is BROKEN on MiniMax (~25% = random)
#   - dealignai CRACK abliterated versions use this

QUANT_PROFILES = {
    "quality_first": {
        "format": "GGUF",
        "level": "Q6_K",
        "gb_per_1b": 0.9,
        "quality_loss": "minimal",
        "note": "When accuracy matters more than fitting",
    },
    "balanced": {
        "format": "GGUF",
        "level": "Q4_K_M",
        "gb_per_1b": 0.7,
        "quality_loss": "slight",
        "note": "Default for most use cases",
    },
    "aggressive": {
        "format": "GGUF",
        "level": "Q3_K_M",
        "gb_per_1b": 0.5,
        "quality_loss": "moderate",
        "note": "When VRAM is tight but you need the model",
    },
    "extreme": {
        "format": "GGUF",
        "level": "IQ2_XXS",
        "gb_per_1b": 0.3,
        "quality_loss": "significant",
        "note": "Last resort. Test output quality before trusting.",
    },
    "unsloth_dynamic": {
        "format": "GGUF",
        "level": "1.58-bit dynamic",
        "gb_per_1b": 0.2,
        "quality_loss": "targeted — critical layers preserved",
        "note": "Only for supported models. Best extreme compression.",
    },
    "speed_king": {
        "format": "EXL2",
        "level": "4-bit mixed",
        "gb_per_1b": 0.7,
        "quality_loss": "slight",
        "note": "Fastest inference. GPU only. ExLlamaV2 required.",
    },
}

# ═══════════════════════════════════════════════════════════════════════
# 2. MoE LAYER SPLITTING — The Big Trick for 230B+ Models
# ═══════════════════════════════════════════════════════════════════════
#
# MoE models (MiniMax, DeepSeek, Qwen MoE) only activate 8-10B of 230B+
# The trick: dense layers on GPU, expert layers on CPU RAM
#
# llama.cpp:
#   llama-server -m model.gguf --n-cpu-moe 15
#   # Offloads 15 expert layers to CPU, keeps dense on GPU
#
# The --fit on flag (llama.cpp):
#   Automatically splits MoE experts to CPU, dense to GPU
#   15% CPU during prompt, 25-45% during generation
#   That's the tax — worth paying for 230B on 24GB
#
# Practical: Qwen3-Coder-Next 80B (3B active) ran on 16GB VRAM + 30GB RAM
#   Command: -np 1 -t 8 --fit on -fa 1
#   MoE experts on CPU, dense on GPU, flash attention for KV

MOE_OFFLOAD_CONFIGS = {
    "minimax_m2_on_3090": {
        "model_params": "230B total / 10B active",
        "quant": "Q4_K_M",
        "weights_gb": 18,  # active params
        "gpu_layers": "dense attention + routing",
        "cpu_layers": "MoE experts (248 of 256)",
        "vram_required": 20,  # GB
        "ram_required": 48,   # GB
        "expected_speed": "8-15 tok/s",
        "cmd": "llama-server -m minimax-m2.gguf -ngl 99 --n-cpu-moe 248 -fa 1 -c 32768",
    },
    "deepseek_r1_dynamic": {
        "model_params": "671B total",
        "quant": "1.58-bit Unsloth dynamic",
        "weights_gb": 131,
        "gpu_layers": "critical dense layers",
        "cpu_layers": "bulk experts",
        "vram_required": 24,
        "ram_required": 131,
        "expected_speed": "2-5 tok/s on CPU, 10+ with GPU offload",
        "note": "Outperforms GPT-4.1 in no-thinking mode at this quant",
    },
}

# ═══════════════════════════════════════════════════════════════════════
# 3. KV CACHE OPTIMIZATION — Where VRAM Actually Goes
# ═══════════════════════════════════════════════════════════════════════
#
# VRAM grows LINEAR with context length, not model size.
# A 7B model at 128K context can eat more VRAM than a 70B at 4K.
#
# Ollama KV cache quantization:
#   OLLAMA_KV_CACHE_TYPE=q8_0   # halves KV cache memory (recommended)
#   OLLAMA_KV_CACHE_TYPE=q4_0   # reduces to 1/3 (aggressive)
#   Requires flash attention enabled
#
# SnapKV (2024):
#   Selects only "important" past token positions per attention head
#   3.6x faster generation, 8.2x lower memory on 16K inputs
#   380K context on single 80GB GPU with minor quality loss
#
# RetrievalAttention (2024):
#   Offloads past KV to CPU, uses ANN search for relevant ones
#   Accesses only 1-3% of cached data
#   128K context on single 24GB GPU
#
# Rule: measure VRAM at two context lengths, extrapolate to find your max

KV_CACHE_SETTINGS = {
    "conservative": {
        "type": "q8_0",
        "savings": "50%",
        "quality": "negligible loss",
        "requires": "flash attention",
    },
    "aggressive": {
        "type": "q4_0",
        "savings": "67%",
        "quality": "slight loss on long contexts",
        "requires": "flash attention",
    },
}

# ═══════════════════════════════════════════════════════════════════════
# 4. MULTI-GPU SPLITTING — 3090 + MI60 Together
# ═══════════════════════════════════════════════════════════════════════
#
# llama.cpp tensor split (layer-based, NOT tensor parallel):
#   llama-server -m model.gguf \
#     --tensor-split 1,1.3 \     # Ratio: 24GB:32GB
#     --split-mode layer \        # Split by layers
#     --main-gpu 0                # KV cache on 3090 (faster bus)
#
# WARNING: llama.cpp does NOT do tensor parallelism. It's layer offloading.
# For true parallel: vLLM or ExLlamaV2
#
# Practical 56GB combined fits:
#   - 70B models at Q4: ~35GB weights + KV headroom ✓
#   - 32B models at Q6: ~29GB with room to breathe ✓
#   - 230B MoE at Q4: dense on GPUs, experts on CPU ✓

MULTI_GPU_CONFIGS = {
    "3090_mi60_balanced": {
        "cmd": "--tensor-split 1,1.3 --split-mode layer --main-gpu 0",
        "note": "MI60 gets more layers (more VRAM). KV cache on 3090 (faster PCIe).",
    },
}

# ═══════════════════════════════════════════════════════════════════════
# 5. SPECULATIVE DECODING — Draft Small, Verify Big
# ═══════════════════════════════════════════════════════════════════════
#
# Use a tiny model (1-3B) to draft tokens, big model verifies in batch
# 2-3x speedup because verification is cheaper than generation
#
# Llama 70B + Llama 1B drafter: 2.31x speedup
# Draft model must be 10-50x smaller than target
# Speedup increases with target model size
#
# llama.cpp:
#   llama-server -m big.gguf --model-draft small.gguf \
#     --draft-max 8 --draft-min 1

SPECULATIVE_PAIRS = {
    "deepseek_r1": {"target": "deepseek-r1:32b", "draft": "deepseek-r1:1.5b", "speedup": "2x"},
    "qwen3_coder": {"target": "qwen3-coder:30b", "draft": "qwen3:0.6b", "speedup": "1.8x"},
    "hermes3": {"target": "hermes3:8b", "draft": "hermes3:1b", "speedup": "1.5x"},
}

# ═══════════════════════════════════════════════════════════════════════
# 6. CPU OPTIMIZATION — Don't Leave Performance on the Table
# ═══════════════════════════════════════════════════════════════════════
#
# Default llama.cpp often ships WITHOUT BLAS or native CPU optimizations
# Enabling blasSupport + GGML_NATIVE: 8 tok/s → 50 tok/s
#
# Build flags:
#   cmake -DGGML_NATIVE=ON -DGGML_BLAS=ON ..
#
# Your 9950X3D with 128MB 3D V-Cache is a MONSTER for CPU inference
# The V-Cache means massive KV cache hits during attention computation
#
# Thread settings matter:
#   -t 8 for generation (half your cores — avoid memory bandwidth saturation)
#   -t 16 for prompt processing (use all cores)
#   -tb 16 for batch threads

CPU_SETTINGS = {
    "9950x3d": {
        "gen_threads": 8,
        "prompt_threads": 16,
        "batch_threads": 16,
        "build_flags": "-DGGML_NATIVE=ON -DGGML_BLAS=ON",
        "advantage": "128MB V-Cache = massive KV cache hit rate",
    },
}

# ═══════════════════════════════════════════════════════════════════════
# 7. FINE-TUNING ON CONSUMER HARDWARE — LoRA/QLoRA
# ═══════════════════════════════════════════════════════════════════════
#
# QLoRA on 3090: up to 13B full quality, 32B with aggressive settings
#
# Optimal LoRA config for quality:
#   target_modules = ["q_proj", "k_proj", "v_proj", "o_proj",
#                     "gate_proj", "up_proj", "down_proj"]
#   r=64, alpha=128
#   gradient_checkpointing=True
#   bf16=True
#
# Speed tricks:
#   packing=True in SFTConfig: 1.5-2x throughput
#   attn_implementation="sdpa" if flash attention unstable
#   Unsloth: 2-3x speedup on Ampere GPUs
#
# For abliterating models yourself:
#   remove-refusals-with-transformers (Arditi et al. 2024)
#   PRISM: projected refusal isolation via subspace modification
#   Target the refusal direction in residual stream, subtract it

LORA_CONFIGS = {
    "quality": {
        "r": 64, "alpha": 128,
        "targets": "all attention + MLP",
        "vram": "~22GB on 3090",
    },
    "speed": {
        "r": 16, "alpha": 32,
        "targets": "q_proj, v_proj only",
        "vram": "~14GB on 3090",
    },
}

# ═══════════════════════════════════════════════════════════════════════
# 8. THE DIET RECIPES — Common Setups
# ═══════════════════════════════════════════════════════════════════════

RECIPES = {
    "jeff_default": {
        "name": "Jeff Daily Driver",
        "model": "hermes3:8b or abliterated equivalent",
        "quant": "Q4_K_M",
        "vram": "~6GB",
        "speed": "40+ tok/s",
        "use": "Fast coding, tool dispatch, quick answers",
        "kv_cache": "q8_0",
    },
    "jeff_reasoning": {
        "name": "Jeff Deep Think",
        "model": "deepseek-r1:32b",
        "quant": "Q4_K_M",
        "vram": "~20GB on 3090",
        "speed": "15-20 tok/s",
        "use": "Complex reasoning, architecture decisions",
        "kv_cache": "q8_0",
        "speculative": "deepseek-r1:1.5b drafter",
    },
    "jeff_frontier": {
        "name": "Jeff Goes Hard",
        "model": "minimax-m2.7 abliterated (when available)",
        "quant": "Q4_K_M with MoE offload",
        "vram": "20GB GPU + 48GB RAM",
        "speed": "8-15 tok/s",
        "use": "Frontier coding, complex multi-file edits",
        "cmd": "llama-server -m model.gguf -ngl 99 --n-cpu-moe 248 -fa 1 -c 32768",
    },
    "jeff_consensus": {
        "name": "Jeff Pit Crew (BranchialAnalyzer)",
        "models": "hermes3:8b + deepseek-r1:14b + qwen3:8b + 2-3 abliterated",
        "method": "Run same prompt through all, score by consensus",
        "vram": "Swap models sequentially, ~6-8GB peak",
        "use": "Critical decisions, code review, adversarial validation",
        "note": "Disagreements ARE the kerf. That's where truth hides.",
    },
    "jeff_training": {
        "name": "Jeff Learns",
        "method": "QLoRA fine-tune on 3090",
        "base": "Any 8-13B model",
        "vram": "~22GB with gradient checkpointing",
        "config": "r=64, alpha=128, all linear targets, packing=True",
        "use": "Custom abliteration, domain specialization",
    },
}

# ═══════════════════════════════════════════════════════════════════════
# 9. THE RULES
# ═══════════════════════════════════════════════════════════════════════
#
# 1. Never uniform quantize MoE models. Use dynamic or per-layer.
# 2. KV cache eats more VRAM than you think. Always quantize it.
# 3. Flash attention is not optional. Enable it everywhere.
# 4. CPU offload without BLAS is 6x slower. Always compile native.
# 5. Speculative decoding is free speed. Use it.
# 6. Your 9950X3D V-Cache is a competitive advantage. Use half
#    threads for generation, full threads for prompt processing.
# 7. The gap between what fits and what doesn't is ONE optimization.
#    Don't give up until you've tried MoE offload + KV quant + spec decode.
# 8. Abliterated models don't just remove refusals — they remove the
#    engagement loop. That's a feature, not a risk.
# 9. Consensus across diverse models beats any single model.
#    Include at least one abliterated model in every pit crew run.
# 10. Test output quality BEFORE trusting aggressive quants.
#     Run your gate on the model's output, not just the code.
