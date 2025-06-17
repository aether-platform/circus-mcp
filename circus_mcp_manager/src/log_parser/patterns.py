"""
Pattern management for log classification.
"""

import re
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

from ..utils.exceptions import LogPatternError, ConfigurationError
from ..utils.helpers import load_config


logger = logging.getLogger(__name__)


class LogPattern:
    """Represents a single log pattern."""

    def __init__(self, regex: str, priority: int = 1, flags: int = 0) -> None:
        """
        Initialize log pattern.

        Args:
            regex: Regular expression pattern
            priority: Pattern priority (lower = higher priority)
            flags: Regex flags
        """
        self.regex_str = regex
        self.priority = priority
        self.flags = flags

        try:
            self.compiled_regex = re.compile(regex, flags)
        except re.error as e:
            raise LogPatternError(f"Invalid regex pattern '{regex}': {str(e)}")

    def match(self, text: str) -> bool:
        """
        Check if pattern matches text.

        Args:
            text: Text to match against

        Returns:
            True if pattern matches
        """
        return bool(self.compiled_regex.search(text))

    def __repr__(self) -> str:
        return f"LogPattern(regex='{self.regex_str}', priority={self.priority})"


class PatternManager:
    """Manages log patterns for classification."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        """
        Initialize pattern manager.

        Args:
            config_path: Path to log patterns configuration file
        """
        self.config_path = config_path or Path("config/log_patterns.yaml")
        self.patterns: Dict[str, List[LogPattern]] = {}
        self.custom_patterns: Dict[str, List[LogPattern]] = {}
        self._load_patterns()

    def _load_patterns(self) -> None:
        """Load patterns from configuration file."""
        try:
            if self.config_path.exists():
                config = load_config(self.config_path, "yaml")
                self._parse_patterns_config(config)
                logger.info(f"Loaded log patterns from {self.config_path}")
            else:
                logger.warning(f"Pattern config file not found: {self.config_path}")
                self._load_default_patterns()
        except Exception as e:
            logger.error(f"Failed to load patterns: {str(e)}")
            self._load_default_patterns()

    def _parse_patterns_config(self, config: Dict[str, Any]) -> None:
        """Parse patterns from configuration."""
        # Load standard patterns
        patterns_config = config.get("patterns", {})
        for level, pattern_list in patterns_config.items():
            self.patterns[level] = []
            for pattern_info in pattern_list:
                if isinstance(pattern_info, dict):
                    regex = pattern_info.get("regex", "")
                    priority = pattern_info.get("priority", 1)
                    flags = self._parse_regex_flags(pattern_info.get("flags", []))
                else:
                    regex = str(pattern_info)
                    priority = 1
                    flags = 0

                if regex:
                    try:
                        pattern = LogPattern(regex, priority, flags)
                        self.patterns[level].append(pattern)
                    except LogPatternError as e:
                        logger.error(f"Invalid pattern for level {level}: {str(e)}")

        # Load custom patterns
        custom_config = config.get("custom_patterns", {})
        for level, pattern_list in custom_config.items():
            self.custom_patterns[level] = []
            for pattern_info in pattern_list:
                if isinstance(pattern_info, dict):
                    regex = pattern_info.get("regex", "")
                    priority = pattern_info.get("priority", 1)
                    flags = self._parse_regex_flags(pattern_info.get("flags", []))
                else:
                    regex = str(pattern_info)
                    priority = 1
                    flags = 0

                if regex:
                    try:
                        pattern = LogPattern(regex, priority, flags)
                        self.custom_patterns[level].append(pattern)
                    except LogPatternError as e:
                        logger.error(
                            f"Invalid custom pattern for level {level}: {str(e)}"
                        )

    def _parse_regex_flags(self, flags_list: List[str]) -> int:
        """Parse regex flags from string list."""
        flags = 0
        flag_mapping = {
            "IGNORECASE": re.IGNORECASE,
            "MULTILINE": re.MULTILINE,
            "DOTALL": re.DOTALL,
            "VERBOSE": re.VERBOSE,
        }

        for flag_name in flags_list:
            if flag_name in flag_mapping:
                flags |= flag_mapping[flag_name]

        return flags

    def _load_default_patterns(self) -> None:
        """Load default patterns."""
        self.patterns = {
            "error": [
                LogPattern(
                    r"ERROR|Exception|Traceback|Fatal|Critical", 1, re.IGNORECASE
                ),
                LogPattern(r"\[ERROR\]|\[FATAL\]|\[CRITICAL\]", 1),
            ],
            "warning": [
                LogPattern(r"WARNING|WARN", 2, re.IGNORECASE),
                LogPattern(r"\[WARNING\]|\[WARN\]", 2),
            ],
            "info": [
                LogPattern(
                    r"INFO|Starting|Stopping|Listening|Server", 3, re.IGNORECASE
                ),
                LogPattern(r"\[INFO\]", 3),
            ],
            "debug": [
                LogPattern(r"DEBUG", 4, re.IGNORECASE),
                LogPattern(r"\[DEBUG\]", 4),
            ],
        }
        self.custom_patterns = {}
        logger.info("Loaded default log patterns")

    def get_patterns(self, level: str) -> List[LogPattern]:
        """
        Get patterns for a specific level.

        Args:
            level: Log level

        Returns:
            List of patterns for the level
        """
        patterns = self.patterns.get(level, []).copy()
        patterns.extend(self.custom_patterns.get(level, []))

        # Sort by priority
        patterns.sort(key=lambda p: p.priority)

        return patterns

    def get_all_patterns(self) -> Dict[str, List[LogPattern]]:
        """
        Get all patterns organized by level.

        Returns:
            Dictionary of patterns by level
        """
        all_patterns = {}

        # Combine standard and custom patterns
        all_levels = set(self.patterns.keys()) | set(self.custom_patterns.keys())

        for level in all_levels:
            all_patterns[level] = self.get_patterns(level)

        return all_patterns

    def add_custom_pattern(self, level: str, regex: str, priority: int = 1) -> None:
        """
        Add a custom pattern.

        Args:
            level: Log level
            regex: Regular expression pattern
            priority: Pattern priority

        Raises:
            LogPatternError: If pattern is invalid
        """
        try:
            pattern = LogPattern(regex, priority)

            if level not in self.custom_patterns:
                self.custom_patterns[level] = []

            self.custom_patterns[level].append(pattern)
            logger.info(f"Added custom pattern for level {level}: {regex}")

        except LogPatternError as e:
            logger.error(f"Failed to add custom pattern: {str(e)}")
            raise

    def remove_custom_pattern(self, level: str, regex: str) -> bool:
        """
        Remove a custom pattern.

        Args:
            level: Log level
            regex: Regular expression pattern to remove

        Returns:
            True if pattern was removed
        """
        if level not in self.custom_patterns:
            return False

        patterns = self.custom_patterns[level]
        for i, pattern in enumerate(patterns):
            if pattern.regex_str == regex:
                del patterns[i]
                logger.info(f"Removed custom pattern for level {level}: {regex}")
                return True

        return False

    def validate_patterns(self) -> List[str]:
        """
        Validate all patterns.

        Returns:
            List of validation errors
        """
        errors = []

        all_patterns = self.get_all_patterns()
        for level, patterns in all_patterns.items():
            for pattern in patterns:
                try:
                    # Test pattern compilation
                    re.compile(pattern.regex_str, pattern.flags)
                except re.error as e:
                    errors.append(
                        f"Invalid pattern in level {level}: {pattern.regex_str} - {str(e)}"
                    )

        return errors

    def reload_patterns(self) -> None:
        """Reload patterns from configuration file."""
        self.patterns.clear()
        self.custom_patterns.clear()
        self._load_patterns()
        logger.info("Reloaded log patterns")

    def get_pattern_stats(self) -> Dict[str, Any]:
        """
        Get statistics about loaded patterns.

        Returns:
            Pattern statistics
        """
        all_patterns = self.get_all_patterns()

        stats = {
            "total_levels": len(all_patterns),
            "total_patterns": sum(len(patterns) for patterns in all_patterns.values()),
            "levels": {},
        }

        for level, patterns in all_patterns.items():
            standard_count = len(self.patterns.get(level, []))
            custom_count = len(self.custom_patterns.get(level, []))

            stats["levels"][level] = {
                "total_patterns": len(patterns),
                "standard_patterns": standard_count,
                "custom_patterns": custom_count,
            }

        return stats
