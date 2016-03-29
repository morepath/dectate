This scenario is based on

http://docs.pylonsproject.org/projects/pyramid/en/latest/designdefense.html#application-programmers-don-t-control-the-module-scope-codepath-import-time-side-effects-are-evil

To run it, add dectate to the PYTHONPATH and then do:

  $ python app.py

You should see a ConflictError.
