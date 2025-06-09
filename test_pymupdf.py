# test_pymupdf.py
# A simple script to test PyMuPDF text rotation

import fitz

def test_rotation():
    try:
        # Create a new PDF document
        doc = fitz.open()
        # Add a new page
        doc.new_page()
        
        # Test with float rotation value
        doc[0].insert_text(
            fitz.Point(100, 100),
            "Test with float rotation",
            fontsize=12,
            fontname="helv",
            rotate=45.0,  # Using float value
            color=(0, 0, 0)
        )
        
        print("Rotation test successful!")
        return True
    except Exception as e:
        print(f"Rotation test failed: {e}")
        return False

if __name__ == "__main__":
    test_rotation()