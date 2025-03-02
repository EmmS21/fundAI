"""
Constants for the orchestration module.
Contains only shared values that are repeated across multiple scripts.
"""

# Education levels with their folder IDs
EDUCATION_LEVELS = {
    "ASLevel": "1lzWwkwUXA0MfSUEUePxGiSePY_qQKP-E",
    "Primary School": "1oQtk89IL1iX1bU3kl9Axx2Cqb5uq1PFN",
    "OLevel": "1lunOQUkc02cfsdZXcuLZe5rOBgUVvYwk"
}

# Result structure for level processing
def create_level_result(level_name, documents_created=0, errors=0, error_details=None):
    """Create a standardized result structure for level processing"""
    return {
        "level": level_name,
        "documents_created": documents_created,
        "errors": errors,
        "error_details": error_details or []
    }
