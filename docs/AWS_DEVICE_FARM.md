# AWS Device Farm

AWS Device Farm is planned for hardware validation and repeatable benchmark runs on real Android phones. It should be introduced after a minimal Android probe APK or test runner exists, not after the full inference library.

Expected later usage:

- List available Samsung Android devices.
- Create or reuse a Device Farm project.
- Upload probe or benchmark APK artifacts.
- Schedule runs with explicit user-provided AWS credentials.
- Pull result artifacts for schema validation and benchmark analysis.

Phase 0 status:

- Only shell script stubs and documentation are created.
- No AWS credentials are included.
- No external service is required for tests.
- No Device Farm run is scheduled.

