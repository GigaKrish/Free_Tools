"""
Facebook Timestamp Parser Module

A comprehensive timestamp parser extracted from Facebook scraper that can handle
various Facebook timestamp formats and convert them to days ago.

Usage:
    from timestamp_parser import FacebookTimestampParser
    
    parser = FacebookTimestampParser(verbose=True)
    days_ago = parser.parse_timestamp_to_days("2 hours ago")
    print(f"Days ago: {days_ago}")  # Output: 0
    
    days_ago = parser.parse_timestamp_to_days("27 March 2017")
    print(f"Days ago: {days_ago}")  # Output: actual days since March 27, 2017
"""

import re
from datetime import datetime


class TimestampParser:
    """
    A comprehensive parser for Facebook timestamps that converts various
    timestamp formats into days ago from current date.
    
    Handles formats like:
    - "27 March 2017"
    - "13 Feb 10:37" (current year assumed)
    - "March 27, 2017"
    - "2 hours ago"
    - "Yesterday at 3:45 PM"
    - "Just now"
    - "3d", "2w" (short forms)
    - And many more Facebook timestamp variations
    """
    
    def __init__(self, verbose=False):
        """
        Initialize the timestamp parser.
        
        Args:
            verbose (bool): If True, prints detailed parsing information
        """
        self.verbose = verbose
        
        # Month abbreviation mappings
        self.month_mappings = {
            'jan': 'january', 'feb': 'february', 'mar': 'march', 'apr': 'april',
            'may': 'may', 'jun': 'june', 'jul': 'july', 'aug': 'august',
            'sep': 'september', 'sept': 'september', 'oct': 'october',
            'nov': 'november', 'dec': 'december'
        }
    
    def log(self, message):
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            print(f"[TimestampParser] {message}")
    
    def parse_timestamp_to_days(self, timestamp):
        """
        Parse Facebook timestamps into days ago.
        
        Args:
            timestamp (str): The timestamp string to parse
            
        Returns:
            int or None: Number of days ago, or None if parsing failed
        """
        ts_lower = str(timestamp).lower().strip()
        now = datetime.now()

        self.log(f"Parsing timestamp: '{ts_lower}'")

        if not ts_lower:
            return None

        # Handle immediate timestamps
        if any(phrase in ts_lower for phrase in ["just now", " now", "a moment ago", "moments ago"]):
            self.log("Matched immediate timestamp - returning 0 days")
            return 0

        # Handle seconds/minutes/hours (same day) - including short forms
        time_units = [
            (r"(\d+)\s*s(?:ec|ecs|econd|econds)?\b", 0),  # seconds
            (r"(\d+)\s*(?:m|min|mins|minute|minutes)\b", 0),  # minutes
            (r"(\d+)\s*(?:h|hr|hrs|hour|hours)\b", 0),  # hours - includes "2h"
        ]

        for pattern, days in time_units:
            match = re.search(pattern, ts_lower)
            if match:
                self.log(f"Matched time unit pattern: {pattern} - returning {days} days")
                return days

        # Handle "yesterday"
        if "yesterday" in ts_lower:
            self.log("Matched 'yesterday' - returning 1 day")
            return 1

        # Handle days/weeks explicitly mentioned - including short forms like "3d", "2w"
        relative_patterns = [
            (r"(\d+)\s*(?:d|day|days)\b(?:\s*ago)?", lambda x: int(x)),  # includes "3d"
            (r"(\d+)\s*(?:w|wk|week|weeks)\b(?:\s*ago)?", lambda x: int(x) * 7),  # includes "2w"
        ]

        for pattern, converter in relative_patterns:
            match = re.search(pattern, ts_lower)
            if match:
                result = converter(match.group(1))
                self.log(f"Matched relative pattern: {pattern} - returning {result} days")
                return result

        # Clean up the timestamp for date parsing
        # Remove time portions like "at 10:37", "at 3:45 PM", "at 17:50", "at 15:00" etc.
        ts_cleaned = re.sub(r"\s+at\s+\d{1,2}:\d{2}(?::\d{2})?(?:\s*[ap]m)?", "", ts_lower).strip()

        # Remove trailing info after | or · (like "16 February | Feb")
        ts_cleaned = re.sub(r"\s*[\|·].*$", "", ts_cleaned).strip()

        # Remove "ago" if present
        ts_cleaned = re.sub(r"\s+ago\s*$", "", ts_cleaned).strip()

        # Normalize month abbreviations
        for abbrev, full_name in self.month_mappings.items():
            ts_cleaned = re.sub(rf'\b{abbrev}\b', full_name, ts_cleaned)

        self.log(f"Cleaned timestamp: '{ts_cleaned}'")

        
        date_formats_with_year = [
            "%d %B %Y",      # "22 march 2017"
            "%B %d, %Y",     # "march 27, 2017"
            "%b %d, %Y",     # "mar 27, 2017"
            "%d %b %Y",      # "27 mar 2017"
            "%Y-%m-%d",      # "2017-03-27"
            "%m/%d/%Y",      # "03/27/2017"
            "%d/%m/%Y",      # "27/03/2017"
            "%Y/%m/%d",      # "2017/03/27"
            "%B %d %Y",      # "march 27 2017" (no comma)
            "%d-%B-%Y",      # "27-march-2017"
            "%d-%b-%Y",      # "27-mar-2017"
            "%B %d, %Y",     # "April 15, 2023"
        ]

        # Try parsing with year first
        for fmt_str in date_formats_with_year:
            try:
                parsed_dt = datetime.strptime(ts_cleaned, fmt_str)
                days_diff = (now - parsed_dt).days
                self.log(f"Successfully parsed with format '{fmt_str}' - {days_diff} days ago")
                return max(0, days_diff)
            except ValueError:
                continue

        # Date formats WITHOUT year (assume current or previous year)
        date_formats_no_year = [
            "%d %B",         # "22 march", "29 april"
            "%B %d",         # "april 15", "february 13"
            "%d %b",         # "14 mar", "13 feb"
            "%b %d",         # "may 2", "feb 13"
            "%m/%d",         # "02/13"
            "%d/%m",         # "13/02"
            "%d-%B",         # "13-february"
            "%d-%b",         # "13-feb"
        ]

        # Try parsing without year
        for fmt_str in date_formats_no_year:
            try:
                # First try with current year
                parsed_dt_curr_year = datetime.strptime(f"{ts_cleaned} {now.year}", f"{fmt_str} %Y")

                # If the parsed date is in the future, assume it's from last year
                if parsed_dt_curr_year.date() > now.date():
                    parsed_dt = datetime(now.year - 1, parsed_dt_curr_year.month, parsed_dt_curr_year.day)
                    self.log(f"Date appears to be from last year ({now.year - 1})")
                else:
                    parsed_dt = parsed_dt_curr_year

                days_diff = (now - parsed_dt).days
                self.log(f"Successfully parsed with format '{fmt_str}' (year assumed) - {days_diff} days ago")
                return max(0, days_diff)
            except ValueError:
                continue

        # Handle special Facebook formats that might have been missed
        special_patterns = [
            # "2 days ago", "3 weeks ago", etc. that might have slipped through
            (r"(\d+)\s+days?\s+ago", lambda x: int(x)),
            (r"(\d+)\s+weeks?\s+ago", lambda x: int(x) * 7),
            (r"(\d+)\s+months?\s+ago", lambda x: int(x) * 30),  # Rough approximation
            (r"(\d+)\s+years?\s+ago", lambda x: int(x) * 365),  # Rough approximation
        ]

        for pattern, converter in special_patterns:
            match = re.search(pattern, ts_lower)
            if match:
                result = converter(match.group(1))
                self.log(f"Matched special pattern: {pattern} - {result} days ago")
                return result

        # Last resort: try to extract any date-like patterns
        # Look for patterns like "13 Feb" even if mixed with other text
        date_pattern_match = re.search(r'(\d{1,2})\s+([a-z]+)(?:\s+(\d{4}))?', ts_cleaned)
        if date_pattern_match:
            day_str = date_pattern_match.group(1)
            month_str = date_pattern_match.group(2)
            year_str = date_pattern_match.group(3)

            # Normalize month
            if month_str in self.month_mappings:
                month_str = self.month_mappings[month_str]

            try:
                if year_str:
                    # Has year
                    parsed_dt = datetime.strptime(f"{day_str} {month_str} {year_str}", "%d %B %Y")
                else:
                    # No year, assume current or previous year
                    parsed_dt_curr_year = datetime.strptime(f"{day_str} {month_str} {now.year}", "%d %B %Y")
                    if parsed_dt_curr_year.date() > now.date():
                        parsed_dt = datetime(now.year - 1, parsed_dt_curr_year.month, parsed_dt_curr_year.day)
                    else:
                        parsed_dt = parsed_dt_curr_year

                days_diff = (now - parsed_dt).days
                self.log(f"Matched fallback pattern - {days_diff} days ago")
                return max(0, days_diff)
            except ValueError:
                pass

        # If all parsing attempts failed
        self.log(f"Failed to parse timestamp: '{timestamp}' (cleaned: '{ts_cleaned}')")
        return None

    def parse_multiple_timestamps(self, timestamps):
        """
        Parse multiple timestamps at once.
        
        Args:
            timestamps (list): List of timestamp strings
            
        Returns:
            list: List of tuples (original_timestamp, days_ago)
        """
        results = []
        for timestamp in timestamps:
            days_ago = self.parse_timestamp_to_days(timestamp)
            results.append((timestamp, days_ago))
        return results

    def get_parsed_info(self, timestamp):
        """
        Get detailed parsing information for a timestamp.
        
        Args:
            timestamp (str): The timestamp to parse
            
        Returns:
            dict: Dictionary with parsing details
        """
        days_ago = self.parse_timestamp_to_days(timestamp)
        
        info = {
            'original': timestamp,
            'days_ago': days_ago,
            'parsed_successfully': days_ago is not None,
            'category': self._categorize_timestamp(days_ago) if days_ago is not None else 'unparseable'
        }
        
        return info

    def _categorize_timestamp(self, days_ago):
        """Categorize the timestamp based on days ago."""
        if days_ago == 0:
            return 'today'
        elif days_ago == 1:
            return 'yesterday'
        elif days_ago <= 7:
            return 'this_week'
        elif days_ago <= 30:
            return 'this_month'
        elif days_ago <= 365:
            return 'this_year'
        else:
            return 'older_than_year'


