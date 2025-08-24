import pandas as pd
import argparse
import sys
from pathlib import Path
from datetime import datetime
import re


class CSVCleaner:
    def __init__(self, input_file):
        """Initialize the CSV cleaner with input file path."""
        self.input_file = input_file
        self.df = None
        self.original_rows = 0

    def convert_text_to_csv(self, delimiter=None, has_header=True, output_file=None, encoding='utf-8'):
        """
        Convert a delimited text file to CSV format.

        Args:
            delimiter: The delimiter used in the text file (None for auto-detect)
            has_header: Whether the first line contains column headers
            output_file: Output CSV file path (optional)
            encoding: File encoding (default: utf-8)
        """
        try:
            # Read the file to analyze its structure
            with open(self.input_file, 'r', encoding=encoding) as file:
                lines = file.readlines()

            if not lines:
                print("Error: File is empty")
                return False

            # Auto-detect delimiter if not provided
            if delimiter is None:
                delimiter = self._detect_delimiter(lines[:5])  # Check first 5 lines
                if delimiter is None:
                    print("Error: Could not auto-detect delimiter")
                    return False
                print(f"Auto-detected delimiter: '{delimiter}'")

            # Handle special delimiter names
            delimiter_map = {
                'tab': '\t',
                'space': ' ',
                'pipe': '|',
                'semicolon': ';',
                'colon': ':',
                'comma': ','
            }

            if delimiter.lower() in delimiter_map:
                delimiter = delimiter_map[delimiter.lower()]

            # Read the file with pandas using the detected/specified delimiter
            try:
                self.df = pd.read_csv(
                    self.input_file,
                    delimiter=delimiter,
                    header=0 if has_header else None,
                    encoding=encoding,
                    engine='python'  # More flexible for complex delimiters
                )

                # If no header, create generic column names
                if not has_header:
                    self.df.columns = [f'Column_{i + 1}' for i in range(len(self.df.columns))]

                self.original_rows = len(self.df)

                print(f"Successfully converted text file to CSV format")
                print(f"Loaded {self.original_rows} rows and {len(self.df.columns)} columns")
                print(f"Columns: {list(self.df.columns)}")

                # Save as CSV if output file specified
                if output_file:
                    if not self.save_csv(output_file):
                        return False
                else:
                    # Create default output filename
                    input_path = Path(self.input_file)
                    default_output = input_path.parent / f"{input_path.stem}_converted.csv"
                    if not self.save_csv(default_output):
                        return False

                return True

            except Exception as e:
                print(f"Error reading file with delimiter '{delimiter}': {e}")
                return False

        except FileNotFoundError:
            print(f"Error: File '{self.input_file}' not found")
            return False
        except Exception as e:
            print(f"Error reading file: {e}")
            return False

    def _detect_delimiter(self, sample_lines):
        """
        Auto-detect the delimiter used in the text file.

        Args:
            sample_lines: List of sample lines from the file

        Returns:
            The most likely delimiter or None if detection fails
        """
        # Common delimiters to test
        delimiters = [',', '\t', ';', ':', '|', ' ']
        delimiter_scores = {}

        for delimiter in delimiters:
            scores = []
            for line in sample_lines:
                line = line.strip()
                if line:
                    # Count occurrences of this delimiter
                    count = line.count(delimiter)
                    scores.append(count)

            if scores:
                # Calculate consistency - good delimiters should appear
                # roughly the same number of times in each line
                avg_score = sum(scores) / len(scores)
                if avg_score > 0:
                    # Calculate variance to measure consistency
                    variance = sum((score - avg_score) ** 2 for score in scores) / len(scores)
                    # Good delimiters have high average and low variance
                    delimiter_scores[delimiter] = avg_score / (1 + variance)

        if not delimiter_scores:
            return None

        # Return the delimiter with the highest score
        best_delimiter = max(delimiter_scores.items(), key=lambda x: x[1])[0]

        # Ensure the best delimiter appears at least once in most lines
        if delimiter_scores[best_delimiter] < 0.5:
            return None

        return best_delimiter

    def load_csv(self):
        """Load CSV file into pandas DataFrame."""
        try:
            self.df = pd.read_csv(self.input_file)
            self.original_rows = len(self.df)
            print(f"Loaded CSV with {self.original_rows} rows and {len(self.df.columns)} columns")
            print(f"Columns: {list(self.df.columns)}")
            return True
        except FileNotFoundError:
            print(f"Error: File '{self.input_file}' not found")
            return False
        except Exception as e:
            print(f"Error loading CSV: {e}")
            return False

    def _normalize_column_name(self, column_name):
        """Normalize column name by stripping whitespace only (case-sensitive)."""
        return column_name.strip()

    def _normalize_value(self, value):
        """Normalize value by stripping whitespace and converting to lowercase for comparison."""
        if pd.isna(value):
            return value
        return str(value).strip().lower()

    def _find_exact_column(self, target_column):
        """Find exact column match (case-sensitive, ignoring only whitespace)."""
        target_normalized = self._normalize_column_name(target_column)

        for col in self.df.columns:
            if self._normalize_column_name(col) == target_normalized:
                return col
        return None

    def remove_duplicates(self, unique_column):
        """Remove duplicate rows based on a unique column."""
        exact_column = self._find_exact_column(unique_column)

        if exact_column is None:
            print(f"Error: Column '{unique_column}' not found in CSV")
            print(f"Available columns: {list(self.df.columns)}")
            return False

        initial_count = len(self.df)

        # Remove duplicates based on the unique column, keep first occurrence
        self.df = self.df.drop_duplicates(subset=[exact_column], keep='first')

        duplicates_removed = initial_count - len(self.df)
        print(f"Removed {duplicates_removed} duplicate rows based on '{exact_column}'")
        return True

    def filter_rows(self, column_name, value_to_remove):
        """Remove rows where specified column has a particular value (case-insensitive value matching)."""
        exact_column = self._find_exact_column(column_name)

        if exact_column is None:
            print(f"Error: Column '{column_name}' not found in CSV")
            print(f"Available columns: {list(self.df.columns)}")
            return False

        initial_count = len(self.df)

        # Normalize the value to remove for comparison
        normalized_value_to_remove = self._normalize_value(value_to_remove)

        # Create a mask for rows where normalized column values don't match the normalized target value
        mask = self.df[exact_column].apply(lambda x: self._normalize_value(x) != normalized_value_to_remove)
        self.df = self.df[mask]

        rows_removed = initial_count - len(self.df)
        print(f"Removed {rows_removed} rows where '{exact_column}' = '{value_to_remove}' (case-insensitive)")
        return True

    def drop_column(self, column_name):
        """Drop/remove a complete column from the DataFrame."""
        exact_column = self._find_exact_column(column_name)

        if exact_column is None:
            print(f"Error: Column '{column_name}' not found in CSV")
            print(f"Available columns: {list(self.df.columns)}")
            return False

        try:
            self.df = self.df.drop(columns=[exact_column])
            print(f"Successfully dropped column '{exact_column}'")
            print(f"Remaining columns ({len(self.df.columns)}): {list(self.df.columns)}")
            return True
        except Exception as e:
            print(f"Error dropping column '{exact_column}': {e}")
            return False

    def replace_values(self, column_name, old_value, new_value, replace_all=False):
        """Replace specific values in a column or all occurrences of a value (case-insensitive value matching)."""
        if replace_all:
            # Replace value across all columns with case-insensitive matching
            initial_count = 0
            normalized_old_value = self._normalize_value(old_value)

            for col in self.df.columns:
                # Count matches before replacement
                mask = self.df[col].apply(lambda x: self._normalize_value(x) == normalized_old_value)
                initial_count += mask.sum()

                # Replace values where normalized values match
                self.df.loc[mask, col] = new_value

            print(
                f"Replaced {initial_count} occurrences of '{old_value}' with '{new_value}' across all columns (case-insensitive)")
        else:
            # Replace value in specific column
            exact_column = self._find_exact_column(column_name)

            if exact_column is None:
                print(f"Error: Column '{column_name}' not found in CSV")
                print(f"Available columns: {list(self.df.columns)}")
                return False

            normalized_old_value = self._normalize_value(old_value)

            # Count matches before replacement
            mask = self.df[exact_column].apply(lambda x: self._normalize_value(x) == normalized_old_value)
            initial_count = mask.sum()

            # Replace values where normalized values match
            self.df.loc[mask, exact_column] = new_value

            print(
                f"Replaced {initial_count} occurrences of '{old_value}' with '{new_value}' in column '{exact_column}' (case-insensitive)")

        return True

    def replace_partial_values(self, column_name, old_substring, new_substring):
        """Replace substring within values in a specific column."""
        exact_column = self._find_exact_column(column_name)

        if exact_column is None:
            print(f"Error: Column '{column_name}' not found in CSV")
            print(f"Available columns: {list(self.df.columns)}")
            return False

        try:
            # Count how many cells contain the substring
            mask = self.df[exact_column].astype(str).str.contains(old_substring, na=False)
            initial_count = mask.sum()

            # Replace substring in string values
            self.df[exact_column] = self.df[exact_column].astype(str).str.replace(old_substring, new_substring)

            print(
                f"Replaced substring '{old_substring}' with '{new_substring}' in {initial_count} cells in column '{exact_column}'")
            return True
        except Exception as e:
            print(f"Error replacing substring in column '{exact_column}': {e}")
            return False

    def _normalize_column_names_for_comparison(self, columns):
        """Create a mapping of normalized column names to original names (case-sensitive)."""
        normalized_map = {}
        for col in columns:
            normalized = self._normalize_column_name(col)  # Only strips whitespace, keeps case
            normalized_map[normalized] = col
        return normalized_map

    def combine_csvs(self, csv_files, how='outer', on_column=None):
        """
        Combine multiple CSV files with matching attributes.

        Args:
            csv_files: List of CSV file paths to combine
            how: How to combine ('outer', 'inner', 'left', 'right') - default 'outer'
            on_column: Column to join on (optional, for merge operations)
        """
        if not csv_files:
            print("Error: No CSV files provided for combining")
            return False

        dataframes = []
        all_columns = set()

        # Load all CSV files
        for csv_file in csv_files:
            try:
                df_temp = pd.read_csv(csv_file)
                print(f"Loaded '{csv_file}' with {len(df_temp)} rows and {len(df_temp.columns)} columns")
                print(f"Columns: {list(df_temp.columns)}")

                # Normalize column names for comparison
                normalized_cols = [self._normalize_column_name(col) for col in df_temp.columns]
                all_columns.update(normalized_cols)

                dataframes.append((df_temp, csv_file))

            except Exception as e:
                print(f"Error loading '{csv_file}': {e}")
                return False

        if not dataframes:
            print("Error: No valid CSV files loaded")
            return False

        # Check if all files have compatible columns
        compatible_files = []
        reference_cols = set(
            self._normalize_column_name(col) for col in dataframes[0][0].columns)  # Case-sensitive comparison

        for df_temp, file_path in dataframes:
            current_cols = set(self._normalize_column_name(col) for col in df_temp.columns)  # Case-sensitive comparison

            if on_column:
                # For merge operations, just check if the join column exists
                join_col_normalized = self._normalize_column_name(on_column)
                if join_col_normalized in current_cols:
                    compatible_files.append((df_temp, file_path))
                else:
                    print(f"Warning: '{file_path}' doesn't have join column '{on_column}', skipping")
            else:
                # For concatenation, check column compatibility
                if current_cols == reference_cols:
                    compatible_files.append((df_temp, file_path))
                else:
                    missing_cols = reference_cols - current_cols
                    extra_cols = current_cols - reference_cols
                    print(f"Warning: '{file_path}' has different columns:")
                    if missing_cols:
                        print(f"  Missing: {missing_cols}")
                    if extra_cols:
                        print(f"  Extra: {extra_cols}")

                    if how == 'outer':
                        # Include anyway for outer join
                        compatible_files.append((df_temp, file_path))
                    else:
                        print(f"  Skipping '{file_path}' due to column mismatch")

        if not compatible_files:
            print("Error: No compatible CSV files found for combining")
            return False

        print(f"\nCombining {len(compatible_files)} compatible files...")

        try:
            if on_column:
                # Merge operation
                result_df = compatible_files[0][0]
                join_column = self._find_exact_column_in_df(result_df, on_column)

                if not join_column:
                    print(f"Error: Join column '{on_column}' not found in first file")
                    return False

                for i in range(1, len(compatible_files)):
                    df_temp, file_path = compatible_files[i]
                    join_col_temp = self._find_exact_column_in_df(df_temp, on_column)

                    if not join_col_temp:
                        print(f"Warning: Join column '{on_column}' not found in '{file_path}', skipping")
                        continue

                    result_df = result_df.merge(df_temp, left_on=join_column, right_on=join_col_temp, how=how,
                                                suffixes=('', f'_{i}'))
                    print(f"Merged with '{file_path}'")
            else:
                # Concatenation operation
                dfs_to_concat = [df for df, _ in compatible_files]
                result_df = pd.concat(dfs_to_concat, ignore_index=True, sort=False)

            # Update the main DataFrame
            original_rows = len(self.df) if self.df is not None else 0
            self.df = result_df
            self.original_rows = original_rows

            print(f"\nSuccessfully combined {len(compatible_files)} CSV files")
            print(f"Combined result: {len(self.df)} rows and {len(self.df.columns)} columns")
            print(f"Final columns: {list(self.df.columns)}")
            return True

        except Exception as e:
            print(f"Error combining CSV files: {e}")
            return False

    def _find_exact_column_in_df(self, df, target_column):
        """Find exact column match in a specific DataFrame (case-sensitive)."""
        target_normalized = self._normalize_column_name(target_column)  # Only strips whitespace

        for col in df.columns:
            if self._normalize_column_name(col) == target_normalized:
                return col
        return None

    def save_csv(self, output_file=None):
        """Save the cleaned DataFrame to a CSV file with timestamp."""
        if output_file is None:
            # Create output filename with timestamp in same folder as input
            input_path = Path(self.input_file)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = input_path.parent / f"{input_path.stem}_cleaned_{timestamp}{input_path.suffix}"

        try:
            self.df.to_csv(output_file, index=False)
            print(f"Cleaned CSV saved as '{output_file}'")
            print(
                f"Final result: {len(self.df)} rows and {len(self.df.columns)} columns (reduced from {self.original_rows} rows)")
            return True
        except Exception as e:
            print(f"Error saving CSV: {e}")
            return False

    def display_summary(self):
        """Display summary of the cleaning process."""
        if self.df is not None:
            print("\n--- Summary ---")
            print(f"Original rows: {self.original_rows}")
            print(f"Final rows: {len(self.df)}")
            print(f"Total rows removed: {self.original_rows - len(self.df)}")
            print(f"Final columns: {len(self.df.columns)}")
            print(f"Column names: {list(self.df.columns)}")


