"""Render TikZ code to PNG bytes via pdflatex + PyMuPDF."""

import asyncio
import logging
import os
import tempfile

logger = logging.getLogger(__name__)


async def render_tikz_to_png(tikz_code: str) -> bytes | None:
    """Render a TikZ snippet to PNG bytes.

    Uses asyncio.create_subprocess_exec (safe, no shell injection) to run
    pdflatex, then PyMuPDF to convert the resulting PDF to a PNG at 150 DPI.

    Returns None on any failure (missing pdflatex, compilation error, etc.).
    """
    tmpdir = tempfile.mkdtemp(prefix="tikz_")
    tex_path = os.path.join(tmpdir, "diagram.tex")
    pdf_path = os.path.join(tmpdir, "diagram.pdf")

    tex_document = rf"""\documentclass[border=2pt]{{standalone}}
\usepackage{{tikz}}
\begin{{document}}
{tikz_code}
\end{{document}}
"""

    try:
        # Write .tex file
        with open(tex_path, "w") as f:
            f.write(tex_document)

        # Run pdflatex via asyncio.create_subprocess_exec (no shell, safe)
        proc = await asyncio.create_subprocess_exec(
            "pdflatex",
            "-interaction=nonstopmode",
            "-output-directory", tmpdir,
            tex_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

        if proc.returncode != 0:
            logger.warning(
                "pdflatex failed (rc=%d): %s",
                proc.returncode,
                stderr.decode(errors="replace")[:500],
            )
            return None

        if not os.path.exists(pdf_path):
            logger.warning("pdflatex produced no PDF output")
            return None

        # Convert PDF to PNG using PyMuPDF
        import fitz  # PyMuPDF

        doc = fitz.open(pdf_path)
        page = doc[0]
        # 150 DPI: default is 72, so zoom = 150/72
        zoom = 150 / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        png_bytes = pix.tobytes("png")
        doc.close()

        return png_bytes

    except asyncio.TimeoutError:
        logger.warning("pdflatex timed out after 30s")
        return None
    except Exception as e:
        logger.warning("TikZ rendering failed: %s", e)
        return None
    finally:
        # Clean up temp files
        for fname in os.listdir(tmpdir):
            try:
                os.remove(os.path.join(tmpdir, fname))
            except OSError:
                pass
        try:
            os.rmdir(tmpdir)
        except OSError:
            pass
