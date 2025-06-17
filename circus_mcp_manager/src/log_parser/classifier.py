"""
Log classifier for categorizing log entries.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..utils.exceptions import LogParserError
from ..utils.helpers import format_log_entry, parse_log_level
from .patterns import PatternManager


logger = logging.getLogger(__name__)


class LogClassifier:
    """Classifies log entries based on patterns."""

    def __init__(self, pattern_manager: Optional[PatternManager] = None) -> None:
        """
        Initialize log classifier.

        Args:
            pattern_manager: Pattern manager instance
        """
        self.pattern_manager = pattern_manager or PatternManager()
        self._classification_stats = {
            "total_classified": 0,
            "by_level": {},
        }

    def classify_log_entry(
        self,
        log_text: str,
        process_name: str = "unknown",
        timestamp: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Classify a single log entry.

        Args:
            log_text: Log text to classify
            process_name: Name of the process that generated the log
            timestamp: Log timestamp (defaults to current time)

        Returns:
            Classified log entry
        """
        if timestamp is None:
            timestamp = datetime.now()

        # Determine log level based on patterns
        detected_level = self._detect_log_level(log_text)

        # Format log entry
        log_entry = format_log_entry(
            timestamp=timestamp,
            level=detected_level,
            process_name=process_name,
            message=log_text,
            extra_data={
                "classification_method": "pattern_matching",
                "patterns_checked": self._get_patterns_checked_count(),
            },
        )

        # Update statistics
        self._update_stats(detected_level)

        return log_entry

    def classify_log_batch(
        self, log_entries: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Classify a batch of log entries.

        Args:
            log_entries: List of log entries with 'text', 'process_name', 'timestamp'

        Returns:
            List of classified log entries
        """
        classified_entries = []

        for entry in log_entries:
            try:
                log_text = entry.get("text", "")
                process_name = entry.get("process_name", "unknown")
                timestamp = entry.get("timestamp")

                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp)
                elif timestamp is None:
                    timestamp = datetime.now()

                classified_entry = self.classify_log_entry(
                    log_text, process_name, timestamp
                )
                classified_entries.append(classified_entry)

            except Exception as e:
                logger.error(f"Error classifying log entry: {str(e)}")
                # Add error entry
                classified_entries.append(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "level": "error",
                        "process_name": "classifier",
                        "message": f"Classification error: {str(e)}",
                        "original_entry": entry,
                    }
                )

        return classified_entries

    def _detect_log_level(self, log_text: str) -> str:
        """
        Detect log level based on patterns.

        Args:
            log_text: Log text to analyze

        Returns:
            Detected log level
        """
        all_patterns = self.pattern_manager.get_all_patterns()

        # Check patterns in priority order
        matches = []

        for level, patterns in all_patterns.items():
            for pattern in patterns:
                if pattern.match(log_text):
                    matches.append((level, pattern.priority))

        if matches:
            # Sort by priority (lower number = higher priority)
            matches.sort(key=lambda x: x[1])
            return matches[0][0]

        # Default level if no patterns match
        return "info"

    def _get_patterns_checked_count(self) -> int:
        """Get total number of patterns checked."""
        all_patterns = self.pattern_manager.get_all_patterns()
        return sum(len(patterns) for patterns in all_patterns.values())

    def _update_stats(self, level: str) -> None:
        """Update classification statistics."""
        self._classification_stats["total_classified"] += 1

        if level not in self._classification_stats["by_level"]:
            self._classification_stats["by_level"][level] = 0

        self._classification_stats["by_level"][level] += 1

    def get_classification_stats(self) -> Dict[str, Any]:
        """
        Get classification statistics.

        Returns:
            Classification statistics
        """
        return self._classification_stats.copy()

    def reset_stats(self) -> None:
        """Reset classification statistics."""
        self._classification_stats = {
            "total_classified": 0,
            "by_level": {},
        }
        logger.info("Classification statistics reset")

    def add_custom_pattern(self, level: str, regex: str, priority: int = 1) -> None:
        """
        Add a custom classification pattern.

        Args:
            level: Log level for the pattern
            regex: Regular expression pattern
            priority: Pattern priority
        """
        self.pattern_manager.add_custom_pattern(level, regex, priority)
        logger.info(f"Added custom classification pattern for level {level}")

    def remove_custom_pattern(self, level: str, regex: str) -> bool:
        """
        Remove a custom classification pattern.

        Args:
            level: Log level
            regex: Regular expression pattern to remove

        Returns:
            True if pattern was removed
        """
        result = self.pattern_manager.remove_custom_pattern(level, regex)
        if result:
            logger.info(f"Removed custom classification pattern for level {level}")
        return result

    def test_classification(self, test_logs: List[str]) -> Dict[str, Any]:
        """
        Test classification on sample logs.

        Args:
            test_logs: List of log texts to test

        Returns:
            Test results
        """
        results = {
            "total_tested": len(test_logs),
            "classifications": {},
            "details": [],
        }

        for i, log_text in enumerate(test_logs):
            try:
                classified = self.classify_log_entry(log_text, f"test_process_{i}")
                level = classified["level"]

                if level not in results["classifications"]:
                    results["classifications"][level] = 0
                results["classifications"][level] += 1

                results["details"].append(
                    {
                        "input": log_text,
                        "classified_level": level,
                        "success": True,
                    }
                )

            except Exception as e:
                results["details"].append(
                    {
                        "input": log_text,
                        "error": str(e),
                        "success": False,
                    }
                )

        return results
