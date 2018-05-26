import os

from reportlab.pdfgen.canvas import Canvas


# TODO: keep working on PDF generation.  This is a scratch function.
def make_pdf(path, text):
    """
    Args:
      path: a path-like object.
      text: the text to include, as a string.
    """
    # Convert the path to a string for reportlab.
    path = os.fspath(path)
    canvas = Canvas(path)
    canvas.drawString(200, 500, text)
    canvas.showPage()
    canvas.save()
