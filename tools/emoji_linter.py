#!/usr/bin/env python3

"""
Emoji Linter for Summit Project
Automatically detects and removes emoji characters from code and documentation.
Enforces the strict no-emoji policy across the entire codebase.
"""

import os
import re
import sys
import argparse
import unicodedata
from pathlib import Path
from typing import List, Tuple, Set
import subprocess

class EmojiLinter:
    """Detects and removes emoji characters from files"""
    
    def __init__(self, auto_fix: bool = False, verbose: bool = False):
        self.auto_fix = auto_fix
        self.verbose = verbose
        self.files_changed = []
        self.total_emojis_removed = 0
        
        # Comprehensive emoji detection patterns
        self.emoji_patterns = [
            # Unicode emoji ranges
            r'[\U0001F600-\U0001F64F]',  # emoticons
            r'[\U0001F300-\U0001F5FF]',  # symbols & pictographs
            r'[\U0001F680-\U0001F6FF]',  # transport & map symbols
            r'[\U0001F1E0-\U0001F1FF]',  # flags (iOS)
            r'[\U00002702-\U000027B0]',  # dingbats
            r'[\U000024C2-\U0001F251]',  # enclosed characters
            r'[\U0001F900-\U0001F9FF]',  # supplemental symbols
            r'[\U0001FA70-\U0001FAFF]',  # symbols and pictographs extended-A
            
            # Common emoji sequences
            r'[\u2600-\u26FF]',          # miscellaneous symbols
            r'[\u2700-\u27BF]',          # dingbats
            r'[\U0001F170-\U0001F251]',  # enclosed ideographic supplement
        ]
        
        # Compile all patterns into one regex
        self.emoji_regex = re.compile('|'.join(self.emoji_patterns))
        
        # Files to include in scanning
        self.include_extensions = {
            '.py', '.md', '.txt', '.rst', '.json', '.yaml', '.yml',
            '.js', '.ts', '.html', '.css', '.sh', '.bash', '.zsh'
        }
        
        # Directories to skip
        self.skip_dirs = {
            '.git', '__pycache__', '.pytest_cache', 'node_modules',
            '.coverage', '.venv', 'venv', 'env'
        }
    
    def is_emoji(self, char: str) -> bool:
        """Check if a character is an emoji using multiple methods"""
        # Method 1: Unicode category check
        if unicodedata.category(char) == 'So':  # Symbol, other
            return True
            
        # Method 2: Regex pattern matching
        if self.emoji_regex.match(char):
            return True
            
        # Method 3: Unicode name check for common emoji keywords
        try:
            name = unicodedata.name(char, '').lower()
            emoji_keywords = [
                'face', 'smile', 'heart', 'fire', 'rocket', 'check',
                'cross', 'warning', 'heavy', 'white', 'black'
            ]
            if any(keyword in name for keyword in emoji_keywords):
                return True
        except ValueError:
            pass
            
        return False
    
    def detect_emojis_in_text(self, text: str) -> List[Tuple[int, str]]:
        """Detect emoji characters in text and return their positions"""
        emojis = []
        for i, char in enumerate(text):
            if self.is_emoji(char):
                emojis.append((i, char))
        return emojis
    
    def remove_emojis_from_text(self, text: str) -> Tuple[str, int]:
        """Remove all emojis from text and return cleaned text + count"""
        original_text = text
        
        # Remove using regex patterns
        cleaned_text = self.emoji_regex.sub('', text)
        
        # Remove using character-by-character check for edge cases
        final_text = ''
        emojis_removed = 0
        
        for char in cleaned_text:
            if self.is_emoji(char):
                emojis_removed += 1
                if self.verbose:
                    print(f"Removing emoji: {char} (U+{ord(char):04X})")
            else:
                final_text += char
        
        # Count total emojis removed by comparing lengths
        total_removed = len(original_text) - len(final_text)
        
        return final_text, total_removed
    
    def should_process_file(self, file_path: Path) -> bool:
        """Check if a file should be processed for emoji removal"""
        # Skip if file is in excluded directory
        for part in file_path.parts:
            if part in self.skip_dirs:
                return False
        
        # Include if extension matches
        if file_path.suffix.lower() in self.include_extensions:
            return True
            
        # Include if it's a shell script or executable text file
        if file_path.is_file():
            try:
                with open(file_path, 'rb') as f:
                    header = f.read(100)
                    # Check for shebang
                    if header.startswith(b'#!'):
                        return True
                    # Check if it's likely a text file
                    try:
                        header.decode('utf-8')
                        return True
                    except UnicodeDecodeError:
                        return False
            except (PermissionError, OSError):
                return False
                
        return False
    
    def process_file(self, file_path: Path) -> bool:
        """Process a single file for emoji removal"""
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                original_content = f.read()
            
            # Check for emojis
            emojis_found = self.detect_emojis_in_text(original_content)
            
            if not emojis_found:
                return False  # No emojis found
            
            if self.verbose:
                print(f"Found {len(emojis_found)} emojis in {file_path}")
                for pos, emoji in emojis_found[:10]:  # Show first 10
                    print(f"  Position {pos}: {emoji} (U+{ord(emoji):04X})")
                if len(emojis_found) > 10:
                    print(f"  ... and {len(emojis_found) - 10} more")
            
            if not self.auto_fix:
                print(f"EMOJI VIOLATION: {file_path} contains {len(emojis_found)} emoji(s)")
                return True  # Found emojis but not fixing
            
            # Remove emojis
            cleaned_content, emojis_removed = self.remove_emojis_from_text(original_content)
            
            if emojis_removed > 0:
                # Write cleaned content back
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(cleaned_content)
                
                print(f"FIXED: Removed {emojis_removed} emojis from {file_path}")
                self.files_changed.append(str(file_path))
                self.total_emojis_removed += emojis_removed
                return True
            
            return False
            
        except (UnicodeDecodeError, PermissionError, OSError) as e:
            if self.verbose:
                print(f"Skipping {file_path}: {e}")
            return False
    
    def scan_directory(self, directory: Path) -> bool:
        """Scan entire directory for emoji violations"""
        violations_found = False
        files_processed = 0
        
        for file_path in directory.rglob('*'):
            if file_path.is_file() and self.should_process_file(file_path):
                files_processed += 1
                if self.process_file(file_path):
                    violations_found = True
        
        if self.verbose:
            print(f"Processed {files_processed} files")
            
        return violations_found
    
    def scan_git_staged_files(self) -> bool:
        """Scan only Git staged files for emoji violations"""
        try:
            # Get list of staged files
            result = subprocess.run(
                ['git', 'diff', '--cached', '--name-only'],
                capture_output=True, text=True, check=True
            )
            staged_files = result.stdout.strip().split('\n')
            
            if not staged_files or staged_files == ['']:
                if self.verbose:
                    print("No staged files to check")
                return False
            
            violations_found = False
            
            for file_path_str in staged_files:
                file_path = Path(file_path_str)
                if file_path.exists() and self.should_process_file(file_path):
                    if self.process_file(file_path):
                        violations_found = True
            
            return violations_found
            
        except subprocess.CalledProcessError:
            if self.verbose:
                print("Not in a Git repository or no Git available")
            return False
    
    def generate_report(self) -> str:
        """Generate a summary report of emoji linting results"""
        if self.auto_fix:
            if self.total_emojis_removed > 0:
                report = f"Emoji Linter: Removed {self.total_emojis_removed} emojis from {len(self.files_changed)} files\n"
                if self.files_changed:
                    report += "Modified files:\n"
                    for file_path in self.files_changed:
                        report += f"  - {file_path}\n"
                return report
            else:
                return "Emoji Linter: No emojis found - codebase is clean!"
        else:
            if self.total_emojis_removed > 0:
                return f"Emoji Linter: Found emoji violations in {len(self.files_changed)} files"
            else:
                return "Emoji Linter: No emoji violations found"

