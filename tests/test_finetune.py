"""Tests for Item 13 — Fine-Tuning Loop."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest

from aecos.finetune.collector import InteractionCollector
from aecos.finetune.dataset import DatasetBuilder
from aecos.finetune.deployer import ModelDeployer
from aecos.finetune.evaluator import EvaluationReport, ModelEvaluator
from aecos.finetune.feedback import FeedbackManager
from aecos.finetune.golden_set import GOLDEN_TEST_SET
from aecos.finetune.trainer import TrainingConfig, TrainingManager
from aecos.nlp.providers.fallback import FallbackProvider


# ---------------------------------------------------------------------------
# InteractionCollector
# ---------------------------------------------------------------------------


class TestInteractionCollector:
    def test_log_creates_file(self, tmp_path: Path):
        """Log interaction -> JSONL file created with correct fields."""
        collector = InteractionCollector(tmp_path / "interactions")
        interaction_id = collector.log_interaction(
            prompt="150mm concrete wall",
            context={"region": "LA"},
            raw_output=None,
            parsed_spec={"ifc_class": "IfcWall", "properties": {"thickness_mm": 150}},
            confidence=0.9,
        )

        assert interaction_id
        filepath = tmp_path / "interactions" / f"{interaction_id}.jsonl"
        assert filepath.is_file()

        record = json.loads(filepath.read_text(encoding="utf-8").strip())
        assert record["prompt"] == "150mm concrete wall"
        assert record["confidence"] == 0.9
        assert record["accepted"] is True
        assert record["corrected"] is False
        assert record["parsed_spec"]["ifc_class"] == "IfcWall"

    def test_get_interaction(self, tmp_path: Path):
        collector = InteractionCollector(tmp_path / "interactions")
        iid = collector.log_interaction(
            prompt="test", context=None, raw_output=None,
            parsed_spec={"intent": "create"}, confidence=0.5,
        )

        record = collector.get_interaction(iid)
        assert record is not None
        assert record["prompt"] == "test"

    def test_list_interactions(self, tmp_path: Path):
        collector = InteractionCollector(tmp_path / "interactions")
        collector.log_interaction(
            prompt="wall", context=None, raw_output=None,
            parsed_spec={}, confidence=0.5,
        )
        collector.log_interaction(
            prompt="door", context=None, raw_output=None,
            parsed_spec={}, confidence=0.6,
        )

        interactions = collector.list_interactions()
        assert len(interactions) == 2

    def test_update_interaction(self, tmp_path: Path):
        collector = InteractionCollector(tmp_path / "interactions")
        iid = collector.log_interaction(
            prompt="test", context=None, raw_output=None,
            parsed_spec={}, confidence=0.5,
        )

        success = collector.update_interaction(iid, {"accepted": False})
        assert success

        record = collector.get_interaction(iid)
        assert record["accepted"] is False


# ---------------------------------------------------------------------------
# FeedbackManager
# ---------------------------------------------------------------------------


class TestFeedbackManager:
    def test_record_correction(self, tmp_path: Path):
        """Record correction -> interaction updated."""
        collector = InteractionCollector(tmp_path / "interactions")
        iid = collector.log_interaction(
            prompt="test wall", context=None, raw_output=None,
            parsed_spec={"ifc_class": "IfcWall"}, confidence=0.5,
        )

        fm = FeedbackManager(collector)
        result = fm.record_correction(iid, {"ifc_class": "IfcWall", "thickness_mm": 200})
        assert result is True

        record = collector.get_interaction(iid)
        assert record["corrected"] is True
        assert record["correction"]["thickness_mm"] == 200

    def test_record_approval(self, tmp_path: Path):
        collector = InteractionCollector(tmp_path / "interactions")
        iid = collector.log_interaction(
            prompt="test", context=None, raw_output=None,
            parsed_spec={}, confidence=0.9,
        )

        fm = FeedbackManager(collector)
        fm.record_approval(iid)

        record = collector.get_interaction(iid)
        assert record["accepted"] is True

    def test_record_rejection(self, tmp_path: Path):
        collector = InteractionCollector(tmp_path / "interactions")
        iid = collector.log_interaction(
            prompt="test", context=None, raw_output=None,
            parsed_spec={}, confidence=0.3,
        )

        fm = FeedbackManager(collector)
        fm.record_rejection(iid, "Completely wrong output")

        record = collector.get_interaction(iid)
        assert record["rejected"] is True
        assert record["rejection_reason"] == "Completely wrong output"

    def test_pending_reviews(self, tmp_path: Path):
        collector = InteractionCollector(tmp_path / "interactions")

        # Low confidence -> should be flagged
        collector.log_interaction(
            prompt="ambiguous input", context=None, raw_output=None,
            parsed_spec={}, confidence=0.4,
        )
        # High confidence -> should NOT be flagged
        collector.log_interaction(
            prompt="clear input", context=None, raw_output=None,
            parsed_spec={}, confidence=0.95,
        )

        fm = FeedbackManager(collector)
        pending = fm.get_pending_reviews()
        assert len(pending) == 1
        assert pending[0]["prompt"] == "ambiguous input"


# ---------------------------------------------------------------------------
# DatasetBuilder
# ---------------------------------------------------------------------------


class TestDatasetBuilder:
    def test_build_from_interactions(self, tmp_path: Path):
        """Build from interactions -> valid Alpaca JSONL with train/val split."""
        collector = InteractionCollector(tmp_path / "interactions")

        # Add 10 interactions with high confidence
        for i in range(10):
            collector.log_interaction(
                prompt=f"wall specification {i}",
                context=None,
                raw_output=None,
                parsed_spec={"ifc_class": "IfcWall", "thickness_mm": 150 + i},
                confidence=0.9,
            )

        builder = DatasetBuilder(collector, tmp_path / "datasets")
        train_path = builder.build_dataset(min_confidence=0.85)

        assert train_path.is_file()
        assert train_path.suffix == ".jsonl"

        # Read and verify Alpaca format
        lines = train_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) >= 1

        example = json.loads(lines[0])
        assert "instruction" in example
        assert "input" in example
        assert "output" in example

    def test_dataset_deduplication(self, tmp_path: Path):
        """Duplicate prompts -> only one entry."""
        collector = InteractionCollector(tmp_path / "interactions")

        # Add duplicate interactions
        for _ in range(3):
            collector.log_interaction(
                prompt="150mm concrete wall",
                context=None,
                raw_output=None,
                parsed_spec={"ifc_class": "IfcWall"},
                confidence=0.95,
            )

        builder = DatasetBuilder(collector, tmp_path / "datasets")
        train_path = builder.build_dataset()

        # Should only have 1 unique entry
        all_lines = []
        for p in (tmp_path / "datasets").glob("*.jsonl"):
            all_lines.extend(
                p.read_text(encoding="utf-8").strip().split("\n")
            )
        # Filter non-empty
        all_lines = [l for l in all_lines if l.strip()]

        # Combined train + val should have exactly 1 entry
        assert len(all_lines) == 1

    def test_corrections_included(self, tmp_path: Path):
        """Corrected interactions should be included in dataset."""
        collector = InteractionCollector(tmp_path / "interactions")
        iid = collector.log_interaction(
            prompt="bad wall spec",
            context=None,
            raw_output=None,
            parsed_spec={"ifc_class": "IfcSlab"},  # Wrong
            confidence=0.3,
        )

        fm = FeedbackManager(collector)
        fm.record_correction(iid, {"ifc_class": "IfcWall", "thickness_mm": 200})

        builder = DatasetBuilder(collector, tmp_path / "datasets")
        train_path = builder.build_dataset(min_confidence=0.0, include_corrections=True)

        lines = train_path.read_text(encoding="utf-8").strip().split("\n")
        lines = [l for l in lines if l.strip()]
        assert len(lines) >= 1

        example = json.loads(lines[0])
        output = json.loads(example["output"])
        assert output["ifc_class"] == "IfcWall"

    def test_train_val_split(self, tmp_path: Path):
        """Dataset should be split into train and validation sets."""
        collector = InteractionCollector(tmp_path / "interactions")
        for i in range(20):
            collector.log_interaction(
                prompt=f"wall specification number {i}",
                context=None,
                raw_output=None,
                parsed_spec={"ifc_class": "IfcWall", "index": i},
                confidence=0.95,
            )

        builder = DatasetBuilder(collector, tmp_path / "datasets")
        train_path = builder.build_dataset()

        # Find val file
        dataset_files = list((tmp_path / "datasets").glob("*.jsonl"))
        assert len(dataset_files) == 2  # train + val

        train_files = [f for f in dataset_files if "train" in f.name]
        val_files = [f for f in dataset_files if "val" in f.name]
        assert len(train_files) == 1
        assert len(val_files) == 1


# ---------------------------------------------------------------------------
# Golden test set
# ---------------------------------------------------------------------------


class TestGoldenSet:
    def test_golden_set_has_30_prompts(self):
        """Verify 30 golden test prompts present."""
        assert len(GOLDEN_TEST_SET) == 30

    def test_all_have_expected_output(self):
        """All golden test cases have expected output."""
        for i, case in enumerate(GOLDEN_TEST_SET):
            assert "prompt" in case, f"Case {i} missing prompt"
            assert "expected" in case, f"Case {i} missing expected"
            assert isinstance(case["prompt"], str)
            assert isinstance(case["expected"], dict)

    def test_covers_all_ifc_classes(self):
        """Golden set covers wall, door, window, slab, column, beam."""
        classes = set()
        for case in GOLDEN_TEST_SET:
            ifc_class = case["expected"].get("ifc_class", "")
            if ifc_class:
                classes.add(ifc_class)

        assert "IfcWall" in classes
        assert "IfcDoor" in classes
        assert "IfcWindow" in classes
        assert "IfcSlab" in classes
        assert "IfcColumn" in classes
        assert "IfcBeam" in classes


# ---------------------------------------------------------------------------
# ModelEvaluator
# ---------------------------------------------------------------------------


class TestModelEvaluator:
    def test_evaluate_fallback_provider(self):
        """Evaluate FallbackProvider -> scores returned."""
        provider = FallbackProvider()
        evaluator = ModelEvaluator()
        report = evaluator.evaluate(provider)

        assert isinstance(report, EvaluationReport)
        assert report.total_cases == 30
        assert 0.0 <= report.intent_accuracy <= 1.0
        assert 0.0 <= report.ifc_class_accuracy <= 1.0
        assert 0.0 <= report.property_accuracy <= 1.0
        assert 0.0 <= report.material_accuracy <= 1.0
        assert 0.0 <= report.overall_score <= 1.0

    def test_evaluation_report_to_markdown(self):
        provider = FallbackProvider()
        evaluator = ModelEvaluator()
        report = evaluator.evaluate(provider)

        md = report.to_markdown()
        assert "Evaluation Report" in md
        assert "Intent Accuracy" in md
        assert "Overall Score" in md


# ---------------------------------------------------------------------------
# ModelDeployer
# ---------------------------------------------------------------------------


class TestModelDeployer:
    def test_deployer_without_ollama(self, tmp_path: Path):
        """ModelDeployer without Ollama -> stores metadata only, no crash."""
        registry_path = tmp_path / "registry.json"
        deployer = ModelDeployer(registry_path)

        entry = deployer.register_model(
            adapter_path=tmp_path / "adapter",
            model_name="test-model",
            version="1.0",
        )

        assert entry is not None
        assert entry["version"] == "1.0"
        assert entry["deployed"] is False  # Ollama not available

        # Registry persisted
        assert registry_path.is_file()
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        assert "test-model" in registry
        assert len(registry["test-model"]) == 1

    def test_list_models(self, tmp_path: Path):
        deployer = ModelDeployer(tmp_path / "registry.json")
        deployer.register_model(tmp_path / "a1", "model-a", "1.0")
        deployer.register_model(tmp_path / "a2", "model-a", "2.0")
        deployer.register_model(tmp_path / "b1", "model-b", "1.0")

        models = deployer.list_models()
        assert len(models) == 2
        assert len(models["model-a"]) == 2
        assert len(models["model-b"]) == 1

    def test_rollback(self, tmp_path: Path):
        deployer = ModelDeployer(tmp_path / "registry.json")
        deployer.register_model(tmp_path / "a1", "model-a", "1.0")
        deployer.register_model(tmp_path / "a2", "model-a", "2.0")

        result = deployer.rollback("model-a", "1.0")
        assert result is not None
        assert result["version"] == "1.0"

    def test_rollback_nonexistent(self, tmp_path: Path):
        deployer = ModelDeployer(tmp_path / "registry.json")
        result = deployer.rollback("missing", "1.0")
        assert result is None


# ---------------------------------------------------------------------------
# TrainingManager
# ---------------------------------------------------------------------------


class TestTrainingManager:
    def test_train_without_gpu(self, tmp_path: Path):
        """TrainingManager without GPU -> logs warning, returns mock result."""
        trainer = TrainingManager(tmp_path / "models")
        config = trainer.prepare_config(
            base_model="test-model",
            dataset_path=str(tmp_path / "dataset.jsonl"),
            output_name="test-run",
        )

        result = trainer.train(config)
        assert result.success
        assert result.mock is True
        assert result.model_path is not None
        assert "mock" in result.message.lower() or "no gpu" in result.message.lower()

    def test_prepare_config(self, tmp_path: Path):
        trainer = TrainingManager(tmp_path / "models")
        config = trainer.prepare_config(
            base_model="llama3.3:70b",
            dataset_path="/data/train.jsonl",
            output_name="my-model",
        )

        assert isinstance(config, TrainingConfig)
        assert config.base_model == "llama3.3:70b"
        assert config.lora_r == 64
        assert config.lora_alpha == 16
        assert config.lora_dropout == 0.05
        assert config.learning_rate == 2e-5
        assert config.num_epochs == 3


# ---------------------------------------------------------------------------
# Full round-trip
# ---------------------------------------------------------------------------


class TestFullRoundTrip:
    def test_log_build_verify(self, tmp_path: Path):
        """Full round-trip: log interaction -> build dataset -> verify in JSONL."""
        collector = InteractionCollector(tmp_path / "interactions")

        # Log interactions
        for i in range(5):
            collector.log_interaction(
                prompt=f"concrete wall {150 + i * 10}mm thick",
                context={"region": "LA"},
                raw_output=None,
                parsed_spec={
                    "ifc_class": "IfcWall",
                    "properties": {"thickness_mm": 150 + i * 10},
                },
                confidence=0.9,
            )

        # Build dataset
        builder = DatasetBuilder(collector, tmp_path / "datasets")
        train_path = builder.build_dataset()

        # Verify
        assert train_path.is_file()
        lines = train_path.read_text(encoding="utf-8").strip().split("\n")
        lines = [l for l in lines if l.strip()]
        assert len(lines) >= 1

        for line in lines:
            example = json.loads(line)
            assert "instruction" in example
            output = json.loads(example["output"])
            assert output["ifc_class"] == "IfcWall"
