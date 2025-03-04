import dagger
from dagger import dag, object_type, function

@object_type
class PdfTools:
    """Module for PDF image extraction and analysis."""
    
    @function
    async def extract_image(self, pdf_file: dagger.File, page_number: int) -> str:
        """Extract an image from a specific page in the PDF."""
        # Create a container to extract the image
        container = (
            dag.container()
            .from_("python:3.12-slim")
            .with_exec(["pip", "install", "PyPDF2", "Pillow"])
            .with_file("/app/exam.pdf", pdf_file)
            # Copy the pdf_tools.py script from the Dagger module
            .with_mounted_directory("/src", dag.host().directory("src"))
            .with_exec(["cp", "/src/qaextractor/scripts/tools/pdf_tools.py", "/app/"])
            .with_workdir("/app")
            .with_exec(["python", "pdf_tools.py", "extract_images", "exam.pdf", str(page_number)])
        )
        
        return await container.stdout()