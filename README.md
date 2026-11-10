# resume_builder

Builds a 2-page `Resume.docx` and `Resume.pdf` from a plain `.txt` resume.
The code is the original `create_resume.py`, unchanged; only packaging was added.

    pip install .
    create-resume "examples/New Resume.txt" -o out --verify
    python -m resume_builder resume.txt --basename MyCV      # same thing

On Windows, double-click `run_resume.bat`.

`prompts/cv_tailoring_prompt.txt` is the CV-tailoring prompt template.