def main():
    """Main entry point for emoji linter"""
    parser = argparse.ArgumentParser(
        description='Emoji Linter - Remove emoji characters from code and documentation'
    )
    parser.add_argument(
        '--fix', action='store_true',
        help='Automatically remove emojis (default: just report violations)'
    )
    parser.add_argument(
        '--staged', action='store_true',
        help='Only check Git staged files (for pre-commit hooks)'
    )
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Verbose output showing details of emoji detection'
    )
    parser.add_argument(
        'paths', nargs='*', default=['.'],
        help='Files or directories to check (default: current directory)'
    )
    
    args = parser.parse_args()
    
    linter = EmojiLinter(auto_fix=args.fix, verbose=args.verbose)
    
    violations_found = False
    
    if args.staged:
        # Check only staged files for pre-commit hook
        violations_found = linter.scan_git_staged_files()
    else:
        # Check specified paths
        for path_str in args.paths:
            path = Path(path_str)
            if path.is_file():
                if linter.should_process_file(path):
                    if linter.process_file(path):
                        violations_found = True
            elif path.is_dir():
                if linter.scan_directory(path):
                    violations_found = True
            else:
                print(f"Path not found: {path}")
    
    # Print summary
    print(linter.generate_report())
    
    # Exit with appropriate code
    if violations_found and not args.fix:
        print("\nEmoji violations found! Run with --fix to automatically remove them.")
        sys.exit(1)
    elif linter.files_changed and args.fix:
        print("\nFiles were modified. Please review changes and re-add to Git if needed.")
        sys.exit(1)  # Exit with 1 to trigger re-staging in pre-commit hook
    else:
        sys.exit(0)

if __name__ == '__main__':
    main() 