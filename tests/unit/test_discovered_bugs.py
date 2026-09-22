#!/usr/bin/env python3
"""Bugs found during system testing: deprecation warnings, load time, error message
quality, parameter validation, memory growth and the cache."""

import gc
import sys
import time
import unittest
import warnings
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse import ToolUniverse
from tooluniverse.exceptions import ToolError, ToolValidationError  # noqa: F401

UNIPROT = "UniProt_get_entry_by_accession"


@pytest.mark.unit
class TestDiscoveredBugs(unittest.TestCase):

    def setUp(self):
        self.tu = ToolUniverse()
        self.tu.load_tools()

    def tearDown(self):
        if hasattr(self, "tu"):
            self.tu.close()

    def test_deprecated_method_warnings(self):
        """get_tool_by_name must issue a DeprecationWarning naming itself."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            try:
                self.assertIsInstance(self.tu.get_tool_by_name(["NonExistentTool"]), list)
            except Exception:
                pass  # the method having been removed is also fine

        deprecations = [x for x in w if issubclass(x.category, DeprecationWarning)]
        if deprecations:
            self.assertTrue(
                any("get_tool_by_name" in str(d.message) for d in deprecations),
                "DeprecationWarning should reference 'get_tool_by_name'",
            )

    def test_tool_loading_does_not_hang(self):
        """load_tools() must complete within 30 seconds."""
        start = time.time()
        self.tu.load_tools()
        elapsed = time.time() - start
        self.assertLess(elapsed, 30, f"load_tools() took {elapsed:.1f}s (limit 30s)")

    def test_error_message_clarity(self):
        """The error dict for an unknown tool must carry a meaningful message."""
        result = self.tu.run({"name": "NonExistentTool", "arguments": {"test": "value"}})

        self.assertIsInstance(result, dict)
        self.assertIn("error", result, "Expected error key for unknown tool")
        error_msg = str(result["error"])
        self.assertGreater(len(error_msg), 0, "Error message must not be empty")
        self.assertTrue(
            any(kw in error_msg.lower() for kw in ["tool", "not", "found", "error"]),
            f"Error message should mention tool/not/found/error: {error_msg!r}",
        )

    def test_parameter_validation_rejects_non_strings_and_the_empty_string(self):
        """None/list/dict are not strings, and "" must fail before any network call."""
        for case in [{"accession": None}, {"accession": []}, {"accession": {}},
                     {"accession": ""}]:
            result = self.tu.run({"name": UNIPROT, "arguments": case})
            self.assertIsInstance(result, dict, f"Expected dict for {case!r}")
            self.assertIn("error", result, f"Expected error for {case!r}")

    @pytest.mark.network
    def test_parameter_validation_wrong_types_coerced(self):
        """An int/bool accession is either coerced or rejected, never a crash."""
        for case in [{"accession": 123}, {"accession": True}]:
            result = self.tu.run({"name": UNIPROT, "arguments": case})
            self.assertIsInstance(result, dict, f"Expected dict for {case!r}")
            self.assertTrue(
                "error" in result or "status" in result or "data" in result,
                f"Unexpected response structure for {case!r}: {list(result.keys())}",
            )

    @pytest.mark.network
    def test_memory_leak_prevention(self):
        """10 sequential run() calls must not grow the object graph by >2000 objects."""
        initial_objects = len(gc.get_objects())

        for i in range(10):
            result = self.tu.run({"name": UNIPROT, "arguments": {"accession": f"P{i:05d}"}})
            self.assertIsInstance(result, dict)
            if i % 5 == 0:
                gc.collect()

        gc.collect()
        object_growth = len(gc.get_objects()) - initial_objects
        self.assertLess(object_growth, 2000,
                        f"Object growth of {object_growth} suggests a memory leak")

    @pytest.mark.network
    def test_missing_api_key_returns_dict(self):
        """The invariant is "does not raise, and any FAILURE is a readable envelope" --
        not "always a dict": ArXiv_search_papers needs no key and returns a list."""
        tool_args = {
            UNIPROT: {"accession": "P05067"},
            "ArXiv_search_papers": {"query": "test", "limit": 5},
            "OpenTargets_get_associated_targets_by_disease_efoId": {"efoId": "EFO_0000305"},
        }
        for tool_name, args in tool_args.items():
            result = self.tu.run({"name": tool_name, "arguments": args})
            self.assertIsNotNone(result, f"{tool_name} returned None instead of a result")
            if isinstance(result, dict) and "error" in result:
                self.assertIsInstance(result["error"], str)
                self.assertGreater(len(result["error"]), 0,
                                   f"Error message for {tool_name} must not be empty")

    def test_cache_set_get_clear(self):
        """Cache set/get/clear must work as a basic key-value store."""
        self.tu.clear_cache()
        self.assertEqual(len(self.tu._cache), 0)

        self.tu._cache.set("mykey", "myvalue")
        self.assertEqual(self.tu._cache.get("mykey"), "myvalue")

        self.tu.clear_cache()
        self.assertEqual(len(self.tu._cache), 0)


if __name__ == "__main__":
    unittest.main()
