#!/usr/bin/env python3
"""
Script to generate architecture change documentation templates.
"""

import argparse
import os
from datetime import datetime

TEMPLATE = """# {title}

## Overview

[Brief description of the architecture change]

## Motivation

[Explain why this change was necessary]

## Implementation Details

1. **[Component 1]**: 
   - [Description of changes]
   - [Technical details]

2. **[Component 2]**:
   - [Description of changes]
   - [Technical details]

## Migration Path

### For [User Type 1]
[Steps for migration]

### For [User Type 2]
[Steps for migration]

## Advantages

- **[Advantage 1]**: [Description]
- **[Advantage 2]**: [Description]
- **[Advantage 3]**: [Description]

## Potential Issues

1. **[Issue 1]**: [Description and mitigation]
2. **[Issue 2]**: [Description and mitigation]
3. **[Issue 3]**: [Description and mitigation]

## Future Considerations

1. **[Future Work 1]**:
   - [Description]
   - [Timeline]

2. **[Future Work 2]**:
   - [Description]
   - [Timeline]

## Architecture Diagram

```
[Insert ASCII/text-based diagram here]
```
"""


def create_architecture_doc(title, output_path=None):
    """Create an architecture change documentation file with the given title."""
    # Format the title for the filename
    formatted_title = title.lower().replace(" ", "_")

    # Get the current date
    date_prefix = datetime.now().strftime("%Y%m%d")

    # Create the filename
    filename = f"{date_prefix}_{formatted_title}.md"

    # Determine the output path
    if not output_path:
        output_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "docs",
            "architecture_changes",
        )

    # Create the output directory if it doesn't exist
    os.makedirs(output_path, exist_ok=True)

    # Create the file path
    file_path = os.path.join(output_path, filename)

    # Fill the template
    content = TEMPLATE.format(title=title)

    # Write the file
    with open(file_path, "w") as f:
        f.write(content)

    print(f"Created architecture change documentation: {file_path}")
    return file_path


def main():
    """Main function to parse arguments and create the documentation."""
    parser = argparse.ArgumentParser(
        description="Generate architecture change documentation template"
    )
    parser.add_argument(
        "title",
        help="Title of the architecture change (e.g., 'Database Migration')",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output directory (default: docs/architecture_changes)",
        default=None,
    )

    args = parser.parse_args()
    create_architecture_doc(args.title, args.output)


if __name__ == "__main__":
    main()
