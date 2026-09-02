# Do not submit the draft

The file `docs/Day1-Foundations-Lab-Submission.md` is a **source draft**.

The grader explicitly requires actual run evidence for Labs 1.2 and 1.3.
Therefore the only grader-ready file is generated after the real model runs:

`submission/Day1-Foundations-Lab-Submission-FINAL.md`

On Windows run:

```powershell
powershell -ExecutionPolicy Bypass -File .\GENERATE-COMPLETE-SUBMISSION.ps1
```

The command performs:

1. real model execution;
2. evidence capture;
3. automatic insertion into Labs 1.2/1.3;
4. completeness verification.

The verifier fails if placeholders remain or token/path evidence is absent.