def main():
    parser = argparse.ArgumentParser(
        description='Clean CSV by removing duplicates, filtering rows, dropping columns, replacing values, combining CSV files, and converting text files to CSV')
    parser.add_argument('input_file', help='Input CSV or text file path')

    # Text-to-CSV conversion options
    parser.add_argument('--convert-to-csv', '-ctc', action='store_true',
                        help='Convert delimited text file to CSV format')
    parser.add_argument('--delimiter', '-d',
                        help='Delimiter used in text file (comma, tab, colon, semicolon, pipe, space, or custom character). Auto-detect if not specified.')
    parser.add_argument('--no-header', '-nh', action='store_true',
                        help='Text file does not have header row (will create generic column names)')
    parser.add_argument('--encoding', '-e', default='utf-8',
                        help='File encoding (default: utf-8)')

    # Existing options
    parser.add_argument('--unique-column', '-u', help='Column name to check for duplicates')
    parser.add_argument('--filter-column', '-fc', help='Column name to filter on')
    parser.add_argument('--filter-value', '-fv', help='Value to remove from filter column')
    parser.add_argument('--output', '-o', help='Output CSV file path (optional)')

    # Existing options continued
    parser.add_argument('--drop-column', '-dc', help='Column name to drop/remove completely')
    parser.add_argument('--replace-column', '-rc', help='Column name for value replacement')
    parser.add_argument('--old-value', '-ov', help='Old value to replace')
    parser.add_argument('--new-value', '-nv', help='New value to replace with')
    parser.add_argument('--replace-all', '-ra', action='store_true',
                        help='Replace value across all columns (ignores --replace-column)')
    parser.add_argument('--substring-replace', '-sr', action='store_true', help='Replace substring within values')

    # Combine functionality
    parser.add_argument('--combine-files', '-cf', nargs='+', help='Additional CSV files to combine with input file')
    parser.add_argument('--combine-method', '-cm', choices=['concat', 'merge'], default='concat',
                        help='Method to combine files: concat (stack rows) or merge (join on column)')
    parser.add_argument('--join-column', '-jc', help='Column name to join on when using merge method')
    parser.add_argument('--join-type', '-jt', choices=['outer', 'inner', 'left', 'right'], default='outer',
                        help='Type of join when merging files')

    args = parser.parse_args()

    # Initialize cleaner
    cleaner = CSVCleaner(args.input_file)

    # Handle text-to-CSV conversion first if specified
    if args.convert_to_csv:
        has_header = not args.no_header
        if not cleaner.convert_text_to_csv(
                delimiter=args.delimiter,
                has_header=has_header,
                output_file=args.output,
                encoding=args.encoding
        ):
            sys.exit(1)

        # If only converting, display summary and exit
        if not any([args.unique_column, args.filter_column, args.drop_column,
                    args.old_value, args.combine_files]):
            cleaner.display_summary()
            return

    # Handle combine operation if specified
    elif args.combine_files:
        all_files = [args.input_file] + args.combine_files
        if args.combine_method == 'concat':
            if not cleaner.combine_csvs(all_files, how=args.join_type):
                sys.exit(1)
        else:  # merge
            if not cleaner.combine_csvs(all_files, how=args.join_type, on_column=args.join_column):
                sys.exit(1)
    else:
        # Load CSV normally if not combining or converting
        if not cleaner.load_csv():
            sys.exit(1)

    # Validate arguments for cleaning operations
    if args.filter_column and not args.filter_value:
        print("Error: --filter-value is required when using --filter-column")
        sys.exit(1)

    if args.filter_value and not args.filter_column:
        print("Error: --filter-column is required when using --filter-value")
        sys.exit(1)

    if (args.old_value or args.new_value) and not (args.old_value and args.new_value):
        print("Error: Both --old-value and --new-value are required for replacement")
        sys.exit(1)

    if args.old_value and not args.replace_all and not args.replace_column:
        print("Error: --replace-column is required when replacing values (unless using --replace-all)")
        sys.exit(1)

    if args.combine_method == 'merge' and not args.join_column:
        print("Error: --join-column is required when using merge method")
        sys.exit(1)

    # Remove duplicates if unique column specified
    if args.unique_column:
        if not cleaner.remove_duplicates(args.unique_column):
            sys.exit(1)

    # Filter rows if filter criteria specified
    if args.filter_column and args.filter_value:
        if not cleaner.filter_rows(args.filter_column, args.filter_value):
            sys.exit(1)

    # Drop column if specified
    if args.drop_column:
        if not cleaner.drop_column(args.drop_column):
            sys.exit(1)

    # Replace values if specified
    if args.old_value and args.new_value:
        if args.substring_replace and not args.replace_all:
            if not cleaner.replace_partial_values(args.replace_column, args.old_value, args.new_value):
                sys.exit(1)
        else:
            if not cleaner.replace_values(args.replace_column, args.old_value, args.new_value, args.replace_all):
                sys.exit(1)

    # Save cleaned CSV (only if not already saved during conversion)
    if not args.convert_to_csv or args.unique_column or args.filter_column or args.drop_column or args.old_value:
        if not cleaner.save_csv(args.output):
            sys.exit(1)

    # Display summary
    cleaner.display_summary()


