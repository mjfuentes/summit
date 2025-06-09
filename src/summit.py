#!/usr/bin/env python3
"""
Summit - Wrapper to redirect to FastMCP server

This file is maintained for backward compatibility.
It redirects to the new FastMCP server implementation.
"""

import logging
import os
import sys
import warnings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Show deprecation warning
warnings.warn(
    "The summit.py server is deprecated and will be removed in a future version. "
    "Please use fastmcp_server.py instead.",
    DeprecationWarning,
    stacklevel=2,
)

if __name__ == "__main__":
    logger.info("Redirecting to FastMCP server...")

    # Set the transport to stdio for backward compatibility
    os.environ["MCP_TRANSPORT"] = "stdio"

    # Import and run the FastMCP server
    try:
        # Since we're in the src directory, we can import directly
        from fastmcp_server import mcp

        mcp.run(transport="stdio")
    except ImportError:
        logger.error(
            "Failed to import FastMCP server. Please install FastMCP or check your installation."
        )
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error running FastMCP server: {e}", exc_info=True)
        sys.exit(1)
