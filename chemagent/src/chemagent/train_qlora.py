from __future__ import annotations

import argparse
import json
import os
import platform
import socket
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import ConfigError, load_toml, project_root, resolve_project_path, sha256_file


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Two-GPU QLoRA trainer")
    parser.add_argument("--model-config", type=Path, required=True)
    parser.add_argument("--training-config", type=Path, required=True)
    return parser


def _count_jsonl(path: Path) -> int:
    with path.open(encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def _dtype(torch: Any, name: str) -> Any:
    values = {"bfloat16": torch.bfloat16, "float16": torch.float16, "float32": torch.float32}
    try:
        return values[name]
    except KeyError as exc:
        raise ConfigError(f"Unsupported compute dtype: {name}") from exc


def _write_run_manifest(
    output_dir: Path,
    model_config_path: Path,
    training_config_path: Path,
    model_config: dict[str, Any],
    train_path: Path,
    validation_path: Path,
    versions: dict[str, str],
) -> Path:
    if output_dir.exists():
        raise ConfigError(f"Training output already exists; refusing overwrite: {output_dir}")
    output_dir.mkdir(parents=True)
    dataset_audit = train_path.parent / "audit.json"
    if not dataset_audit.is_file():
        raise ConfigError(f"Curated dataset audit is missing: {dataset_audit}")
    manifest = {
        "schema_version": 1,
        "status": "INITIALIZED",
        "started_at_utc": datetime.now(UTC).isoformat(),
        "command": sys.argv,
        "host": socket.gethostname(),
        "platform": platform.platform(),
        "python": sys.version,
        "model_id": model_config["model"]["id"],
        "model_revision": model_config["model"]["revision"],
        "model_config_sha256": sha256_file(model_config_path),
        "training_config_sha256": sha256_file(training_config_path),
        "train_sha256": sha256_file(train_path),
        "validation_sha256": sha256_file(validation_path),
        "dataset_audit_sha256": sha256_file(dataset_audit),
        "versions": versions,
    }
    manifest_path = output_dir / "run_manifest.json"
    with manifest_path.open("x", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return manifest_path


def _finish_manifest(path: Path, metrics: dict[str, Any]) -> None:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["status"] = "COMPLETE"
    manifest["finished_at_utc"] = datetime.now(UTC).isoformat()
    manifest["metrics"] = metrics
    temporary = path.with_suffix(".json.tmp")
    with temporary.open("x", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temporary, path)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = project_root()
    model_config_path = args.model_config.resolve()
    training_config_path = args.training_config.resolve()
    model_config = load_toml(model_config_path)
    training_config = load_toml(training_config_path)
    model = model_config["model"]
    if model["revision"] == "PIN_BEFORE_TRAINING":
        raise ConfigError("Pin model.revision to an immutable commit SHA before training")

    data = training_config["data"]
    train_path = resolve_project_path(data["train_file"], root)
    validation_path = resolve_project_path(data["validation_file"], root)
    if not train_path.is_file() or not validation_path.is_file():
        raise ConfigError("Curated train and validation JSONL files are required")
    train_count = _count_jsonl(train_path)
    validation_count = _count_jsonl(validation_path)
    gate = training_config["pilot_gate"]
    if not gate["minimum_train_records"] <= train_count <= gate["maximum_train_records"]:
        raise ConfigError(
            f"Pilot train count {train_count} is outside "
            f"[{gate['minimum_train_records']}, {gate['maximum_train_records']}]"
        )
    if validation_count == 0:
        raise ConfigError("Pilot validation split must contain at least one record")

    try:
        import accelerate
        import bitsandbytes
        import datasets
        import peft
        import torch
        import transformers
        from accelerate import Accelerator
        from datasets import load_dataset
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            BitsAndBytesConfig,
            DataCollatorForLanguageModeling,
            Trainer,
            TrainingArguments,
        )
    except ImportError as exc:
        raise ConfigError("Install the training extra before launching QLoRA") from exc

    accelerator = Accelerator()
    if gate["require_two_gpus"] and torch.cuda.device_count() < 2:
        raise ConfigError(f"Two CUDA GPUs are required; found {torch.cuda.device_count()}")

    run = training_config["training"]
    output_dir = resolve_project_path(run["output_dir"], root)
    versions = {
        "accelerate": accelerate.__version__,
        "bitsandbytes": bitsandbytes.__version__,
        "datasets": datasets.__version__,
        "peft": peft.__version__,
        "torch": torch.__version__,
        "transformers": transformers.__version__,
    }
    manifest_path = output_dir / "run_manifest.json"
    if accelerator.is_main_process:
        manifest_path = _write_run_manifest(
            output_dir,
            model_config_path,
            training_config_path,
            model_config,
            train_path,
            validation_path,
            versions,
        )
    accelerator.wait_for_everyone()

    quantization = model_config["quantization"]
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=quantization["load_in_4bit"],
        bnb_4bit_quant_type=quantization["quant_type"],
        bnb_4bit_use_double_quant=quantization["double_quant"],
        bnb_4bit_compute_dtype=_dtype(torch, quantization["compute_dtype"]),
    )
    tokenizer = AutoTokenizer.from_pretrained(
        model["id"], revision=model["revision"], trust_remote_code=model["trust_remote_code"]
    )
    if tokenizer.chat_template is None:
        raise ConfigError("The pinned tokenizer has no chat template; define one explicitly")
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token

    local_rank = accelerator.local_process_index
    base_model = AutoModelForCausalLM.from_pretrained(
        model["id"],
        revision=model["revision"],
        trust_remote_code=model["trust_remote_code"],
        quantization_config=quantization_config,
        torch_dtype=_dtype(torch, quantization["compute_dtype"]),
        device_map={"": local_rank},
    )
    base_model.config.use_cache = model["use_cache"]
    base_model = prepare_model_for_kbit_training(
        base_model, use_gradient_checkpointing=run["gradient_checkpointing"]
    )
    lora = model_config["lora"]
    peft_config = LoraConfig(
        r=lora["r"],
        lora_alpha=lora["alpha"],
        lora_dropout=lora["dropout"],
        bias=lora["bias"],
        target_modules=lora["target_modules"],
        task_type="CAUSAL_LM",
    )
    tuned_model = get_peft_model(base_model, peft_config)

    dataset = load_dataset(
        "json", data_files={"train": str(train_path), "validation": str(validation_path)}
    )

    def tokenize(batch: dict[str, Any]) -> dict[str, Any]:
        texts = [
            tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
            for messages in batch["messages"]
        ]
        return tokenizer(
            texts,
            truncation=True,
            max_length=data["max_sequence_length"],
            padding=False,
        )

    tokenized = dataset.map(
        tokenize,
        batched=True,
        remove_columns=dataset["train"].column_names,
        desc="Tokenizing audited conversations",
    )
    arguments = TrainingArguments(
        output_dir=str(output_dir),
        seed=run["seed"],
        data_seed=run["seed"],
        per_device_train_batch_size=run["per_device_train_batch_size"],
        per_device_eval_batch_size=run["per_device_eval_batch_size"],
        gradient_accumulation_steps=run["gradient_accumulation_steps"],
        learning_rate=run["learning_rate"],
        num_train_epochs=run["num_train_epochs"],
        warmup_ratio=run["warmup_ratio"],
        weight_decay=run["weight_decay"],
        logging_steps=run["logging_steps"],
        save_steps=run["save_steps"],
        eval_steps=run["eval_steps"],
        save_total_limit=run["save_total_limit"],
        eval_strategy="steps",
        save_strategy="steps",
        bf16=run["bf16"],
        tf32=run["tf32"],
        gradient_checkpointing=run["gradient_checkpointing"],
        optim=run["optim"],
        lr_scheduler_type=run["lr_scheduler_type"],
        report_to=[],
        ddp_find_unused_parameters=False,
    )
    trainer = Trainer(
        model=tuned_model,
        args=arguments,
        train_dataset=tokenized["train"],
        eval_dataset=tokenized["validation"],
        data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False),
    )
    result = trainer.train()
    trainer.save_model(str(output_dir / "adapter"))
    tokenizer.save_pretrained(output_dir / "adapter")
    if accelerator.is_main_process:
        _finish_manifest(manifest_path, result.metrics)
    accelerator.wait_for_everyone()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