# Interactive mode for easier usage
def interactive_mode():
    """Run the cleaner in interactive mode for user-friendly operation."""
    print("=== CSV Data Cleaner - Interactive Mode ===")

    # Get input file
    input_file = input("Enter the path to your CSV or text file: ").strip()

    cleaner = CSVCleaner(input_file)

    # Check if file extension suggests it's not a CSV
    file_ext = Path(input_file).suffix.lower()
    if file_ext not in ['.csv']:
        convert_choice = input(
            f"File appears to be a text file ({file_ext}). Convert to CSV first? (y/n): ").strip().lower()

        if convert_choice == 'y':
            # Get conversion parameters
            print("\nCommon delimiters:")
            print("1. Comma (,)")
            print("2. Tab")
            print("3. Semicolon (;)")
            print("4. Colon (:)")
            print("5. Pipe (|)")
            print("6. Space")
            print("7. Auto-detect")
            print("8. Custom delimiter")

            delimiter_choice = input("Select delimiter (1-8): ").strip()

            delimiter_map = {
                '1': ',',
                '2': '\t',
                '3': ';',
                '4': ':',
                '5': '|',
                '6': ' ',
                '7': None,  # Auto-detect
            }

            if delimiter_choice in delimiter_map:
                delimiter = delimiter_map[delimiter_choice]
            elif delimiter_choice == '8':
                delimiter = input("Enter custom delimiter: ")
            else:
                print("Invalid choice, using auto-detect")
                delimiter = None

            has_header = input("Does the first line contain column headers? (y/n) [default: y]: ").strip().lower()
            has_header = has_header != 'n'

            encoding = input("Enter file encoding [default: utf-8]: ").strip() or 'utf-8'

            if not cleaner.convert_text_to_csv(delimiter=delimiter, has_header=has_header, encoding=encoding):
                print("Failed to convert text file to CSV")
                return
    else:
        # Ask if user wants to combine files first
        combine_choice = input("Do you want to combine this file with other CSV files? (y/n): ").strip().lower()

        if combine_choice == 'y':
            combine_files = []
            while True:
                additional_file = input("Enter path to additional CSV file (or press Enter to finish): ").strip()
                if not additional_file:
                    break
                combine_files.append(additional_file)

            if combine_files:
                all_files = [input_file] + combine_files
                print("\nCombine methods:")
                print("1. Concatenate (stack rows) - files should have same columns")
                print("2. Merge (join on column) - join files based on a common column")

                method_choice = input("Select combine method (1-2): ").strip()

                if method_choice == '2':
                    join_col = input("Enter the column name to join on: ").strip()
                    join_type = input("Enter join type (outer/inner/left/right) [default: outer]: ").strip() or 'outer'
                    cleaner.combine_csvs(all_files, how=join_type, on_column=join_col)
                else:
                    join_type = input("Enter join type (outer/inner/left/right) [default: outer]: ").strip() or 'outer'
                    cleaner.combine_csvs(all_files, how=join_type)
        else:
            # Load CSV normally
            if not cleaner.load_csv():
                return

    while True:
        print("\n=== Available Operations ===")
        print("1. Remove duplicates")
        print("2. Filter out specific rows")
        print("3. Drop a column")
        print("4. Replace specific values in a column")
        print("5. Replace values across all columns")
        print("6. Replace substring within values")
        print("7. Combine with additional CSV files")
        print("8. Convert text file to CSV")
        print("9. Save and exit")
        print("10. Exit without saving")

        choice = input("\nSelect operation (1-10): ").strip()

        if choice == '1':
            # Remove duplicates
            unique_col = input("Enter the column name to check for duplicates: ").strip()
            cleaner.remove_duplicates(unique_col)

        elif choice == '2':
            # Filter rows
            filter_col = input("Enter the column name to filter on: ").strip()
            filter_val = input(f"Enter the value to remove from '{filter_col}' column: ").strip()
            cleaner.filter_rows(filter_col, filter_val)

        elif choice == '3':
            # Drop column
            drop_col = input("Enter the column name to drop: ").strip()
            cleaner.drop_column(drop_col)

        elif choice == '4':
            # Replace values in specific column
            replace_col = input("Enter the column name: ").strip()
            old_val = input("Enter the old value: ").strip()
            new_val = input("Enter the new value: ").strip()
            cleaner.replace_values(replace_col, old_val, new_val, replace_all=False)

        elif choice == '5':
            # Replace values across all columns
            old_val = input("Enter the old value: ").strip()
            new_val = input("Enter the new value: ").strip()
            cleaner.replace_values(None, old_val, new_val, replace_all=True)

        elif choice == '6':
            # Replace substring
            replace_col = input("Enter the column name: ").strip()
            old_substring = input("Enter the substring to replace: ").strip()
            new_substring = input("Enter the new substring: ").strip()
            cleaner.replace_partial_values(replace_col, old_substring, new_substring)

        elif choice == '7':
            # Combine additional CSV files
            combine_files = []
            while True:
                additional_file = input("Enter path to additional CSV file (or press Enter to finish): ").strip()
                if not additional_file:
                    break
                combine_files.append(additional_file)

            if combine_files:
                print("\nCombine methods:")
                print("1. Concatenate (stack rows)")
                print("2. Merge (join on column)")

                method_choice = input("Select combine method (1-2): ").strip()

                if method_choice == '2':
                    join_col = input("Enter the column name to join on: ").strip()
                    join_type = input("Enter join type (outer/inner/left/right) [default: outer]: ").strip() or 'outer'

                    # Create temporary list with current data
                    current_files = combine_files
                    cleaner.combine_csvs(current_files, how=join_type, on_column=join_col)
                else:
                    join_type = input("Enter join type (outer/inner/left/right) [default: outer]: ").strip() or 'outer'
                    cleaner.combine_csvs(combine_files, how=join_type)

        elif choice == '8':
            # Convert text file to CSV
            text_file = input("Enter path to text file to convert: ").strip()

            print("\nCommon delimiters:")
            print("1. Comma (,)")
            print("2. Tab")
            print("3. Semicolon (;)")
            print("4. Colon (:)")
            print("5. Pipe (|)")
            print("6. Space")
            print("7. Auto-detect")
            print("8. Custom delimiter")

            delimiter_choice = input("Select delimiter (1-8): ").strip()

            delimiter_map = {
                '1': ',',
                '2': '\t',
                '3': ';',
                '4': ':',
                '5': '|',
                '6': ' ',
                '7': None,  # Auto-detect
            }

            if delimiter_choice in delimiter_map:
                delimiter = delimiter_map[delimiter_choice]
            elif delimiter_choice == '8':
                delimiter = input("Enter custom delimiter: ")
            else:
                print("Invalid choice, using auto-detect")
                delimiter = None

            has_header = input("Does the first line contain column headers? (y/n) [default: y]: ").strip().lower()
            has_header = has_header != 'n'

            encoding = input("Enter file encoding [default: utf-8]: ").strip() or 'utf-8'

            output_csv = input("Enter output CSV file path (or press Enter for auto-generated): ").strip() or None

            # Create temporary cleaner for conversion
            temp_cleaner = CSVCleaner(text_file)
            temp_cleaner.convert_text_to_csv(delimiter=delimiter, has_header=has_header,
                                             output_file=output_csv, encoding=encoding)

        elif choice == '9':
            # Save and exit
            output_file = input("\nEnter output file path (press Enter for auto-generated name): ").strip()
            if not output_file:
                output_file = None

            if cleaner.save_csv(output_file):
                cleaner.display_summary()
            break

        elif choice == '10':
            # Exit without saving
            print("Exiting without saving changes.")
            break

        else:
            print("Invalid choice. Please select 1-10.")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # No command line arguments, run interactive mode
        interactive_mode()
    else:
        # Command line arguments provided, run main function
        main()