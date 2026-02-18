**Fine-Tuning Loop (Roadmap Item 13)**  
**Goal:** Establish a fully automated, human-in-the-loop fine-tuning pipeline that continuously improves the accuracy, domain specificity, and reliability of your local LLM (used primarily by the Natural Language Parser in Item 6, but also by the compliance engine, generator, and visualization components). The loop collects real user interactions, corrections, and high-quality outputs; curates them into structured training datasets; performs efficient LoRA/QLoRA fine-tuning on consumer-grade hardware; evaluates the new model against AEC-specific benchmarks; and deploys the improved model with full version control and rollback capability. This turns the system from a static LLM into an evolving, company- and user-specific “design intelligence” that learns your preferences, Louisiana regional practices, and project-specific conventions over time.

**Core Architecture**  
- **Data Collection:** Automatic logging of every parse request + accepted/corrected structured output.  
- **Dataset:** Alpaca-style JSONL format stored in `fine_tuning/datasets/`.  
- **Training:** LoRA via Axolotl or Unsloth (2026 state-of-the-art for local efficiency).  
- **Evaluation:** Automated test suite of 200+ held-out AEC prompts.  
- **Deployment:** Ollama model registry with semantic versioning and git-tracked Modelfiles.  
- **Integration:** Hooks into `aecos.nlp.parser` and CLI commands.

**Recommended Technology Stack (February 2026)**  
- Ollama (latest) + `ollama create` for base serving  
- Axolotl or Unsloth for LoRA training (GPU-efficient)  
- Hugging Face `datasets` and `peft` libraries  
- FAISS for retrieval-augmented evaluation  
- Git LFS for storing model checkpoints (if >100 MB)

**Prerequisites (1 hour)**  
- Completion of Roadmap Items 1–12.  
- `aecos` package installed in editable mode.  
- GPU with ≥16 GB VRAM recommended (RTX 4090 or equivalent; works on 8 GB with QLoRA).  
- `pip install axolotl unsloth[colab-new] datasets peft accelerate` (or latest equivalents).  
- Base model already running in Ollama (e.g., `llama3.3:70b` or your current fine-tuned variant).

**Phase 1: Feedback Collection System (Day 1)**  
Extend `aecos/nlp/parser.py`:  
```python
def parse(self, user_prompt: str) -> ElementMetadata:
    result = self.graph.invoke(...)
    # Auto-log
    log_interaction(
        prompt=user_prompt,
        raw_output=result,
        accepted=True,          # default; user can later mark as corrected
        correction=None
    )
    return result
```
Create `aecos/finetune/collector.py` with CLI command `aecos feedback correct "wall prompt" --fixed-json {...}` to capture manual corrections.

**Phase 2: Dataset Curation Pipeline (Day 1–2)**  
```python
def build_dataset(raw_logs: list) -> Dataset:
    examples = []
    for log in raw_logs:
        examples.append({
            "instruction": log["prompt"],
            "input": log["context"],          # retrieved Markdown
            "output": json.dumps(log["accepted_or_corrected_output"])
        })
    return Dataset.from_list(examples)
```
Filter for quality: minimum confidence ≥ 0.85, length limits, and manual approval queue (optional).

**Phase 3: Training Configuration & LoRA Setup (Day 2)**  
Create `fine_tuning/config.yaml` for Axolotl:  
```yaml
base_model: llama3.3:70b
model_type: llama
lora_r: 64
lora_alpha: 16
lora_dropout: 0.05
learning_rate: 2e-5
num_epochs: 3
batch_size: 2          # adjust to your GPU
dataset: datasets/latest.jsonl
output_dir: models/finetuned-v2026-02-17
```
Support QLoRA for 8 GB GPUs.

**Phase 4: Automated Training Pipeline (Day 3)**  
Script `aecos/finetune/train.py`:  
```python
def run_finetune(dataset_path: Path, output_name: str):
    # Launch Axolotl or Unsloth training
    # After training, convert to GGUF and import to Ollama
    subprocess.run(["ollama", "create", output_name, "-f", "Modelfile"])
```
GitHub Action or local cron: nightly training on accumulated data (>50 new examples).

**Phase 5: Model Evaluation & Selection (Day 3–4)**  
Automated benchmark suite:  
- 200 golden prompts covering walls, doors, MEP, seismic, Title 24, etc.  
- Metrics: exact JSON match, parameter accuracy, compliance pass rate, hallucination rate.  
- Compare new model vs current; auto-promote if improvement ≥ 5 %.

**Phase 6: Model Deployment & Rollback (Day 4)**  
- Store models in `models/` with git tags (`finetuned-v2026-02-17`).  
- CLI: `aecos model switch finetuned-v2026-02-17` (updates Ollama alias).  
- Rollback: `aecos model rollback` restores previous Modelfile.

**Phase 7: Monitoring & Continuous Improvement (Day 5)**  
- Dashboard (Streamlit): training history, accuracy trend, dataset size.  
- Feedback loop: low-confidence parses automatically flagged for review.  
- Annual full retrain on entire history (optional).

**Total Time to Working Version 1:** 5–7 days  
**Milestone Verification:** After collecting 50 real interactions and running one training cycle, the command `aecos parse "150 mm concrete wall fire-rated two hours California seismic D"` returns a result with measurably higher accuracy (≥ 8 % improvement on your test set) when compared to the base model. The new model is automatically registered in Ollama and used by the parser going forward.

This fine-tuning loop is the mechanism that makes your AEC OS truly personal and increasingly intelligent—turning every project into training data that accelerates future work.

Implement Phases 1–3 today on a small set of 10–20 logged interactions. Paste one sample logged interaction (prompt + accepted output) here if you would like me to generate the exact JSONL format or Axolotl config tweaks.
