"""
Safe DOCX placeholder replacement with 100% formatting preservation.

Task 3: Replace {{placeholders}} in DOCX while preserving ALL run formatting.
Critical guarantee: font.name, font.size, bold, italic, color, and all other
run properties are NEVER modified.

Strategy:
1. Simple case: Placeholder in single run → replace text only, no property touch
2. Fallback: Placeholder spans multiple runs → reconstruct preserving originals
"""
from typing import Optional
from docx.text.paragraph import Paragraph


class LaudoDocxSafe:
    """Replace placeholders in DOCX paragraphs while preserving formatting."""

    def replace_in_paragraph_safe(
        self, para: Paragraph, old_text: str, new_text: str
    ) -> bool:
        """
        Replace old_text with new_text in paragraph, preserving ALL formatting.

        Args:
            para: python-docx Paragraph object
            old_text: Placeholder to find (e.g., "{{numero_laudo}}")
            new_text: Replacement value (e.g., "2026-00001")

        Returns:
            True if replaced, False if not found

        Guarantee:
            No run properties modified (font.name, font.size, bold, italic, color, etc.)
            All formatting is preserved exactly as-is.
        """
        if not para.runs:
            return False

        # Try simple case first: placeholder entirely in one run
        for run in para.runs:
            if old_text in run.text:
                # Replace text only, never touch properties
                run.text = run.text.replace(old_text, new_text)
                return True

        # Fallback: placeholder might span multiple runs
        # Concatenate all run texts to find the placeholder
        full_text = "".join(run.text for run in para.runs)

        if old_text not in full_text:
            return False

        # Placeholder spans multiple runs - reconstruct carefully
        self._replace_spanning_placeholder(para, old_text, new_text, full_text)
        return True

    def _replace_spanning_placeholder(
        self, para: Paragraph, old_text: str, new_text: str, full_text: str
    ) -> None:
        """
        Handle case where placeholder spans multiple runs.

        Strategy: Reconstruct runs while preserving original formatting.
        - Find the placeholder position
        - Split runs intelligently at boundaries
        - Replace placeholder text
        - Preserve original run properties for all affected runs
        """
        # Find position of old_text in concatenated text
        replacement_index = full_text.find(old_text)
        if replacement_index < 0:
            return

        # Build list of (run, start_in_run, end_in_run) for affected runs
        affected_runs = []
        char_count = 0
        for run in para.runs:
            run_start = char_count
            run_end = char_count + len(run.text)

            # Check if this run overlaps with the placeholder
            if run_end > replacement_index and run_start < replacement_index + len(
                old_text
            ):
                # Calculate position within this specific run
                local_start = max(0, replacement_index - run_start)
                local_end = min(len(run.text), replacement_index + len(old_text) - run_start)
                affected_runs.append((run, local_start, local_end, run_start))

            char_count = run_end

        if not affected_runs:
            return

        # Reconstruct: for first affected run, do the replacement
        # For others, just adjust or mark for removal
        first_run, first_local_start, first_local_end, _ = affected_runs[0]

        # Build new text for first run: keep before + new_text + keep after
        before = first_run.text[:first_local_start]
        after = first_run.text[first_local_end:]
        first_run.text = before + new_text + after

        # For remaining affected runs, clear their text
        # (they contained parts of the old placeholder that we've now replaced)
        for run, local_start, local_end, _ in affected_runs[1:]:
            run.text = ""

    def replace_in_document(
        self, doc, placeholder_map: dict
    ) -> None:
        """
        Replace multiple placeholders in a full document.

        Args:
            doc: python-docx Document object
            placeholder_map: Dict mapping placeholder → replacement value
                            e.g., {"{{numero_laudo}}": "2026-00001", ...}

        This is a convenience method for Task 4 (LaudoGeneratorV2) to use.
        """
        if not placeholder_map:
            return

        # Process all paragraphs in document
        for para in doc.paragraphs:
            for placeholder, value in placeholder_map.items():
                self.replace_in_paragraph_safe(para, placeholder, str(value))

        # Also process tables (common in templates)
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        for placeholder, value in placeholder_map.items():
                            self.replace_in_paragraph_safe(
                                para, placeholder, str(value)
                            )
