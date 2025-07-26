# TimeStamp Parser Module

A comprehensive timestamp parser extracted from Facebook, Instagram, Twitter or other website scrapers that can handle
various timestamp formats embedded in images, posts or in comments and convert them to days ago for classification purpose or any other usage scenario.

### Usage:
```python
    from Timestamp_Parser_toDays import TimestampParser
    
    parser = TimestampParser(verbose=True)
    days_ago = parser.parse_timestamp_to_days("2 hours ago")
    print(f"Days ago: {days_ago}")  # Output: 0
    
    days_ago = parser.parse_timestamp_to_days("27 March 2017")
    print(f"Days ago: {days_ago}")  # Output: actual days since March 27, 2017
```

Script is modular thus easy to import and debug. 
Just make sure file exists in same folder to use it.