# Convenience functions for quick usage
def parse_timestamp(timestamp, verbose=False):
    """
    Quick function to parse a single timestamp.
    
    Args:
        timestamp (str): The timestamp to parse
        verbose (bool): Enable verbose logging
        
    Returns:
        int or None: Days ago, or None if parsing failed
    """
    parser = TimestampParser(verbose=verbose)
    return parser.parse_timestamp_to_days(timestamp)


def parse_timestamps(timestamps, verbose=False):
    """
    Quick function to parse multiple timestamps.
    
    Args:
        timestamps (list): List of timestamps to parse
        verbose (bool): Enable verbose logging
        
    Returns:
        list: List of tuples (original_timestamp, days_ago)
    """
    parser = TimestampParser(verbose=verbose)
    return parser.parse_multiple_timestamps(timestamps)


# Example usage and testing
if __name__ == "__main__":
    # Test the parser with various timestamp formats
    test_timestamps = [
        "just now",
        "2 hours ago",
        "yesterday at 3:45 PM",
        "3d",
        "2w",
        "27 March 2017",
        "13 Feb 10:37",
        "March 27, 2017",
        "Yesterday at 15:30",
        "5 days ago",
        "2 weeks ago",
        "April 15, 2023",
        "14 mar 2020",
        "feb 13",
        "29 april",
        "invalid timestamp"
    ]
    
    print("Testing Facebook Timestamp Parser")
    print("=" * 50)
    
    # Test with verbose mode
    parser = TimestampParser(verbose=True)
    
    for timestamp in test_timestamps:
        print(f"\nTesting: '{timestamp}'")
        result = parser.parse_timestamp_to_days(timestamp)
        info = parser.get_parsed_info(timestamp)
        
        print(f"Result: {result} days ago")
        print(f"Category: {info['category']}")
        print("-" * 30)
    
    print("\n" + "=" * 50)
    print("Quick parsing without verbose:")
    
    # Test quick functions
    quick_results = parse_timestamps(["2 hours ago", "27 March 2017", "invalid"])
    for original, days_ago in quick_results:
        status = f"{days_ago} days ago" if days_ago is not None else "Failed to parse"
        print(f"'{original}' -> {status}")
