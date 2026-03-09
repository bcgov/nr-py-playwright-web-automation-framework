import fitz
from pathlib import Path

def pdf_to_images(pdf_path, output_dir=None):
    """
    Convert each page of PDF to a PNG screenshot.

    Args:
        pdf_path (str or Path): path to PDF
        output_dir (Path, optional): folder to save screenshots

    Returns:
        list of screenshot file paths
    """
    pdf_path = Path(pdf_path)
    if output_dir is None:
        output_dir = pdf_path.parent / "screenshots"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    screenshots = []

    for i, page in enumerate(doc):
        pix = page.get_pixmap()
        screenshot_path = output_dir / f"page_{i+1}.png"
        pix.save(str(screenshot_path))
        screenshots.append(str(screenshot_path))

    return screenshots