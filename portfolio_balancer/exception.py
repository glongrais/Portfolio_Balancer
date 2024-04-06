class UnsupportedFileTypeError(Exception):
    """Exception raised for unsupported file types."""
    def __init__(self, file_type, message="Unsupported file type"):
        self.file_type = file_type
        self.message = message + f": {file_type}"
        super().__init__(self.message)