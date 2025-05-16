from .server import mcp


def main():
    """Main entry point for the package."""
    mcp.run()


# Optionally expose other important items at package level
__all__ = ['main', 'server']

if __name__ == "__main__":
    main()
