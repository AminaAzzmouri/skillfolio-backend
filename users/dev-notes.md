# Dev Notes — Common Pitfalls & Fixes

This document logs errors we ran into during feature/guided-questions implementation and how we solved them.

## 1. Models not saved properly → Missing fields in migrations

    - Symptom: makemigrations didn’t detect new fields (work_type, duration_text, etc.).
    - Cause: VS Code didn’t actually save the models.py file (showed a compare dialog).
    - Fix: Ensure models.py is saved before running makemigrations. Always check with: git diff users/models.py

## 2. Admin fields mismatch (list_display / list_filter)

    - Symptom:
            * (admin.E108) The value of 'list_display[...]' refers to 'work_type', 
               which is not a callable, an attribute of 'ProjectAdmin', or an attribute or method on 'users.Project'.
    - Cause: Admin was referencing fields (work_type, duration_text) before they were actually added to the model.
    - Fix: After saving models, re-run migrations and confirm fields exist. Keep admin list_display and list_filter in sync with the model.

## 3. Forgot to activate venv → Missing deps

    - Symptom: ModuleNotFoundError: No module named 'corsheaders'
    - Cause: Forgot to activate the virtual environment after reopening terminal.
    - Fix:

            * Windows PowerShell: .\venv\Scripts\activate
            * macOS/Linux: source venv/bin/activate

## 4. Missing Certificate model import  
    
    - Symptom: ImportError: cannot import name 'Certificate' from 'users.models'
    - Cause: Certificate model wasn’t yet defined in models.py, but was referenced in admin.py and Project FK.
    - Fix: Define the Certificate model first, then reference it in Project.

## 5. Indentation Errors in serializers

    - Symptom: IndentationError: unindent does not match any outer indentation level
    - Cause: Copy/paste of serializer Meta class had inconsistent spacing (tabs vs spaces).
    - Fix: Normalize indentation in VS Code (Ctrl+Shift+P → Convert Indentation to Spaces).

## 6. Validation Testing — Projects/Goals

    ### Project auto-description: Confirmed that if description is blank, backend composes one from guided answers.
    
    - Goal validations:
            Negative target → rejected
            Past deadline → rejected
            progress_percent computed correctly from completed projects



