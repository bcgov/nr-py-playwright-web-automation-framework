import fitz
from pathlib import Path

def pdf_to_images(pdf_path, output_dir=None):
    pdf_path = Path(pdf_path)

    base_dir = Path(output_dir) if output_dir else pdf_path.parent
    output_dir = base_dir / pdf_path.stem
    output_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    screenshots = []

    for i, page in enumerate(doc):
        pix = page.get_pixmap()
        screenshot_path = output_dir / f"page_{i+1}.png"
        pix.save(str(screenshot_path))
        screenshots.append(str(screenshot_path))

    return screenshots