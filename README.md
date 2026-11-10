# resume_builder

Tailors your resume to a job using the bundled prompt (`src/resume_builder/prompt_template.txt`),
then builds a 2-page `Resume.docx` and `Resume.pdf` with the original `create_resume.py` (unchanged).

## Windows (easiest)
Double-click `run_resume.bat` and pick:
1. Local Qwen 2.5 3B - installs Ollama (winget) and downloads the model (~2 GB, once)
2. Claude API - paste your Anthropic API key (used for this run only)
3. Format only - no AI

## Command line
    pip install .
    tailor-resume "examples/New Resume.txt" --job-title "Senior Program Manager" --company "Acme" --jd job.txt --backend qwen   -o out --verify
    tailor-resume "examples/New Resume.txt" --job-title "Senior Program Manager" --jd job.txt --backend claude -o out --verify
    create-resume resume.txt -o out --verify        # format only

Outputs in the output folder: `Resume.txt` (tailored), `Resume.docx`, `Resume.pdf`,
`Resume_report.md` (fit rating, keyword table, metric questions, LinkedIn About, bullet variations)
and `Resume_raw.txt` (the model's raw reply, for debugging).

Your input TXT must use the same layout as `examples/New Resume.txt`.
After tailoring, check the warnings: the tool flags any employer/date that differs from your original
and any `[ADD METRIC]` placeholders left for you to fill in.
